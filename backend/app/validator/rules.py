"""
LOOKEY 3팀 회로 검증 모듈 — rules.py (검증 로직 담당)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .adapter import (
    CircuitJson,
    Connection,
    _to_lower,
    convert_edges_to_connections,
    extract_used_pins_from_code,
    get_connected_pins_by_node,
    get_hardware_io_pins,
    is_io_pin,
    load_circuit_json,
    normalize_pin,
)

ValidationResult = Dict[str, Any]


def _is_power_pin(pin: Any) -> bool:
    return normalize_pin(pin) in {"5V", "3.3V", "VCC"}


def _is_gnd_pin(pin: Any) -> bool:
    return normalize_pin(pin) == "GND"


def _component_text(*values: Any) -> str:
    return " ".join(_to_lower(v) for v in values if v is not None)


def _is_led_component(text: str) -> bool:
    return "led" in text


def _is_resistor_component(text: str) -> bool:
    return "resistor" in text or "저항" in text


def _is_board_component(text: str) -> bool:
    return ("arduino" in text or "uno" in text or "nano" in text
            or "esp32" in text or "raspberry" in text or "board" in text)


def _is_passive_component(text: str) -> bool:
    return _is_resistor_component(text) or "capacitor" in text or "커패시터" in text


def check_required_fields(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    has_nodes_edges = "nodes" in circuit_json and "edges" in circuit_json
    has_connections = "connections" in circuit_json
    has_task_result_format = "components" in circuit_json and "circuit_connections" in circuit_json
    has_circuit_object = isinstance(circuit_json.get("circuit"), dict) and "connections" in circuit_json["circuit"]

    if not (has_nodes_edges or has_connections or has_task_result_format or has_circuit_object):
        return {"ruleId": "R002", "level": "ERROR", "title": "회로 JSON 필수 필드 누락",
                "message": "회로 JSON에 nodes/edges, connections, components/circuit_connections, 또는 circuit.parts/connections 정보가 없습니다.",
                "target": {}}
    return None


def check_short_circuit(connections: List[Connection]) -> Optional[ValidationResult]:
    for conn in connections:
        f_pin = normalize_pin(conn.get("from_pin"))
        t_pin = normalize_pin(conn.get("to_pin"))
        if (_is_power_pin(f_pin) and _is_gnd_pin(t_pin)) or (_is_gnd_pin(f_pin) and _is_power_pin(t_pin)):
            return {"ruleId": "R004", "level": "ERROR", "title": "VCC-GND 직접 단락",
                    "message": (f"{conn.get('from_component')}의 {conn.get('from_pin')} 핀과 "
                                 f"{conn.get('to_component')}의 {conn.get('to_pin')} 핀이 직접 연결되어 있어요. "
                                 "전원과 GND를 바로 연결하면 보드가 손상될 수 있습니다."),
                    "target": {"edge_id": conn.get("edge_id"), "from_component": conn.get("from_component"),
                               "from_pin": conn.get("from_pin"), "to_component": conn.get("to_component"),
                               "to_pin": conn.get("to_pin")}}
    return None


def check_led_resistor(connections: List[Connection]) -> Optional[ValidationResult]:
    has_led = has_resistor = False
    for conn in connections:
        text = _component_text(conn.get("from_component"), conn.get("to_component"),
                                conn.get("from_component_key"), conn.get("to_component_key"))
        if _is_led_component(text):
            has_led = True
        if _is_resistor_component(text):
            has_resistor = True
    if has_led and not has_resistor:
        return {"ruleId": "R006", "level": "ERROR", "title": "LED 전류 제한 저항 누락",
                "message": ("회로에 LED가 있지만 전류를 제한해 줄 저항이 보이지 않아요. "
                             "LED를 보드 핀에 직접 연결하면 LED가 손상될 수 있으니, LED와 직렬로 저항을 추가하세요."),
                "target": {}}
    return None


def check_unknown_components(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    nodes = circuit_json.get("nodes", [])
    if not isinstance(nodes, list):
        return None
    unknown_nodes = [n.get("id") for n in nodes if not n.get("componentKey") and not n.get("label")]
    if unknown_nodes:
        return {"ruleId": "R003", "level": "WARNING", "title": "알 수 없는 부품 정보",
                "message": "일부 부품의 이름이나 componentKey가 비어 있어요.",
                "target": {"node_ids": unknown_nodes}}
    return None


def check_pin_mismatch(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    # GND/VCC 등은 pinMode()로 설정하는 핀이 아니라서(배선상 참조일 뿐)
    # codeMeta.used_pins에 섞여 있어도 이 검사에서는 제외한다.
    used_pins_in_code = [p for p in extract_used_pins_from_code(circuit_json) if is_io_pin(p)]
    if not used_pins_in_code:
        return None
    hardware_pins = get_hardware_io_pins(connections)
    for code_pin in used_pins_in_code:
        if code_pin not in hardware_pins:
            return {"ruleId": "R011", "level": "WARNING", "title": "코드와 회로 핀 불일치",
                    "message": (f"코드에서는 {code_pin} 핀을 사용하지만, 실제 회로 연결에서는 {code_pin} 핀이 보이지 않아요. "
                                 "코드의 핀 번호와 회로의 연결 핀을 맞춰주세요."),
                    "target": {"code_pin": code_pin, "hardware_pins": hardware_pins}}
    return None


def check_unused_hardware_pin(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    used_pins_in_code = [p for p in extract_used_pins_from_code(circuit_json) if is_io_pin(p)]
    if not used_pins_in_code:
        return None
    hardware_pins = get_hardware_io_pins(connections)
    for hardware_pin in hardware_pins:
        if hardware_pin not in used_pins_in_code:
            return {"ruleId": "R012", "level": "INFO", "title": "회로 핀이 코드에서 사용되지 않음",
                    "message": f"회로에는 {hardware_pin} 핀이 연결되어 있지만 코드에서는 이 핀을 사용하지 않는 것 같아요.",
                    "target": {"hardware_pin": hardware_pin, "used_pins_in_code": used_pins_in_code}}
    return None


def check_missing_power_or_gnd(connections: List[Connection]) -> Optional[ValidationResult]:
    connected_pins = get_connected_pins_by_node(connections)
    seen: set = set()
    for conn in connections:
        for instance_id, component_key in (
            (conn.get("from_component"), conn.get("from_component_key")),
            (conn.get("to_component"), conn.get("to_component_key")),
        ):
            if not instance_id or instance_id in seen:
                continue
            seen.add(instance_id)
            text = _component_text(instance_id, component_key)
            if _is_board_component(text) or _is_passive_component(text) or _is_led_component(text):
                continue
            pins = connected_pins.get(instance_id, [])
            has_power = any(_is_power_pin(pin) for pin in pins)
            has_gnd = any(_is_gnd_pin(pin) for pin in pins)
            if not has_power:
                return {"ruleId": "R007", "level": "WARNING", "title": "부품 전원 연결 확인 필요",
                        "message": f"{instance_id} 부품에 전원 핀 연결이 보이지 않아요.",
                        "target": {"component": instance_id, "connected_pins": pins}}
            if not has_gnd:
                return {"ruleId": "R008", "level": "WARNING", "title": "부품 GND 연결 확인 필요",
                        "message": f"{instance_id} 부품에 GND 연결이 보이지 않아요.",
                        "target": {"component": instance_id, "connected_pins": pins}}
    return None


def check_duplicate_pin_usage(connections: List[Connection]) -> Optional[ValidationResult]:
    pin_usage: Dict[str, List[str]] = {}
    for conn in connections:
        for side in ["from", "to"]:
            component = conn.get(f"{side}_component")
            component_key = conn.get(f"{side}_component_key")
            pin = conn.get(f"{side}_pin")
            edge_id = conn.get("edge_id")
            text = _component_text(component, component_key)
            if _is_board_component(text) and is_io_pin(pin):
                normalized_pin = normalize_pin(pin)
                pin_usage.setdefault(normalized_pin, []).append(str(edge_id))
    for pin, edge_ids in pin_usage.items():
        if len(edge_ids) >= 2:
            return {"ruleId": "R010", "level": "INFO", "title": "하나의 보드 핀에 여러 연결",
                    "message": f"{pin} 핀에 여러 연결이 감지되었어요.",
                    "target": {"pin": pin, "edge_ids": edge_ids}}
    return None


def validate_circuit(circuit_input: Union[str, Path, CircuitJson]) -> List[ValidationResult]:
    try:
        circuit_json = load_circuit_json(circuit_input)
    except Exception as error:
        return [{"ruleId": "R001", "level": "ERROR", "title": "JSON 형식 오류",
                 "message": f"올바르지 않은 JSON 입력입니다. 상세: {error}", "target": {}}]

    required_result = check_required_fields(circuit_json)
    if required_result:
        return [required_result]

    connections = convert_edges_to_connections(circuit_json)
    rule_results = [
        check_unknown_components(circuit_json),
        check_short_circuit(connections),
        check_led_resistor(connections),
        check_missing_power_or_gnd(connections),
        check_duplicate_pin_usage(connections),
        check_pin_mismatch(connections, circuit_json),
        check_unused_hardware_pin(connections, circuit_json),
    ]
    results = [r for r in rule_results if r]
    if not results:
        return [{"is_valid": True, "ruleId": "PASS", "level": "PASS", "title": "기본 검증 통과",
                 "message": "기본 회로 안전 검사를 통과했습니다.", "target": {}}]
    return results


def to_api_shape(results: List[ValidationResult]) -> List[Dict[str, str]]:
    """
    내부 검증 결과(title/target 등 부가정보 포함)를 실제 K-EXAONE API 응답
    스키마(ruleId/level/message 3개 필드만)로 변환한다.
    """
    return [
        {"ruleId": r.get("ruleId", ""), "level": r.get("level", ""), "message": r.get("message", "")}
        for r in results
    ]


def validate_and_attach(circuit_input: Union[str, Path, CircuitJson]) -> CircuitJson:
    circuit_json = load_circuit_json(circuit_input)
    validation_results = validate_circuit(circuit_json)
    circuit_json["validationResults"] = to_api_shape(validation_results)
    existing_warnings = circuit_json.get("warnings", [])
    if not isinstance(existing_warnings, list):
        existing_warnings = []
    warning_messages = [r.get("message") for r in validation_results
                         if r.get("level") in {"ERROR", "WARNING"} and r.get("message")]
    circuit_json["warnings"] = existing_warnings + warning_messages
    return circuit_json