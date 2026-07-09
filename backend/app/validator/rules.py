"""
LOOKEY 3팀 회로 규칙 검증 모듈

역할:
1. 1팀/AI팀이 만든 회로 JSON을 입력받는다.
2. nodes, edges 구조를 검증하기 쉬운 connections 구조로 변환한다.
3. 회로 안전 규칙을 검사한다.
4. 기존 JSON에 validationResults를 붙여 반환한다.

주요 사용 함수:
- validate_circuit(circuit_json)
- validate_and_attach(circuit_json)
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


CircuitJson = Dict[str, Any]
Connection = Dict[str, Any]
ValidationResult = Dict[str, Any]


# =========================================================
# 공통 유틸 함수
# =========================================================

def _to_upper(value: Any) -> str:
    """None 방어 + 문자열 대문자 변환"""
    return str(value or "").strip().upper()


def _to_lower(value: Any) -> str:
    """None 방어 + 문자열 소문자 변환"""
    return str(value or "").strip().lower()


def _normalize_pin(pin: Any) -> str:
    """
    핀 이름 정규화.
    예:
    gnd -> GND
    ground -> GND
    +5v -> 5V
    vcc -> VCC
    d3 -> D3
    """
    raw = _to_upper(pin)

    aliases = {
        "GROUND": "GND",
        "0V": "GND",
        "GND1": "GND",
        "+5V": "5V",
        "5 V": "5V",
        "+3.3V": "3.3V",
        "3V3": "3.3V",
        "VDD": "VCC",
    }

    return aliases.get(raw, raw)


def _is_power_pin(pin: Any) -> bool:
    return _normalize_pin(pin) in {"5V", "3.3V", "VCC"}


def _is_gnd_pin(pin: Any) -> bool:
    return _normalize_pin(pin) == "GND"


def _is_io_pin(pin: Any) -> bool:
    """
    Arduino 계열 입출력 핀 판별.
    D3, D10, A0, A1 같은 핀을 잡는다.
    """
    normalized = _normalize_pin(pin)
    return bool(re.fullmatch(r"[DA]\d+", normalized))


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
# JSON 로딩 함수
# =========================================================

def load_circuit_json(source: Union[str, Path, CircuitJson]) -> CircuitJson:
    """
    회로 JSON을 로드한다.

    가능한 입력:
    1. dict 형태 JSON
    2. JSON 문자열
    3. JSON 파일 경로

    예:
    load_circuit_json({"nodes": [], "edges": []})
    load_circuit_json('{"nodes": [], "edges": []}')
    load_circuit_json("sample_circuit.json")
    """
    if isinstance(source, dict):
        return source

    if isinstance(source, Path):
        with source.open("r", encoding="utf-8") as file:
            return json.load(file)

    if isinstance(source, str):
        stripped = source.strip()

        # JSON 문자열인 경우
        if stripped.startswith("{") or stripped.startswith("["):
            loaded = json.loads(stripped)
            if not isinstance(loaded, dict):
                raise ValueError("회로 JSON의 최상위 구조는 object/dict여야 합니다.")
            return loaded

        # 파일 경로인 경우
        path = Path(source)
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)

    raise ValueError("지원하지 않는 JSON 입력 형식입니다.")


# =========================================================
# 1팀 JSON 구조 변환
# =========================================================

def build_node_map(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    nodes 배열을 id 기준 dictionary로 변환한다.

    입력:
    [
      {"id": "arduino-1", "label": "Arduino Uno"},
      {"id": "led-1", "label": "Red LED"}
    ]

    출력:
    {
      "arduino-1": {"id": "arduino-1", ...},
      "led-1": {"id": "led-1", ...}
    }
    """
    node_map: Dict[str, Dict[str, Any]] = {}

    for node in nodes:
        node_id = node.get("id")
        if node_id:
            node_map[str(node_id)] = node

    return node_map


