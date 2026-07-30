from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.schemas.assembly_plan import (
    AssemblyComponent,
    AssemblyConnection,
    AssemblyPlan,
    AssemblyWarning,
    ConnectionEndpoint,
    Placement,
    Transform,
    Vector3,
)
from app.services.asset_metadata import (
    AssetMetadataError,
    BreadboardGeometry,
    ComponentFootprint,
    load_breadboard_geometry,
    load_component_footprint,
)

if TYPE_CHECKING:
    from app.schemas.circuit import CircuitGenerationResponse


TERMINAL_RE = re.compile(r"^([A-J])([1-9]|[12][0-9]|30)$")
RAIL_RE = re.compile(r"^(?:RAIL_)?(TOP|BOTTOM)_(POS|NEG)_S([1-5])_([1-5])$")
SHORT_RAIL_RE = re.compile(r"^([TB])([+-])([1-9]|1[0-9]|2[0-5])$")
POWER_PINS = {"5V", "3V3", "VCC", "VIN", "AUX_5V", "AUX_3V3"}
GROUND_PINS = {"GND", "GND_D", "GND_P1", "GND_P2", "AUX_GND_1", "AUX_GND_2"}
IO_PINS = {f"D{i}" for i in range(14)} | {f"A{i}" for i in range(6)}
LED_SLUGS = {"led-5mm-blue", "led-5mm-red"}
BREADBOARD_ID = "breadboard-1"


@dataclass(frozen=True)
class PhysicalAddress:
    canonical: str
    kind: str
    electrical_group: str


def parse_physical_address(value: str, geometry: BreadboardGeometry | None = None) -> PhysicalAddress:
    """Resolve actual half-breadboard terminal and segmented-rail addresses."""
    geometry = geometry or load_breadboard_geometry()
    address = value.strip().upper()
    terminal = TERMINAL_RE.fullmatch(address)
    if terminal:
        row, column = terminal.groups()
        bank = "AE" if row <= "E" else "FJ"
        return PhysicalAddress(address, "terminal", f"terminal-{bank}-{column}")

    short_rail = SHORT_RAIL_RE.fullmatch(address)
    if short_rail:
        side, polarity, index_text = short_rail.groups()
        index = int(index_text)
        segment, hole = (index - 1) // 5 + 1, (index - 1) % 5 + 1
        side_name = "TOP" if side == "T" else "BOTTOM"
        polarity_name = "POS" if polarity == "+" else "NEG"
        address = f"RAIL_{side_name}_{polarity_name}_S{segment}_{hole}"

    rail = RAIL_RE.fullmatch(address)
    if rail and address in geometry.rail_groups:
        return PhysicalAddress(address, "rail", geometry.rail_groups[address])
    raise ValueError(f"Unsupported breadboard address: {value}")


class _UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


