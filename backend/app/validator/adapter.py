"""
LOOKEY 3팀 회로 검증 모듈 — adapter.py (JSON 수신/변환 담당)
"""

import re
from typing import Any, Dict, List


CircuitJson = Dict[str, Any]
Connection = Dict[str, Any]


def _to_lower(value: Any) -> str:
    """None 방어 + 문자열 소문자 변환"""
    return str(value or "").strip().lower()


_PIN_ALIASES = {
    "GROUND": "GND",
    "GND_D": "GND", "GND_P1": "GND", "GND_P2": "GND",
    "AUX_GND_1": "GND", "AUX_GND_2": "GND", "GND_1": "GND", "GND_2": "GND",
    "+5V": "5V", "AUX_5V": "5V",
    "3V3": "3.3V", "AUX_3V3": "3.3V",
    "VDD": "VCC",
}


def normalize_pin(pin: Any) -> str:
    raw = str(pin or "").strip().upper()
    return _PIN_ALIASES.get(raw, raw)


def is_io_pin(pin: Any) -> bool:
    return bool(re.fullmatch(r"[DA]\d+", normalize_pin(pin)))


def load_circuit_json(source: Any) -> CircuitJson:
    if isinstance(source, dict):
        return source
    if isinstance(source, str):
        import json
        return json.loads(source)
    raise ValueError("회로 JSON은 dict 또는 JSON 문자열이어야 합니다.")


def _connections_from_nodes_edges(circuit_json: CircuitJson) -> List[Connection]:
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
    components: List[str] = circuit_json.get("components", [])
    instance_ids = [f"{comp_type}_{idx}" for idx, comp_type in enumerate(components)]

    connections: List[Connection] = []
    for cc in circuit_json.get("circuit_connections", []):
        f, t = cc.get("from", {}), cc.get("to", {})
        f_idx, t_idx = f.get("component_index"), t.get("component_index")

        if f_idx is None or t_idx is None or f_idx >= len(components) or t_idx >= len(components):
            continue

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
    if isinstance(circuit_json.get("connections"), list):
        return circuit_json["connections"]

    if isinstance(circuit_json.get("circuit_connections"), list):
        return _connections_from_task_result(circuit_json)

    return _connections_from_nodes_edges(circuit_json)


def get_connected_pins_by_node(connections: List[Connection]) -> Dict[str, List[str]]:
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
    """
    코드에서 실제로 사용된 핀을 뽑는다. 우선순위:
    1. codeMeta.used_pins (K-EXAONE이 이미 계산해서 줌 — 제일 정확)
    2. code/source_code 문자열을 정규식으로 파싱
    """
    code_meta = circuit_json.get("codeMeta")
    if isinstance(code_meta, dict) and isinstance(code_meta.get("used_pins"), list):
        return sorted({normalize_pin(p) for p in code_meta["used_pins"]})

    code = circuit_json.get("code") or circuit_json.get("source_code") or ""
    if not isinstance(code, str):
        return []

    pins = set()
    for match in _PIN_CALL_PATTERN.findall(code):
        pin = match.strip().upper()
        pins.add(f"D{pin}" if pin.isdigit() else pin)
    return sorted(pins)


def get_hardware_io_pins(connections: List[Connection]) -> List[str]:
    pins = set()
    for conn in connections:
        for pin in (conn.get("from_pin"), conn.get("to_pin")):
            if is_io_pin(pin):
                pins.add(normalize_pin(pin))
    return sorted(pins)


def infer_component_type(component_key: str, label: str = "") -> str:
    text = f"{component_key} {label}".lower()

    if "arduino" in text or "uno" in text or "nano" in text:
        return "board"
    if "hc-sr04" in text or "ultrasonic" in text or "sensor" in text:
        return "input"
    if "button" in text or "pushbutton" in text or "switch" in text:
        return "input"
    if "led" in text or "buzzer" in text or "servo" in text:
        return "output"
    if "resistor" in text or "220" in text or "ohm" in text or "저항" in text:
        return "passive"
    return "unknown"


def convert_api_response_to_validator_json(api_response: CircuitJson) -> CircuitJson:
    circuit = api_response.get("circuit", {})
    parts = circuit.get("parts", [])
    connections = circuit.get("connections", [])

    nodes = []
    for part in parts:
        component_key = part.get("componentKey", "")
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
            "sourceHandle": connection.get("sourcePin"),
            "targetHandle": connection.get("targetPin"),
            "label": connection.get("label", ""),
        })

    code_lines = api_response.get("codeLines", [])
    if isinstance(code_lines, list):
        code = "\n".join(str(line) for line in code_lines)
    elif isinstance(api_response.get("code"), str):
        code = api_response.get("code", "")
    else:
        code = ""

    return {
        "title": api_response.get("title"),
        "intent": api_response.get("intent"),
        "difficulty": api_response.get("difficulty"),
        "estimatedTime": api_response.get("estimatedTime"),
        "nodes": nodes,
        "edges": edges,
        "code": code,
        "codeMeta": api_response.get("codeMeta"),  # used_pins(K-EXAONE이 계산한 정확한 값) 보존
        "warnings": api_response.get("warnings", []),
        "explanation": api_response.get("tutorSteps", []),
        "validationResultsFromApi": api_response.get("validationResults", []),
        "originalApiResponse": api_response,
    }