def convert_edges_to_connections(circuit_json: CircuitJson) -> List[Connection]:
    """
    1팀/프론트엔드가 쓰는 nodes + edges 구조를
    우리 검증 규칙에서 쓰기 쉬운 connections 구조로 변환한다.

    입력 edge:
    {
      "id": "edge-1",
      "source": "arduino-1",
      "target": "led-1",
      "sourceHandle": "D3",
      "targetHandle": "anode"
    }

    출력 connection:
    {
      "edge_id": "edge-1",
      "from_component": "Arduino Uno",
      "from_pin": "D3",
      "to_component": "Red LED",
      "to_pin": "anode"
    }
    """
    # 이미 connections 구조로 들어오면 그대로 사용
    if "connections" in circuit_json and isinstance(circuit_json["connections"], list):
        return circuit_json["connections"]

    nodes = circuit_json.get("nodes", [])
    edges = circuit_json.get("edges", [])

    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    node_map = build_node_map(nodes)
    connections: List[Connection] = []

    for edge in edges:
        source_id = edge.get("source")
        target_id = edge.get("target")

        source_node = node_map.get(str(source_id), {})
        target_node = node_map.get(str(target_id), {})

        from_component = (
            source_node.get("label")
            or source_node.get("componentKey")
            or source_id
            or "UNKNOWN_SOURCE"
        )
        to_component = (
            target_node.get("label")
            or target_node.get("componentKey")
            or target_id
            or "UNKNOWN_TARGET"
        )

        connections.append(
            {
                "edge_id": edge.get("id"),
                "from_node_id": source_id,
                "to_node_id": target_id,
                "from_component": from_component,
                "from_component_key": source_node.get("componentKey"),
                "from_component_type": source_node.get("type"),
                "from_pin": edge.get("sourceHandle"),
                "to_component": to_component,
                "to_component_key": target_node.get("componentKey"),
                "to_component_type": target_node.get("type"),
                "to_pin": edge.get("targetHandle"),
                "label": edge.get("label"),
            }
        )

    return connections


def get_connected_pins_by_node(circuit_json: CircuitJson) -> Dict[str, List[str]]:
    """
    node id별로 연결된 핀 목록을 만든다.

    출력 예:
    {
      "arduino-1": ["5V", "GND", "D3"],
      "led-1": ["anode", "cathode"]
    }
    """
    connected: Dict[str, List[str]] = {}

    edges = circuit_json.get("edges", [])
    if not isinstance(edges, list):
        return connected

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        source_handle = edge.get("sourceHandle")
        target_handle = edge.get("targetHandle")

        if source:
            connected.setdefault(str(source), []).append(_normalize_pin(source_handle))
        if target:
            connected.setdefault(str(target), []).append(_normalize_pin(target_handle))

    return connected


# =========================================================
# 코드에서 사용한 핀 추출
# =========================================================