class BreadboardAllocator:
    """Place real metadata footprints on unoccupied 2.54 mm breadboard holes."""

    ROW_ORDER = ("E", "D", "J", "I", "C", "H", "B", "G", "A", "F")
    ROW_PAIRS = {
        "A": "F",
        "B": "G",
        "C": "H",
        "D": "F",
        "E": "F",
        "F": "A",
        "G": "B",
        "H": "C",
        "I": "E",
        "J": "E",
    }

    def __init__(self, geometry: BreadboardGeometry):
        self.geometry = geometry
        self.occupied_holes: set[str] = set()
        self.keep_outs: list[tuple[float, float, float, float]] = []

    def allocate(self, component_id: str, footprint: ComponentFootprint) -> Placement | None:
        max_offset = max(footprint.offsets)
        start_column = 2 if footprint.asset_slug == "pushbutton-6x6" else 1
        for row in self.ROW_ORDER:
            for column in range(start_column, self.geometry.columns - max_offset + 1):
                addresses = self._addresses_for(row, column, footprint)
                if addresses is None:
                    continue
                if any(address in self.occupied_holes for address in addresses.values()):
                    continue
                positions = [self.geometry.hole_position(address) for address in addresses.values()]
                x = sum(position[0] for position in positions) / len(positions)
                z = sum(position[2] for position in positions) / len(positions)
                half_width = footprint.width_meter / 2 + footprint.keep_out_meter
                half_depth = footprint.depth_meter / 2 + footprint.keep_out_meter
                candidate = (x - half_width, x + half_width, z - half_depth, z + half_depth)
                if (candidate[0] < self.geometry.x_bounds[0] or candidate[1] > self.geometry.x_bounds[1]
                        or candidate[2] < self.geometry.z_bounds[0] or candidate[3] > self.geometry.z_bounds[1]):
                    continue
                if any(self._intersects(candidate, occupied) for occupied in self.keep_outs):
                    continue
                self.occupied_holes.update(addresses.values())
                self.keep_outs.append(candidate)
                return Placement(
                    componentId=component_id,
                    mode="breadboard",
                    addresses=addresses,
                    transform=Transform(position=Vector3(x=x, y=self.geometry.surface_y_meter, z=z)),
                )
        return None

    def _addresses_for(
        self,
        row: str,
        column: int,
        footprint: ComponentFootprint,
    ) -> dict[str, str] | None:
        if footprint.row_offsets is None:
            return {
                pin: f"{row}{column + offset}"
                for pin, offset in zip(footprint.pins, footprint.offsets)
            }

        row_pair = self.ROW_PAIRS.get(row)
        if row_pair is None:
            return None
        rows = (row, row_pair)
        return {
            pin: f"{rows[row_offset]}{column + column_offset}"
            for pin, column_offset, row_offset in zip(
                footprint.pins,
                footprint.offsets,
                footprint.row_offsets,
            )
        }

    @staticmethod
    def _intersects(left, right) -> bool:
        return not (
            left[1] <= right[0] or left[0] >= right[1]
            or left[3] <= right[2] or left[2] >= right[3]
        )


def _terminal_siblings(address: str) -> list[str]:
    terminal = TERMINAL_RE.fullmatch(address)
    if not terminal:
        return []
    row, column = terminal.groups()
    rows = "ABCDE" if row <= "E" else "FGHIJ"
    return [f"{candidate}{column}" for candidate in rows]


def _wire_rows_for_component_pin(component_key: str | None, pin_address: str) -> list[str] | None:
    if component_key != "pushbutton-6x6":
        return None
    terminal = TERMINAL_RE.fullmatch(pin_address)
    if not terminal:
        return None
    row, _ = terminal.groups()
    if row == "E":
        return ["D", "C", "B", "A"]
    if row == "F":
        return ["G", "H", "I", "J"]
    if row <= "D":
        return ["E", "D", "C", "B", "A"]
    return ["F", "G", "H", "I", "J"]


def _wire_hole_for_pin(
    pin_address: str | None,
    occupied_holes: set[str],
    used_wire_holes: set[str],
    component_key: str | None = None,
) -> str | None:
    if pin_address is None:
        return None
    preferred_rows = _wire_rows_for_component_pin(component_key, pin_address)
    candidates = (
        [f"{row}{TERMINAL_RE.fullmatch(pin_address).group(2)}" for row in preferred_rows]
        if preferred_rows is not None
        else _terminal_siblings(pin_address)
    )
    for candidate in candidates:
        if candidate not in occupied_holes and candidate not in used_wire_holes:
            used_wire_holes.add(candidate)
            return candidate
    return pin_address


