"""
LOOKEY 3팀 회로 검증 모듈 — adapter.py (JSON 수신/변환 담당)

지원하는 입력 형식 4가지 (convert_edges_to_connections가 자동으로 판별):

1. 이미 변환된 connections 배열 (그대로 통과)
2. nodes + edges (componentKey/sourceHandle/targetHandle) — 이전 AI팀 목업 API 형식
3. components + circuit_connections (component_index 기반) — Task-Result DB 형식
   {
     "components": ["arduino_uno", "hc_sr04", "led", "resistor_220ohm"],
     "circuit_connections": [
       {"from": {"component_index": 0, "pin": "5V"}, "to": {"component_index": 1, "pin": "VCC"}},
       ...
     ]
   }
   ⚠️ component_index는 components 배열에서 몇 번째 부품인지를 가리킵니다.
   같은 부품이 여러 개 있어도(LED 2개 등) 인덱스로 구분할 수 있게 3팀이
   제안한 형식입니다 — 아직 팀 확정 전이라 4팀/1팀과 맞춰봐야 합니다.
4. circuit.parts + circuit.connections — 현재 LooKEY 생성 API 응답 형식

네 형식 모두 아래 공통 connections 구조로 변환되고, rules.py의 나머지
규칙들은 이 공통 구조만 보므로 그대로 재사용됩니다.
"""

import re
from typing import Any, Dict, List


CircuitJson = Dict[str, Any]
Connection = Dict[str, Any]


def _to_lower(value: Any) -> str:
    """None 방어 + 문자열 소문자 변환"""
    return str(value or "").strip().lower()


# assets_db 기준 실제 보드 핀 이름 중, 물리적으로 같은 GND/전원 레일인데
# 이름이 다른 것들. (예: 우노는 GND가 5곳에 있음 — GND_D, GND_P1, GND_P2,
# AUX_GND_1, AUX_GND_2가 전부 하나의 GND 레일)
_PIN_ALIASES = {
    "GROUND": "GND",
    "GND_D": "GND", "GND_P1": "GND", "GND_P2": "GND",
    "AUX_GND_1": "GND", "AUX_GND_2": "GND", "GND_1": "GND", "GND_2": "GND",
    "+5V": "5V", "AUX_5V": "5V",
    "3V3": "3.3V", "AUX_3V3": "3.3V",
    "VDD": "VCC",
}


def normalize_pin(pin: Any) -> str:
    """핀 이름 정규화. gnd -> GND, GND_P1 -> GND, +5v -> 5V, d3 -> D3"""
    raw = str(pin or "").strip().upper()
    return _PIN_ALIASES.get(raw, raw)


def is_io_pin(pin: Any) -> bool:
    """D3, A0처럼 아두이노 디지털/아날로그 핀 이름인지 판별."""
    return bool(re.fullmatch(r"[DA]\d+", normalize_pin(pin)))


def load_circuit_json(source: Any) -> CircuitJson:
    """
    회로 JSON을 받는다. 백엔드가 이미 파싱해서 dict로 넘겨주는 게 기본이고,
    혹시 JSON 문자열로 오면 그것도 파싱해준다.
    """
    if isinstance(source, dict):
        return source
    if isinstance(source, str):
        import json
        return json.loads(source)
    raise ValueError("회로 JSON은 dict 또는 JSON 문자열이어야 합니다.")


def _connections_from_nodes_edges(circuit_json: CircuitJson) -> List[Connection]:
    """형식 2: nodes + edges (componentKey/sourceHandle/targetHandle)"""
    node_map = {str(n["id"]): n for n in circuit_json.get("nodes", []) if n.get("id")}
    connections: List[Connection] = []

    for edge in circuit_json.get("edges", []):
        source_node = node_map.get(str(edge.get("source")), {})
        target_node = node_map.get(str(edge.get("target")), {})

        connections.append({
            "edge_id": edge.get("id"),
            "from_component": source_node.get("label") or source_node.get("componentKey", "UNKNOWN"),
            "from_component_key": source_node.get("componentKey"),
            "from_component_type": source_node.get("type"),
            "from_pin": edge.get("sourceHandle"),
            "to_component": target_node.get("label") or target_node.get("componentKey", "UNKNOWN"),
            "to_component_key": target_node.get("componentKey"),
            "to_component_type": target_node.get("type"),
            "to_pin": edge.get("targetHandle"),
        })

    return connections


def _connections_from_task_result(circuit_json: CircuitJson) -> List[Connection]:
    """형식 3: components(문자열 리스트) + circuit_connections(component_index 기반)"""
    components: List[str] = circuit_json.get("components", [])
    # 같은 부품이 여러 개일 수 있으므로 "타입_인덱스" 형태로 고유 id를 만든다
    instance_ids = [f"{comp_type}_{idx}" for idx, comp_type in enumerate(components)]

    connections: List[Connection] = []
    for cc in circuit_json.get("circuit_connections", []):
        f, t = cc.get("from", {}), cc.get("to", {})
        f_idx, t_idx = f.get("component_index"), t.get("component_index")

        if f_idx is None or t_idx is None or f_idx >= len(components) or t_idx >= len(components):
            continue  # 잘못된 인덱스는 건너뜀 (필요하면 나중에 에러로 승격 가능)

        connections.append({
            "edge_id": cc.get("id"),
            "from_component": instance_ids[f_idx],
            "from_component_key": components[f_idx],
            "from_component_type": None,
            "from_pin": f.get("pin"),
            "to_component": instance_ids[t_idx],
            "to_component_key": components[t_idx],
            "to_component_type": None,
            "to_pin": t.get("pin"),
        })

    return connections