def extract_used_pins_from_code(circuit_json: CircuitJson) -> List[str]:
    """
    codeMeta.used_pins가 있으면 우선 사용한다.
    없으면 code 문자열에서 pinMode/digitalWrite/digitalRead/analogRead를 간단히 파싱한다.

    지원 예:
    pinMode(3, OUTPUT)      -> D3
    digitalWrite(5, HIGH)   -> D5
    digitalRead(7)          -> D7
    analogRead(A0)          -> A0
    """
    # 1. codeMeta.used_pins 우선 사용
    code_meta = circuit_json.get("codeMeta") or circuit_json.get("code_meta") or {}
    if isinstance(code_meta, dict):
        used_pins = code_meta.get("used_pins")
        if isinstance(used_pins, list):
            return sorted({_normalize_pin(pin) for pin in used_pins})

    # 2. code.used_pins 구조 지원
    code_obj = circuit_json.get("code")
    if isinstance(code_obj, dict):
        used_pins = code_obj.get("used_pins")
        if isinstance(used_pins, list):
            return sorted({_normalize_pin(pin) for pin in used_pins})

    # 3. code 문자열 파싱
    code = circuit_json.get("code", "")
    if not isinstance(code, str):
        return []

    found_pins = set()

    patterns = [
        r"pinMode\s*\(\s*([A-Za-z]?\d+)",
        r"digitalWrite\s*\(\s*([A-Za-z]?\d+)",
        r"digitalRead\s*\(\s*([A-Za-z]?\d+)",
        r"analogRead\s*\(\s*([A-Za-z]?\d+)",
        r"analogWrite\s*\(\s*([A-Za-z]?\d+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, code)
        for match in matches:
            pin = str(match).strip().upper()

            # 숫자만 있으면 Arduino 디지털 핀으로 간주
            if pin.isdigit():
                pin = f"D{pin}"

            found_pins.add(_normalize_pin(pin))

    return sorted(found_pins)


def get_hardware_io_pins(connections: List[Connection]) -> List[str]:
    """
    실제 회로 연결에서 D/A 핀 목록 추출.
    """
    hardware_pins = set()

    for conn in connections:
        for pin in [conn.get("from_pin"), conn.get("to_pin")]:
            normalized = _normalize_pin(pin)
            if _is_io_pin(normalized):
                hardware_pins.add(normalized)

    return sorted(hardware_pins)


# =========================================================
# 검증 규칙들
# =========================================================

def check_required_fields(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """
    [R002] 필수 필드 누락 검사
    """
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
    """
    [R004] VCC-GND 직접 단락 검사
    """
    for conn in connections:
        f_pin = _normalize_pin(conn.get("from_pin"))
        t_pin = _normalize_pin(conn.get("to_pin"))

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
    """
    [R006] LED 전류 제한 저항 누락 검사

    1차 버전:
    회로 전체에 LED는 있는데 Resistor가 하나도 없으면 오류.
    """
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
    """
    [R003] 알 수 없는 부품 정보 검사

    componentKey와 label이 모두 비어 있으면 경고.
    """
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
            "target": {
                "node_ids": unknown_nodes,
            },
        }

    return None


def check_pin_mismatch(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """
    [R011] 코드-회로 핀 불일치 검사

    코드에서 D5를 쓰는데 실제 회로에는 D5 연결이 없으면 WARNING.
    """
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
                "target": {
                    "code_pin": code_pin,
                    "hardware_pins": hardware_pins,
                },
            }

    return None


def check_unused_hardware_pin(connections: List[Connection], circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """
    [R012] 회로에는 연결되어 있는데 코드에서 사용하지 않는 핀 검사

    예:
    회로에는 D3가 연결되어 있는데 코드에서는 D3를 제어하지 않음.
    """
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
                "target": {
                    "hardware_pin": hardware_pin,
                    "used_pins_in_code": used_pins_in_code,
                },
            }

    return None


def check_missing_power_or_gnd(circuit_json: CircuitJson) -> Optional[ValidationResult]:
    """
    [R007/R008] 부품 전원 또는 GND 미연결 검사

    1차 버전:
    board/passive/led를 제외한 input/output 부품에 대해
    연결된 핀 중 VCC/5V/3.3V 계열 또는 GND가 전혀 없으면 경고.

    주의:
    모든 부품이 전원 핀을 필요로 하는 것은 아니므로 WARNING으로 처리.
    """
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

        # 보드, 저항, LED 같은 것은 이 규칙에서 제외
        if _is_board_component(text) or _is_passive_component(text) or _is_led_component(text):
            continue

        # input/output 부품 위주로 검사
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
                "target": {
                    "node_id": node_id,
                    "component": label or component_key,
                    "connected_pins": pins,
                },
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
                "target": {
                    "node_id": node_id,
                    "component": label or component_key,
                    "connected_pins": pins,
                },
            }

    return None