class PhysicalAssemblyPlanEngine:
    """Build a deterministic 3D plan backed by the integrated asset metadata."""

    def build(self, response: CircuitGenerationResponse) -> AssemblyPlan:
        parts = sorted(response.circuit.parts, key=lambda item: item.id)
        components = [
            AssemblyComponent(instanceId=part.id, assetSlug=part.component_key, label=part.label)
            for part in parts
        ]
        components.append(AssemblyComponent(
            instanceId=BREADBOARD_ID,
            assetSlug="breadboard-half",
            label="Half-size Breadboard",
        ))
        placements, placement_warnings = self._place(parts)
        connections, union = self._connect(response, placements)
        warnings = placement_warnings + self._validate(response, placements, connections, union)
        return AssemblyPlan(
            components=components,
            placements=placements,
            connections=connections,
            warnings=self._sort_warnings(warnings),
        )

    def _place(self, parts) -> tuple[list[Placement], list[AssemblyWarning]]:
        warnings: list[AssemblyWarning] = []
        placements = [Placement(
            componentId=BREADBOARD_ID,
            mode="board",
            transform=Transform(position=Vector3(x=0, y=0, z=0)),
        )]
        try:
            geometry = load_breadboard_geometry()
        except AssetMetadataError as exc:
            placements[0] = self._failed_placement(BREADBOARD_ID, "BREADBOARD_METADATA_MISSING")
            for part in parts:
                placements.append(self._failed_placement(part.id, "BREADBOARD_METADATA_MISSING"))
            warnings.append(self._warning(
                "BREADBOARD_METADATA_MISSING", "ERROR",
                "브레드보드 좌표 메타데이터를 불러오지 못해 부품을 배치할 수 없습니다.",
                [part.id for part in parts], "3D 자산 메타데이터 경로와 JSON 형식을 확인하세요.",
                {"reason": str(exc)},
            ))
            return placements, warnings

        allocator = BreadboardAllocator(geometry)
        for part in parts:
            if part.component_key == "arduino-uno-r3":
                placements.append(Placement(
                    componentId=part.id,
                    mode="free",
                    transform=Transform(position=Vector3(x=-0.12, y=0, z=0)),
                ))
                continue
            try:
                footprint = load_component_footprint(part.component_key)
            except AssetMetadataError as exc:
                placements.append(self._failed_placement(part.id, "ASSET_METADATA_MISSING"))
                warnings.append(self._warning(
                    "ASSET_METADATA_MISSING", "ERROR",
                    f"{part.label}의 3D 핀 메타데이터가 없어 배치하지 못했습니다.",
                    [part.id], "해당 assetSlug의 component metadata를 추가하세요.",
                    {"assetSlug": part.component_key, "reason": str(exc)},
                ))
                continue
            placement = allocator.allocate(part.id, footprint)
            if placement is None:
                placements.append(self._failed_placement(part.id, "NO_PLACEMENT_CANDIDATE"))
                warnings.append(self._warning(
                    "NO_PLACEMENT_CANDIDATE", "ERROR",
                    f"{part.label}의 다리 간격과 충돌 조건을 만족하는 빈 홀이 없습니다.",
                    [part.id], "브레드보드 공간을 확보하거나 부품 수를 줄이세요.",
                    {"assetSlug": part.component_key, "pinOffsets": list(footprint.offsets)},
                ))
                continue
            placements.append(placement)
            if not footprint.normalized:
                warnings.append(self._warning(
                    "ASSET_SCALE_UNCALIBRATED", "WARNING",
                    f"{part.label}은 미승인 좌표 자산이므로 공칭 2.54 mm 피치로 배치했습니다.",
                    [part.id], "실측 완료된 approved 3D metadata로 교체하세요.",
                    {"assetSlug": part.component_key},
                ))
        return placements, warnings

    @staticmethod
    def _failed_placement(component_id: str, code: str) -> Placement:
        return Placement(
            componentId=component_id,
            mode="breadboard",
            status="failed",
            failureCode=code,
            transform=Transform(position=Vector3(x=0, y=0, z=0)),
        )

    def _connect(self, response, placements) -> tuple[list[AssemblyConnection], _UnionFind]:
        union = _UnionFind()
        addresses = {placement.component_id: placement.addresses for placement in placements}
        occupied_holes = {
            address
            for pin_addresses in addresses.values()
            for address in pin_addresses.values()
        }
        used_wire_holes: set[str] = set()
        try:
            geometry = load_breadboard_geometry()
        except AssetMetadataError:
            geometry = None
        for component_id, pin_addresses in addresses.items():
            for pin, address in pin_addresses.items():
                if geometry is None:
                    continue
                terminal = parse_physical_address(address, geometry)
                pin_node = f"pin:{component_id}:{pin}"
                hole_node = f"hole:{terminal.canonical}"
                group_node = f"breadboard:{terminal.electrical_group}"
                union.union(pin_node, hole_node)
                union.union(hole_node, group_node)

        ordered = sorted(response.circuit.connections, key=lambda item: item.id)
        for item in ordered:
            union.union(f"pin:{item.source}:{item.source_pin}", f"pin:{item.target}:{item.target_pin}")

        connections = []
        parts_by_id = {part.id: part for part in response.circuit.parts}
        for item in ordered:
            source_node = f"pin:{item.source}:{item.source_pin}"
            source_pin_address = addresses.get(item.source, {}).get(item.source_pin)
            target_pin_address = addresses.get(item.target, {}).get(item.target_pin)
            source_part = parts_by_id.get(item.source)
            target_part = parts_by_id.get(item.target)
            connections.append(AssemblyConnection(
                id=item.id,
                source=ConnectionEndpoint(
                    componentId=item.source,
                    pin=item.source_pin,
                    address=_wire_hole_for_pin(
                        source_pin_address,
                        occupied_holes,
                        used_wire_holes,
                        source_part.component_key if source_part else None,
                    ),
                ),
                target=ConnectionEndpoint(
                    componentId=item.target,
                    pin=item.target_pin,
                    address=_wire_hole_for_pin(
                        target_pin_address,
                        occupied_holes,
                        used_wire_holes,
                        target_part.component_key if target_part else None,
                    ),
                ),
                electricalNode=f"node:{union.find(source_node)}",
                color=item.color,
            ))
        return connections, union

    def _validate(self, response, placements, connections, union) -> list[AssemblyWarning]:
        warnings: list[AssemblyWarning] = []
        parts = {part.id: part for part in response.circuit.parts}
        direct_pin_wires: dict[tuple[str, str], list[str]] = defaultdict(list)
        used_holes: dict[str, list[str]] = defaultdict(list)
        for placement in placements:
            for pin, address in placement.addresses.items():
                used_holes[address].append(f"{placement.component_id}:{pin}")
        for address, occupants in sorted(used_holes.items()):
            if len(occupants) > 1:
                warnings.append(self._warning(
                    "HOLE_OCCUPIED", "ERROR", f"브레드보드 {address} 홀에 다리가 중복 배치되었습니다.",
                    sorted({item.split(':')[0] for item in occupants}),
                    "한 홀에는 부품 다리 또는 점퍼 하나만 배치하세요.", {"address": address, "occupants": occupants},
                ))
        for connection in connections:
            direct_pin_wires[(connection.source.component_id, connection.source.pin)].append(connection.id)
            direct_pin_wires[(connection.target.component_id, connection.target.pin)].append(connection.id)
        for (component_id, pin), ids in sorted(direct_pin_wires.items()):
            if len(ids) > 1:
                warnings.append(self._warning(
                    "PIN_DUPLICATE", "WARNING", f"{component_id}의 {pin} 핀에 배선 {len(ids)}개가 직접 연결됩니다.",
                    [component_id], "브레드보드의 같은 전기 노드를 이용해 배선을 분산하세요.",
                    {"pin": pin, "connectionIds": sorted(ids)},
                ))

        board_parts = [part for part in parts.values() if part.component_key == "arduino-uno-r3"]
        power_roots, ground_roots = set(), set()
        for board in board_parts:
            power_roots.update(union.find(f"pin:{board.id}:{pin}") for pin in POWER_PINS)
            ground_roots.update(union.find(f"pin:{board.id}:{pin}") for pin in GROUND_PINS)
        if power_roots & ground_roots:
            warnings.append(self._warning(
                "POWER_GROUND_SHORT", "ERROR", "전원과 GND가 동일한 전기 노드에 연결되어 단락 위험이 있습니다.",
                [part.id for part in board_parts], "전원을 연결하기 전에 빨간색과 GND 배선을 분리하세요.",
            ))

        for part in sorted(parts.values(), key=lambda item: item.id):
            if part.component_key in LED_SLUGS:
                warnings.extend(self._validate_led(part.id, parts, union, power_roots, ground_roots))
            elif part.component_key == "hc-sr04":
                warnings.extend(self._validate_sensor(part.id, union, power_roots, ground_roots, board_parts))
        if not any(item.severity == "ERROR" for item in warnings):
            warnings.append(self._warning(
                "ASSEMBLY_VALID", "INFO", "실제 자산 좌표 기반 배치와 전기 연결에서 치명적인 오류가 없습니다.",
                suggestion="전원 인가 전에 실제 배선과 계획을 다시 비교하세요.",
            ))
        return warnings

    def _validate_led(self, component_id, parts, union, power_roots, ground_roots):
        warnings = []
        anode_root = union.find(f"pin:{component_id}:ANODE")
        cathode_root = union.find(f"pin:{component_id}:CATHODE")
        if anode_root in ground_roots or cathode_root in power_roots:
            warnings.append(self._warning(
                "LED_REVERSED", "ERROR", f"{component_id}의 LED 극성이 반대로 연결되었습니다.",
                [component_id], "ANODE는 출력/전원 쪽, CATHODE는 GND 쪽으로 연결하세요.",
            ))
        resistor_adjacent = False
        for part in parts.values():
            if part.component_key != "resistor-220-ohm":
                continue
            resistor_roots = {
                union.find(f"pin:{part.id}:LEAD_A"), union.find(f"pin:{part.id}:LEAD_B")
            }
            if anode_root in resistor_roots or cathode_root in resistor_roots:
                resistor_adjacent = True
                break
        if not resistor_adjacent:
            warnings.append(self._warning(
                "LED_RESISTOR_MISSING", "ERROR", f"{component_id}에 직렬 전류 제한 저항이 없습니다.",
                [component_id], "LED의 ANODE 또는 CATHODE 노드에 220Ω 저항을 직렬 연결하세요.",
            ))
        return warnings

    def _validate_sensor(self, component_id, union, power_roots, ground_roots, board_parts):
        warnings = []
        io_roots = {
            union.find(f"pin:{board.id}:{pin}") for board in board_parts for pin in IO_PINS
        }
        expectations = {
            "VCC": power_roots,
            "GND": ground_roots,
            "TRIG": io_roots,
            "ECHO": io_roots,
        }
        for pin, expected_roots in expectations.items():
            if union.find(f"pin:{component_id}:{pin}") not in expected_roots:
                warnings.append(self._warning(
                    "SENSOR_PIN_ROLE", "ERROR", f"{component_id}의 {pin} 핀이 올바른 Arduino 역할 핀에 연결되지 않았습니다.",
                    [component_id], "VCC/GND와 TRIG/ECHO의 핀 역할을 확인하세요.", {"pin": pin},
                ))
        return warnings

    @staticmethod
    def _warning(code, severity, message, component_ids=None, suggestion=None, details=None):
        return AssemblyWarning(
            code=code,
            severity=severity,
            message=message,
            suggestion=suggestion,
            details=details or {},
            componentIds=component_ids or [],
        )

    @staticmethod
    def _sort_warnings(warnings):
        order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        return sorted(warnings, key=lambda item: (order[item.severity], item.code, item.component_ids))