def convert_edges_to_connections(circuit_json: CircuitJson) -> List[Connection]:
    """
    회로 JSON을 공통 connections 구조로 변환한다. 네 가지 입력 형식을
    자동으로 판별해서 처리한다 (모듈 docstring 참고).
    """
    if isinstance(circuit_json.get("connections"), list):
        return circuit_json["connections"]

    if isinstance(circuit_json.get("circuit_connections"), list):
        return _connections_from_task_result(circuit_json)

    circuit = circuit_json.get("circuit")
    if isinstance(circuit, dict):
        converted = convert_api_response_to_validator_json(circuit_json)
        return _connections_from_nodes_edges(converted)

    return _connections_from_nodes_edges(circuit_json)


def infer_component_type(component_key: str, label: str = "") -> str:
    """Infer the legacy validator category from a canonical component key."""
    text = f"{component_key} {label}".lower()
    if any(token in text for token in ("arduino", "uno", "nano", "board")):
        return "board"
    if any(token in text for token in ("sensor", "hc-sr04", "button", "switch")):
        return "input"
    if any(token in text for token in ("led", "buzzer", "servo", "motor")):
        return "output"
    if any(token in text for token in ("resistor", "capacitor", "potentiometer")):
        return "passive"
    return "unknown"


def convert_api_response_to_validator_json(api_response: CircuitJson) -> CircuitJson:
    """Convert the current circuit API response into nodes/edges validator input."""
    circuit = api_response.get("circuit")
    if not isinstance(circuit, dict):
        raise ValueError("API response must contain a circuit object.")

    parts = circuit.get("parts")
    connections = circuit.get("connections")
    if not isinstance(parts, list) or not isinstance(connections, list):
        raise ValueError("circuit.parts and circuit.connections must be arrays.")

    nodes = []
    for part in parts:
        component_key = part.get("componentKey") or part.get("component_key") or ""
        label = part.get("label") or part.get("name") or component_key
        nodes.append({
            "id": part.get("id"),
            "componentKey": component_key,
            "type": infer_component_type(component_key, label),
            "label": label,
            "position": part.get("position", {}),
            "width": part.get("width"),
        })

    edges = []
    for connection in connections:
        edges.append({
            "id": connection.get("id"),
            "source": connection.get("source"),
            "target": connection.get("target"),
            "sourceHandle": connection.get("sourcePin") or connection.get("source_pin"),
            "targetHandle": connection.get("targetPin") or connection.get("target_pin"),
            "label": connection.get("label", ""),
        })

    code = api_response.get("code")
    if not isinstance(code, str):
        code_lines = api_response.get("codeLines") or api_response.get("code_lines")
        code = "\n".join(str(line) for line in code_lines) if isinstance(code_lines, list) else ""

    return {
        "title": api_response.get("title"),
        "intent": api_response.get("intent"),
        "difficulty": api_response.get("difficulty"),
        "estimatedTime": api_response.get("estimatedTime") or api_response.get("estimated_time"),
        "nodes": nodes,
        "edges": edges,
        "code": code,
        "codeMeta": api_response.get("codeMeta") or api_response.get("code_meta"),
        "warnings": api_response.get("warnings", []),
        "explanation": api_response.get("tutorSteps") or api_response.get("tutor_steps", []),
    }


def get_connected_pins_by_node(connections: List[Connection]) -> Dict[str, List[str]]:
    """
    부품 instance id별로 연결된 핀 목록을 만든다.
    ⚠️ 예전엔 raw circuit_json(nodes/edges)을 직접 읽었는데, 그러면 형식 3
    (components+circuit_connections)에서는 항상 빈 값만 나오는 문제가 있어서
    convert_edges_to_connections()가 만든 공통 connections 리스트를 받는
    방식으로 바꿨다. (rules.py의 check_missing_power_or_gnd 호출부도 같이 수정 필요)
    """
    connected: Dict[str, List[str]] = {}
    for conn in connections:
        from_id, to_id = conn.get("from_component"), conn.get("to_component")
        if from_id:
            connected.setdefault(from_id, []).append(normalize_pin(conn.get("from_pin")))
        if to_id:
            connected.setdefault(to_id, []).append(normalize_pin(conn.get("to_pin")))
    return connected


_PIN_CALL_PATTERN = re.compile(
    r"(?:pinMode|digitalWrite|digitalRead|analogRead|analogWrite)\s*\(\s*([A-Za-z]?\d+)"
)


def extract_used_pins_from_code(circuit_json: CircuitJson) -> List[str]:
    """code(또는 source_code) 문자열에서 pinMode/digitalWrite 등에 쓰인 핀을 뽑는다."""
    code_meta = circuit_json.get("codeMeta") or circuit_json.get("code_meta")
    if isinstance(code_meta, dict):
        used_pins = code_meta.get("used_pins") or code_meta.get("usedPins")
        if isinstance(used_pins, list):
            return sorted({normalize_pin(pin) for pin in used_pins})

    code = circuit_json.get("code") or circuit_json.get("source_code") or ""
    if not isinstance(code, str):
        return []

    pins = set()
    for match in _PIN_CALL_PATTERN.findall(code):
        pin = match.strip().upper()
        pins.add(f"D{pin}" if pin.isdigit() else pin)
    return sorted(pins)


def get_hardware_io_pins(connections: List[Connection]) -> List[str]:
    """실제 회로 연결에서 D/A 핀 목록 추출."""
    pins = set()
    for conn in connections:
        for pin in (conn.get("from_pin"), conn.get("to_pin")):
            if is_io_pin(pin):
                pins.add(normalize_pin(pin))
    return sorted(pins)
