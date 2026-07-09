"""
LOOKEY 3팀 회로 검증 모듈 — rules.py (검증 로직 담당)

역할:
1. 회로 안전 규칙을 검사한다.
2. 기존 JSON에 validationResults를 붙여 반환한다.

JSON 로딩/nodes+edges 변환/코드 핀 추출은 adapter.py에서 가져다 씁니다.

주요 사용 함수:
- validate_circuit(circuit_json)
- validate_and_attach(circuit_json)
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


# =========================================================
# 부품 분류 유틸 (검증 로직 전용)
# =========================================================

def _is_power_pin(pin: Any) -> bool:
    return normalize_pin(pin) in {"5V", "3.3V", "VCC"}


def _is_gnd_pin(pin: Any) -> bool:
    return normalize_pin(pin) == "GND"


def _component_text(*values: Any) -> str:
    """컴포넌트명, key 등을 합쳐서 검색하기 쉽게 만든다."""
    return " ".join(_to_lower(v) for v in values if v is not None)


def _is_led_component(text: str) -> bool:
    return "led" in text


def _is_resistor_component(text: str) -> bool:
    return "resistor" in text or "저항" in text


def _is_board_component(text: str) -> bool:
    return (
        "arduino" in text
        or "uno" in text
        or "nano" in text
        or "esp32" in text
        or "raspberry" in text
        or "board" in text
    )


def _is_passive_component(text: str) -> bool:
    return _is_resistor_component(text) or "capacitor" in text or "커패시터" in text


# =========================================================
# 검증 규칙들
# =========================================================

def check_required_fields(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """[R002] 필수 필드 누락 검사"""
    has_nodes_edges = "nodes" in circuit_json and "edges" in circuit_json
    has_connections = "connections" in circuit_json

    if not has_nodes_edges and not has_connections:
        return {
            "rule": "R002",
            "grade": "ERROR",
            "title": "회로 JSON 필수 필드 누락",
            "feedback": "회로 JSON에 nodes/edges 또는 connections 정보가 없습니다. 회로 연결 정보를 먼저 생성해야 합니다.",
            "target": {},
        }

    return None


def check_short_circuit(connections: List[Connection]) -> Optional[ValidationResult]:
    """[R004] VCC-GND 직접 단락 검사"""
    for conn in connections:
        f_pin = normalize_pin(conn.get("from_pin"))
        t_pin = normalize_pin(conn.get("to_pin"))

        if (_is_power_pin(f_pin) and _is_gnd_pin(t_pin)) or (_is_gnd_pin(f_pin) and _is_power_pin(t_pin)):
            return {
                "rule": "R004",
                "grade": "ERROR",
                "title": "VCC-GND 직접 단락",
                "feedback": (
                    f"{conn.get('from_component')}의 {conn.get('from_pin')} 핀과 "
                    f"{conn.get('to_component')}의 {conn.get('to_pin')} 핀이 직접 연결되어 있어요. "
                    "전원과 GND를 바로 연결하면 보드가 손상될 수 있습니다."
                ),
                "target": {
                    "edge_id": conn.get("edge_id"),
                    "from_component": conn.get("from_component"),
                    "from_pin": conn.get("from_pin"),
                    "to_component": conn.get("to_component"),
                    "to_pin": conn.get("to_pin"),
                },
            }

    return None


def check_led_resistor(connections: List[Connection]) -> Optional[ValidationResult]:
    """[R006] LED 전류 제한 저항 누락 검사"""
    has_led = False
    has_resistor = False

    for conn in connections:
        text = _component_text(
            conn.get("from_component"),
            conn.get("to_component"),
            conn.get("from_component_key"),
            conn.get("to_component_key"),
        )

        if _is_led_component(text):
            has_led = True

        if _is_resistor_component(text):
            has_resistor = True

    if has_led and not has_resistor:
        return {
            "rule": "R006",
            "grade": "ERROR",
            "title": "LED 전류 제한 저항 누락",
            "feedback": (
                "회로에 LED가 있지만 전류를 제한해 줄 저항이 보이지 않아요. "
                "LED를 보드 핀에 직접 연결하면 LED가 손상될 수 있으니, LED와 직렬로 저항을 추가하세요."
            ),
            "target": {},
        }

    return None


def check_unknown_components(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """[R003] 알 수 없는 부품 정보 검사"""
    nodes = circuit_json.get("nodes", [])
    if not isinstance(nodes, list):
        return None

    unknown_nodes = []

    for node in nodes:
        component_key = node.get("componentKey")
        label = node.get("label")

        if not component_key and not label:
            unknown_nodes.append(node.get("id"))

    if unknown_nodes:
        return {
            "rule": "R003",
            "grade": "WARNING",
            "title": "알 수 없는 부품 정보",
            "feedback": (
                "일부 부품의 이름이나 componentKey가 비어 있어요. "
                "검증 정확도를 높이려면 각 부품에 label 또는 componentKey를 넣어주세요."
            ),
            "target": {"node_ids": unknown_nodes},
        }

    return None


def check_pin_mismatch(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """[R011] 코드-회로 핀 불일치 검사"""
    used_pins_in_code = extract_used_pins_from_code(circuit_json)
    if not used_pins_in_code:
        return None

    hardware_pins = get_hardware_io_pins(connections)

    for code_pin in used_pins_in_code:
        if code_pin not in hardware_pins:
            return {
                "rule": "R011",
                "grade": "WARNING",
                "title": "코드와 회로 핀 불일치",
                "feedback": (
                    f"코드에서는 {code_pin} 핀을 사용하지만, 실제 회로 연결에서는 {code_pin} 핀이 보이지 않아요. "
                    "코드의 핀 번호와 회로의 연결 핀을 맞춰주세요."
                ),
                "target": {"code_pin": code_pin, "hardware_pins": hardware_pins},
            }

    return None


def check_unused_hardware_pin(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """[R012] 회로에는 연결되어 있는데 코드에서 사용하지 않는 핀 검사"""
    used_pins_in_code = extract_used_pins_from_code(circuit_json)
    if not used_pins_in_code:
        return None

    hardware_pins = get_hardware_io_pins(connections)

    for hardware_pin in hardware_pins:
        if hardware_pin not in used_pins_in_code:
            return {
                "rule": "R012",
                "grade": "INFO",
                "title": "회로 핀이 코드에서 사용되지 않음",
                "feedback": (
                    f"회로에는 {hardware_pin} 핀이 연결되어 있지만 코드에서는 이 핀을 사용하지 않는 것 같아요. "
                    "의도한 연결인지 확인해보세요."
                ),
                "target": {"hardware_pin": hardware_pin, "used_pins_in_code": used_pins_in_code},
            }

    return None


def check_missing_power_or_gnd(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """[R007/R008] 부품 전원 또는 GND 미연결 검사"""
    nodes = circuit_json.get("nodes", [])
    if not isinstance(nodes, list):
        return None

    connected_pins = get_connected_pins_by_node(circuit_json)

    for node in nodes:
        node_id = str(node.get("id") or "")
        label = node.get("label")
        component_key = node.get("componentKey")
        node_type = node.get("type")

        text = _component_text(label, component_key, node_type)

        if _is_board_component(text) or _is_passive_component(text) or _is_led_component(text):
            continue

        if node_type not in {"input", "output", "power"}:
            continue

        pins = connected_pins.get(node_id, [])

        has_power = any(_is_power_pin(pin) for pin in pins)
        has_gnd = any(_is_gnd_pin(pin) for pin in pins)

        if not has_power:
            return {
                "rule": "R007",
                "grade": "WARNING",
                "title": "부품 전원 연결 확인 필요",
                "feedback": (
                    f"{label or component_key or node_id} 부품에 전원 핀 연결이 보이지 않아요. "
                    "센서나 모듈이라면 VCC, 5V, 3.3V 중 필요한 전원을 연결해야 합니다."
                ),
                "target": {"node_id": node_id, "component": label or component_key, "connected_pins": pins},
            }

        if not has_gnd:
            return {
                "rule": "R008",
                "grade": "WARNING",
                "title": "부품 GND 연결 확인 필요",
                "feedback": (
                    f"{label or component_key or node_id} 부품에 GND 연결이 보이지 않아요. "
                    "대부분의 센서와 모듈은 보드와 GND를 공통으로 연결해야 정상 동작합니다."
                ),
                "target": {"node_id": node_id, "component": label or component_key, "connected_pins": pins},
            }

    return None


def check_duplicate_pin_usage(connections: List[Connection]) -> Optional[ValidationResult]:
    """[R010] 같은 보드 IO 핀에 여러 연결이 몰린 경우 검사"""
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
            return {
                "rule": "R010",
                "grade": "INFO",
                "title": "하나의 보드 핀에 여러 연결",
                "feedback": (
                    f"{pin} 핀에 여러 연결이 감지되었어요. "
                    "의도한 병렬 연결인지, 아니면 잘못 연결된 선이 있는지 확인해보세요."
                ),
                "target": {"pin": pin, "edge_ids": edge_ids},
            }

    return None


# =========================================================
# 전체 검증 실행 함수
# =========================================================

def validate_circuit(circuit_input: Union[str, Path, CircuitJson]) -> List[ValidationResult]:
    """회로 JSON을 검증하고 validation result 리스트를 반환한다."""
    try:
        circuit_json = load_circuit_json(circuit_input)
    except Exception as error:
        return [{
            "rule": "R001",
            "grade": "ERROR",
            "title": "JSON 형식 오류",
            "feedback": f"올바르지 않은 JSON 입력입니다. 입력 데이터를 다시 확인해주세요. 상세: {error}",
            "target": {},
        }]

    results: List[ValidationResult] = []

    required_result = check_required_fields(circuit_json)
    if required_result:
        return [required_result]

    connections = convert_edges_to_connections(circuit_json)

    rule_results = [
        check_unknown_components(circuit_json),
        check_short_circuit(connections),
        check_led_resistor(connections),
        check_missing_power_or_gnd(circuit_json),
        check_duplicate_pin_usage(connections),
        check_pin_mismatch(connections, circuit_json),
        check_unused_hardware_pin(connections, circuit_json),
    ]

    for result in rule_results:
        if result:
            results.append(result)

    if not results:
        return [{
            "is_valid": True,
            "rule": "PASS",
            "grade": "PASS",
            "title": "기본 검증 통과",
            "feedback": "기본 회로 안전 검사를 통과했습니다.",
            "target": {},
        }]

    return results


def validate_and_attach(circuit_input: Union[str, Path, CircuitJson]) -> CircuitJson:
    """회로 JSON을 검증한 뒤, 기존 JSON에 validationResults 필드를 붙여 반환한다."""
    circuit_json = load_circuit_json(circuit_input)
    validation_results = validate_circuit(circuit_json)

    circuit_json["validationResults"] = validation_results

    existing_warnings = circuit_json.get("warnings", [])
    if not isinstance(existing_warnings, list):
        existing_warnings = []

    warning_messages = [
        result.get("feedback")
        for result in validation_results
        if result.get("grade") in {"ERROR", "WARNING"} and result.get("feedback")
    ]

    circuit_json["warnings"] = existing_warnings + warning_messages

    return circuit_json