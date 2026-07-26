from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.schemas.assembly_plan import (
    AssemblyComponent, AssemblyConnection, AssemblyPlan, AssemblyWarning,
    ConnectionEndpoint, Placement, Transform, Vector3,
)
if TYPE_CHECKING:
    from app.schemas.circuit import CircuitGenerationResponse


BOARD_PIN_RE = re.compile(r"^(?:D(?:[0-9]|1[0-3])|A[0-5]|5V|3V3|VIN|GND(?:_[A-Z0-9]+)?|SDA|SCL|AREF|RESET|IOREF|AUX_[A-Z0-9_]+)$")
BREADBOARD_HOLE_RE = re.compile(r"^([A-J])([1-9]|[12][0-9]|30)$")
POWER_RAIL_RE = re.compile(r"^(?:(L|R)[-_]?)?([+-])([1-9]|[12][0-9]|30)$")
POWER_PINS = {"5V", "3V3", "VCC", "VIN", "AUX_5V", "AUX_3V3"}
GROUND_PINS = {"GND", "GND_D", "GND_P1", "GND_P2", "AUX_GND_1", "AUX_GND_2"}
IO_PINS = {f"D{i}" for i in range(14)} | {f"A{i}" for i in range(6)}
LED_SLUGS = {"led-5mm-blue", "led-5mm-red"}


@dataclass(frozen=True)
class ParsedAddress:
    kind: str
    canonical: str
    electrical_node: str


def parse_address(value: str) -> ParsedAddress:
    """Parse Arduino pins, A1-J30 holes, and optional L/R +/- rails."""
    address = value.strip().upper()
    explicit_board = address.startswith("BOARD:")
    if explicit_board:
        address = address.removeprefix("BOARD:")
    match = None if explicit_board else BREADBOARD_HOLE_RE.fullmatch(address)
    if match:
        row, column = match.groups()
        group = "ABCDE" if row <= "E" else "FGHIJ"
        return ParsedAddress("breadboard-hole", f"{row}{column}", f"bb:{group}:{column}")
    if BOARD_PIN_RE.fullmatch(address):
        normalized = "GND" if address in GROUND_PINS else address
        return ParsedAddress("board-pin", address, f"board:{normalized}")
    match = POWER_RAIL_RE.fullmatch(address)
    if match:
        side, polarity, column = match.groups()
        side = side or "L"
        return ParsedAddress("power-rail", f"{side}{polarity}{column}", f"bb:rail:{side}:{polarity}")
    raise ValueError(f"Unsupported physical address: {value}")


def generate_leg_candidates(asset_slug: str, anchor: str) -> list[dict[str, str]]:
    """Generate deterministic placements with matching component leg pitch."""
    parsed = parse_address(anchor)
    if parsed.kind != "breadboard-hole":
        raise ValueError("Leg candidates require an A1-J30 breadboard hole.")
    match = BREADBOARD_HOLE_RE.fullmatch(parsed.canonical)
    assert match is not None
    row, column_text = match.groups()
    column = int(column_text)
    definitions = {
        "led-5mm-blue": ((0, 1), ("ANODE", "CATHODE")),
        "led-5mm-red": ((0, 1), ("ANODE", "CATHODE")),
        "resistor-220-ohm": ((0, 3), ("LEAD_A", "LEAD_B")),
        "hc-sr04": ((0, 1, 2, 3), ("VCC", "TRIG", "ECHO", "GND")),
    }
    if asset_slug not in definitions:
        return []
    offsets, pins = definitions[asset_slug]
    if column + max(offsets) > 30:
        return []
    return [{pin: f"{row}{column + offset}" for pin, offset in zip(pins, offsets)}]


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


