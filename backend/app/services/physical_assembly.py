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
from app.services.component_rules import (
    component_category,
    component_mounting_mode,
    component_rule,
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

    ROW_ORDER = ("E", "J", "D", "I", "C", "H", "B", "G", "A", "F")
    SNAP_TOLERANCE_METER = 0.0015

    def __init__(self, geometry: BreadboardGeometry):
        self.geometry = geometry
        self.occupied_holes: set[str] = set()
        self.keep_outs: list[tuple[float, float, float, float]] = []

    def allocate(self, component_id: str, footprint: ComponentFootprint) -> Placement | None:
        for row in self.ROW_ORDER:
            for column in range(1, self.geometry.columns + 1):
                addresses = self._snap_addresses(row, column, footprint)
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

    def _snap_addresses(
        self,
        anchor_row: str,
        anchor_column: int,
        footprint: ComponentFootprint,
    ) -> dict[str, str] | None:
        if not footprint.pin_positions_meter:
            addresses = {
                pin: f"{anchor_row}{anchor_column + offset}"
                for pin, offset in zip(footprint.pins, footprint.offsets)
                if 1 <= anchor_column + offset <= self.geometry.columns
            }
            return addresses if len(addresses) == len(footprint.pins) else None

        anchor_x, _, anchor_z = self.geometry.hole_position(
            f"{anchor_row}{anchor_column}"
        )
        first_pin_x, first_pin_z = footprint.pin_positions_meter[0]
        addresses: dict[str, str] = {}
        for pin, (pin_x, pin_z) in zip(
            footprint.pins, footprint.pin_positions_meter
        ):
            target_x = anchor_x + pin_x - first_pin_x
            target_z = anchor_z + pin_z - first_pin_z
            nearest_column = round(
                (target_x - self.geometry.x_start_meter)
                / self.geometry.x_pitch_meter
            ) + 1
            if not 1 <= nearest_column <= self.geometry.columns:
                return None
            nearest_row = min(
                self.geometry.rows_z_meter,
                key=lambda candidate: abs(
                    self.geometry.rows_z_meter[candidate] - target_z
                ),
            )
            snapped_x, _, snapped_z = self.geometry.hole_position(
                f"{nearest_row}{nearest_column}"
            )
            distance = ((snapped_x - target_x) ** 2 + (snapped_z - target_z) ** 2) ** 0.5
            if distance > self.SNAP_TOLERANCE_METER:
                return None
            addresses[pin] = f"{nearest_row}{nearest_column}"
        if len(set(addresses.values())) != len(addresses):
            return None
        return addresses

    @staticmethod
    def _intersects(left, right) -> bool:
        return not (
            left[1] <= right[0] or left[0] >= right[1]
            or left[3] <= right[2] or left[2] >= right[3]
        )


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
        free_index = 0
        for part in parts:
            if component_mounting_mode(part.component_key) == "free":
                x = -0.12 if free_index == 0 else 0.12
                z = 0.06 * max(0, free_index - 1)
                placements.append(Placement(
                    componentId=part.id,
                    mode="free",
                    transform=Transform(position=Vector3(x=x, y=0, z=z)),
                ))
                free_index += 1
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

        for part in sorted(response.circuit.parts, key=lambda item: item.id):
            for pin_group in component_rule(part.component_key).get(
                "internalConnections", []
            ):
                first_pin = pin_group[0]
                for pin in pin_group[1:]:
                    union.union(
                        f"pin:{part.id}:{first_pin}",
                        f"pin:{part.id}:{pin}",
                    )

        ordered = sorted(response.circuit.connections, key=lambda item: item.id)
        for item in ordered:
            union.union(f"pin:{item.source}:{item.source_pin}", f"pin:{item.target}:{item.target_pin}")

        connections = []
        for item in ordered:
            source_node = f"pin:{item.source}:{item.source_pin}"
            connections.append(AssemblyConnection(
                id=item.id,
                source=ConnectionEndpoint(
                    componentId=item.source,
                    pin=item.source_pin,
                    address=addresses.get(item.source, {}).get(item.source_pin),
                ),
                target=ConnectionEndpoint(
                    componentId=item.target,
                    pin=item.target_pin,
                    address=addresses.get(item.target, {}).get(item.target_pin),
                ),
                electricalNode=f"node:{union.find(source_node)}",
                color=item.color,
            ))
        return connections, union

    def _validate_legacy(self, response, placements, connections, union) -> list[AssemblyWarning]:
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

    def _validate(self, response, placements, connections, union) -> list[AssemblyWarning]:
        warnings: list[AssemblyWarning] = []
        parts = {part.id: part for part in response.circuit.parts}
        warnings.extend(self._validate_placement_usage(placements))
        warnings.extend(self._validate_direct_wires(connections))

        board_parts = [
            part
            for part in parts.values()
            if component_category(part.component_key) == "controller"
        ]
        capability_roots = self._capability_roots(board_parts, union)
        root_capabilities: dict[str, set[str]] = defaultdict(set)
        for capability, roots in capability_roots.items():
            for root in roots:
                root_capabilities[root].add(capability)

        power_roots = capability_roots.get("power", set())
        ground_roots = capability_roots.get("ground", set())
        if power_roots & ground_roots:
            warnings.append(self._warning(
                "POWER_GROUND_SHORT",
                "ERROR",
                "Power and ground are connected to the same electrical node.",
                [part.id for part in board_parts],
                "Separate the power and ground wiring before applying power.",
            ))
        if capability_roots.get("power_5v", set()) & capability_roots.get(
            "power_3v3", set()
        ):
            warnings.append(self._warning(
                "POWER_DOMAIN_SHORT",
                "ERROR",
                "The 5 V and 3.3 V power domains are connected together.",
                [part.id for part in board_parts],
                "Keep the 5 V and 3.3 V rails on separate electrical nodes.",
            ))

        for part in sorted(parts.values(), key=lambda item: item.id):
            if component_category(part.component_key) == "controller":
                continue
            rule = component_rule(part.component_key)
            warnings.extend(self._validate_pin_requirements(
                part.id, rule, union, root_capabilities
            ))

            electrical_rules = rule.get("electricalRules", {})
            led_rule = electrical_rules.get("led")
            if led_rule:
                warnings.extend(self._validate_led_rule(
                    part.id,
                    parts,
                    union,
                    power_roots,
                    ground_roots,
                    root_capabilities,
                    led_rule,
                ))
            potentiometer_rule = electrical_rules.get("potentiometer")
            if potentiometer_rule:
                warnings.extend(self._validate_potentiometer_rule(
                    part.id,
                    union,
                    power_roots,
                    ground_roots,
                    potentiometer_rule,
                ))
            if electrical_rules.get("externalPowerRecommended"):
                warnings.append(self._warning(
                    "EXTERNAL_POWER_RECOMMENDED",
                    "WARNING",
                    f"{part.label} can draw more current than a controller pin "
                    "or USB supply should provide.",
                    [part.id],
                    "Use a suitable external 5 V supply and connect its ground "
                    "to the controller ground.",
                ))

        if not any(item.severity == "ERROR" for item in warnings):
            warnings.append(self._warning(
                "ASSEMBLY_VALID",
                "INFO",
                "No blocking placement or electrical rule violation was found.",
                suggestion="Compare the rendered assembly with the physical "
                "wiring once more before applying power.",
            ))
        return warnings

    def _validate_placement_usage(self, placements) -> list[AssemblyWarning]:
        warnings = []
        used_holes: dict[str, list[str]] = defaultdict(list)
        for placement in placements:
            for pin, address in placement.addresses.items():
                used_holes[address].append(f"{placement.component_id}:{pin}")
        for address, occupants in sorted(used_holes.items()):
            if len(occupants) > 1:
                warnings.append(self._warning(
                    "HOLE_OCCUPIED",
                    "ERROR",
                    f"Breadboard hole {address} is occupied more than once.",
                    sorted({item.split(":")[0] for item in occupants}),
                    "Place only one component lead or jumper end in each hole.",
                    {"address": address, "occupants": occupants},
                ))
        return warnings

    def _validate_direct_wires(self, connections) -> list[AssemblyWarning]:
        warnings = []
        direct_pin_wires: dict[tuple[str, str], list[str]] = defaultdict(list)
        for connection in connections:
            direct_pin_wires[
                (connection.source.component_id, connection.source.pin)
            ].append(connection.id)
            direct_pin_wires[
                (connection.target.component_id, connection.target.pin)
            ].append(connection.id)
        for (component_id, pin), ids in sorted(direct_pin_wires.items()):
            if len(ids) > 1:
                warnings.append(self._warning(
                    "PIN_DUPLICATE",
                    "WARNING",
                    f"{component_id}.{pin} has {len(ids)} direct jumper wires.",
                    [component_id],
                    "Fan out the connection through one shared breadboard node.",
                    {"pin": pin, "connectionIds": sorted(ids)},
                ))
        return warnings

    @staticmethod
    def _capability_roots(board_parts, union) -> dict[str, set[str]]:
        roots: dict[str, set[str]] = defaultdict(set)
        for board in board_parts:
            groups = component_rule(board.component_key).get(
                "capabilityGroups", {}
            )
            for capability, pins in groups.items():
                roots[capability].update(
                    union.find(f"pin:{board.id}:{pin}") for pin in pins
                )
        return roots

    def _validate_pin_requirements(
        self,
        component_id,
        rule,
        union,
        root_capabilities,
    ):
        warnings = []
        led_channels = set(
            rule.get("electricalRules", {}).get("led", {}).get(
                "channelPins", []
            )
        )
        for pin, requirement in sorted(
            rule.get("pinRequirements", {}).items()
        ):
            if pin in led_channels:
                continue
            root = union.find(f"pin:{component_id}:{pin}")
            connected = root_capabilities.get(root, set())
            required = set(requirement.get("requiresAny", []))
            preferred = set(requirement.get("preferredAny", []))
            if required and not required & connected:
                warnings.append(self._warning(
                    "PIN_CAPABILITY_MISMATCH",
                    "ERROR",
                    f"{component_id}.{pin} is not connected to a compatible "
                    "controller pin.",
                    [component_id],
                    f"Connect it to one of these capabilities: "
                    f"{', '.join(sorted(required))}.",
                    {
                        "pin": pin,
                        "requiredAny": sorted(required),
                        "connectedCapabilities": sorted(connected),
                    },
                ))
            elif preferred and not preferred & connected:
                warnings.append(self._warning(
                    "PIN_CAPABILITY_PREFERRED",
                    "WARNING",
                    f"{component_id}.{pin} works with the current connection, "
                    "but a preferred controller capability is available.",
                    [component_id],
                    f"Prefer one of these capabilities: "
                    f"{', '.join(sorted(preferred))}.",
                    {
                        "pin": pin,
                        "preferredAny": sorted(preferred),
                        "connectedCapabilities": sorted(connected),
                    },
                ))
        return warnings

    def _validate_led_rule(
        self,
        component_id,
        parts,
        union,
        power_roots,
        ground_roots,
        root_capabilities,
        led_rule,
    ):
        warnings = []
        ground_pin = led_rule["groundPin"]
        channel_pins = led_rule["channelPins"]
        ground_root = union.find(f"pin:{component_id}:{ground_pin}")
        channel_roots = {
            pin: union.find(f"pin:{component_id}:{pin}")
            for pin in channel_pins
        }
        if ground_root in power_roots or any(
            root in ground_roots for root in channel_roots.values()
        ):
            warnings.append(self._warning(
                "LED_REVERSED",
                "ERROR",
                f"{component_id} has reversed LED polarity.",
                [component_id],
                f"Connect {ground_pin} to ground and the channel pins through "
                "current-limiting resistors.",
            ))

        resistor_roots = set()
        for part in parts.values():
            if part.component_key != "resistor-220-ohm":
                continue
            resistor_roots.update({
                union.find(f"pin:{part.id}:LEAD_A"),
                union.find(f"pin:{part.id}:LEAD_B"),
            })

        for channel_pin, channel_root in channel_roots.items():
            channel_is_used = bool(
                root_capabilities.get(channel_root)
                or channel_root in resistor_roots
            )
            if not channel_is_used:
                continue
            if len(channel_pins) == 1:
                protected = bool(
                    {channel_root, ground_root} & resistor_roots
                )
            else:
                protected = channel_root in resistor_roots
            if not protected:
                warnings.append(self._warning(
                    "LED_RESISTOR_MISSING",
                    "ERROR",
                    f"{component_id}.{channel_pin} has no adjacent "
                    "current-limiting resistor.",
                    [component_id],
                    "Add one 220 ohm resistor in series with each used LED "
                    "channel.",
                    {"pin": channel_pin},
                ))
        return warnings

    def _validate_potentiometer_rule(
        self,
        component_id,
        union,
        power_roots,
        ground_roots,
        rule,
    ):
        terminal_roots = {
            union.find(f"pin:{component_id}:{pin}")
            for pin in rule["terminalPins"]
        }
        if terminal_roots & power_roots and terminal_roots & ground_roots:
            return []
        return [self._warning(
            "POTENTIOMETER_TERMINAL_ROLE",
            "ERROR",
            f"{component_id} must place its two outer terminals across power "
            "and ground.",
            [component_id],
            "Connect either outer terminal to power and the other to ground; "
            "connect WIPER to an analog input.",
        )]

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