def check_duplicate_pin_usage(connections: List[Connection]) -> Optional[ValidationResult]:
    """
    [R010] 같은 보드 IO 핀에 여러 연결이 몰린 경우 검사

    1차 버전:
    같은 보드의 D/A 핀이 2개 이상 edge에 등장하면 INFO.
    무조건 오류는 아니지만 초보자에게 확인 필요.
    """
    pin_usage: Dict[str, List[str]] = {}

    for conn in connections:
        for side in ["from", "to"]:
            component = conn.get(f"{side}_component")
            component_key = conn.get(f"{side}_component_key")
            pin = conn.get(f"{side}_pin")
            edge_id = conn.get("edge_id")

            text = _component_text(component, component_key)

            if _is_board_component(text) and _is_io_pin(pin):
                normalized_pin = _normalize_pin(pin)
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
                "target": {
                    "pin": pin,
                    "edge_ids": edge_ids,
                },
            }

    return None


# =========================================================
# 전체 검증 실행 함수
# =========================================================

def validate_circuit(circuit_input: Union[str, Path, CircuitJson]) -> List[ValidationResult]:
    """
    회로 JSON을 검증하고 validation result 리스트를 반환한다.

    입력:
    - dict
    - JSON 문자열
    - JSON 파일 경로

    출력:
    [
      {
        "rule": "R004",
        "grade": "ERROR",
        "title": "...",
        "feedback": "...",
        "target": {...}
      }
    ]
    """
    try:
        circuit_json = load_circuit_json(circuit_input)
    except Exception as error:
        return [
            {
                "rule": "R001",
                "grade": "ERROR",
                "title": "JSON 형식 오류",
                "feedback": f"올바르지 않은 JSON 입력입니다. 입력 데이터를 다시 확인해주세요. 상세: {error}",
                "target": {},
            }
        ]

    results: List[ValidationResult] = []

    # 필수 필드 검사
    required_result = check_required_fields(circuit_json)
    if required_result:
        return [required_result]

    connections = convert_edges_to_connections(circuit_json)

    # 규칙 실행
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
        return [
            {
                "is_valid": True,
                "rule": "PASS",
                "grade": "PASS",
                "title": "기본 검증 통과",
                "feedback": "기본 회로 안전 검사를 통과했습니다.",
                "target": {},
            }
        ]

    return results


def validate_and_attach(circuit_input: Union[str, Path, CircuitJson]) -> CircuitJson:
    """
    회로 JSON을 검증한 뒤, 기존 JSON에 validationResults 필드를 붙여 반환한다.

    백엔드에서 최종적으로 이 함수를 쓰면 된다.

    예:
    circuit_json = make_circuit_json(prompt)
    result_json = validate_and_attach(circuit_json)
    return result_json
    """
    circuit_json = load_circuit_json(circuit_input)
    validation_results = validate_circuit(circuit_json)

    circuit_json["validationResults"] = validation_results

    # 기존 warnings 필드가 있으면 검증 결과의 feedback도 같이 넣어준다.
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


# =========================================================
# 단독 실행 테스트용 코드
# =========================================================

if __name__ == "__main__":
    # 1팀이 넘겨줄 JSON 예시
    sample_circuit = {
        "id": "demo-001",
        "title": "LED 테스트 회로",
        "userPrompt": "아두이노로 LED 켜는 회로 만들어줘",
        "summary": "일부러 오류를 넣은 테스트 회로입니다.",
        "nodes": [
            {
                "id": "arduino-1",
                "componentKey": "arduino_uno",
                "type": "board",
                "label": "Arduino Uno",
                "position": {"x": 100, "y": 200},
                "data": {},
            },
            {
                "id": "led-1",
                "componentKey": "red_led",
                "type": "output",
                "label": "Red LED",
                "position": {"x": 400, "y": 200},
                "data": {},
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "arduino-1",
                "target": "led-1",
                "sourceHandle": "D3",
                "targetHandle": "anode",
                "label": "D3 → LED anode",
                "data": {},
            }
        ],
        "code": "void setup() { pinMode(5, OUTPUT); } void loop() { digitalWrite(5, HIGH); }",
        "warnings": [],
        "explanation": [],
    }

    attached_result = validate_and_attach(sample_circuit)

    print(json.dumps(attached_result, ensure_ascii=False, indent=2))