class AssemblyPlanEngine:
    """Build the same validated physical plan for the same circuit input."""

    def build(self, response: CircuitGenerationResponse) -> AssemblyPlan:
        parts = sorted(response.circuit.parts, key=lambda item: item.id)
        components = [AssemblyComponent(
            instanceId=part.id, assetSlug=part.component_key, label=part.label,
        ) for part in parts]
        placements = self._place(parts)
        connections = self._connect(response)
        warnings = self._validate(response, connections)
        return AssemblyPlan(components=components, placements=placements,
                            connections=connections, warnings=warnings)

    @staticmethod
    def _place(parts) -> list[Placement]:
        placements, occupied = [], []
        for part in parts:
            x = round(part.position.x / 20) * 0.02
            z = round(part.position.y / 20) * 0.02
            radius = max(0.45, part.width / 400)
            while any((x-ox)**2 + (z-oz)**2 < (radius+r)**2 for ox, oz, r in occupied):
                z = round(z + 0.5, 3)
            occupied.append((x, z, radius))
            placements.append(Placement(
                componentId=part.id,
                mode="board" if part.component_key == "arduino-uno-r3" else "free",
                transform=Transform(position=Vector3(x=x, y=0, z=z)),
            ))
        return placements

    @staticmethod
    def _connect(response) -> list[AssemblyConnection]:
        union = _UnionFind()
        ordered = sorted(response.circuit.connections, key=lambda item: item.id)
        for item in ordered:
            union.union(f"{item.source}:{item.source_pin}", f"{item.target}:{item.target_pin}")
        return [AssemblyConnection(
            id=item.id,
            source=ConnectionEndpoint(componentId=item.source, pin=item.source_pin),
            target=ConnectionEndpoint(componentId=item.target, pin=item.target_pin),
            electricalNode=f"node:{union.find(f'{item.source}:{item.source_pin}')}",
            color=item.color,
        ) for item in ordered]

    def _validate(self, response, connections) -> list[AssemblyWarning]:
        warnings, adjacency = [], defaultdict(set)
        pin_connections = defaultdict(list)
        parts = {part.id: part for part in response.circuit.parts}
        for connection in connections:
            source = (connection.source.component_id, connection.source.pin)
            target = (connection.target.component_id, connection.target.pin)
            adjacency[source].add(target); adjacency[target].add(source)
            pin_connections[source].append(connection.id); pin_connections[target].append(connection.id)
        for (component_id, pin), ids in sorted(pin_connections.items()):
            if len(ids) > 1:
                warnings.append(AssemblyWarning(
                    code="PIN_DUPLICATE", severity="WARNING",
                    message=f"{component_id}의 {pin} 핀에 배선 {len(ids)}개가 직접 연결됩니다.",
                    componentIds=[component_id], connectionIds=sorted(ids)))

        power_roots, ground_roots = set(), set()
        for endpoint in adjacency:
            component_id, pin = endpoint
            if parts[component_id].component_key != "arduino-uno-r3":
                continue
            root = self._reachable_key(endpoint, adjacency)
            if pin in POWER_PINS: power_roots.add(root)
            if pin in GROUND_PINS: ground_roots.add(root)
        if power_roots & ground_roots:
            warnings.append(AssemblyWarning(code="POWER_GROUND_SHORT", severity="ERROR",
                message="전원과 GND가 동일한 전기 노드에 연결되어 단락 위험이 있습니다."))

        for part in sorted(parts.values(), key=lambda item: item.id):
            if part.component_key in LED_SLUGS:
                self._check_led(part.id, adjacency, parts, warnings)
            if part.component_key == "hc-sr04":
                self._check_sensor(part.id, adjacency, parts, warnings)
        if not any(item.severity == "ERROR" for item in warnings):
            warnings.append(AssemblyWarning(code="ASSEMBLY_VALID", severity="INFO",
                message="배치 및 전기 연결에서 치명적인 오류가 발견되지 않았습니다."))
        return sorted(warnings, key=lambda item: (item.severity, item.code, item.component_ids))

    @staticmethod
    def _reachable_key(start, adjacency) -> str:
        visited, queue = set(), [start]
        while queue:
            current = queue.pop()
            if current in visited: continue
            visited.add(current); queue.extend(adjacency[current] - visited)
        return "|".join(f"{component}:{pin}" for component, pin in sorted(visited))

    @staticmethod
    def _connected_to_pin(start, adjacency, parts, pins) -> bool:
        visited, queue = set(), [start]
        while queue:
            current = queue.pop()
            if current in visited: continue
            visited.add(current)
            component_id, pin = current
            if parts[component_id].component_key == "arduino-uno-r3" and pin in pins:
                return True
            queue.extend(adjacency[current] - visited)
        return False

    def _check_led(self, component_id, adjacency, parts, warnings) -> None:
        anode, cathode = (component_id, "ANODE"), (component_id, "CATHODE")
        if (self._connected_to_pin(anode, adjacency, parts, GROUND_PINS) or
                self._connected_to_pin(cathode, adjacency, parts, POWER_PINS)):
            warnings.append(AssemblyWarning(code="LED_REVERSED", severity="ERROR",
                message=f"{component_id}의 LED 극성이 반대로 연결되었습니다.", componentIds=[component_id]))
        neighbors = {node[0] for endpoint in (anode, cathode) for node in adjacency[endpoint]}
        if not any(parts[item].component_key == "resistor-220-ohm" for item in neighbors):
            warnings.append(AssemblyWarning(code="LED_RESISTOR_MISSING", severity="ERROR",
                message=f"{component_id}에 직렬 전류 제한 저항이 없습니다.", componentIds=[component_id]))

    def _check_sensor(self, component_id, adjacency, parts, warnings) -> None:
        for pin, expected in {"VCC": POWER_PINS, "GND": GROUND_PINS,
                              "TRIG": IO_PINS, "ECHO": IO_PINS}.items():
            if not self._connected_to_pin((component_id, pin), adjacency, parts, expected):
                warnings.append(AssemblyWarning(code="SENSOR_PIN_ROLE", severity="ERROR",
                    message=f"{component_id}의 {pin} 핀이 올바른 Arduino 역할 핀에 연결되지 않았습니다.",
                    componentIds=[component_id]))
