"""
LOOKEY 3팀 회로 검증 모듈 — adapter.py (JSON 수신/변환 담당)

⚠️ AI팀 실제 스키마(componentKey, type, sourceHandle, targetHandle, code)가
이미 확정되어 있어서, "어떤 형식으로 올지 몰라 대비하는" 방어 코드를 다
뺐습니다. 원래 버전은 JSON 문자열/파일 경로 입력, codeMeta 대체 구조,
label 없을 때의 여러 겹 대체 로직까지 지원했는데, 실제로는 백엔드가 이미
파싱된 dict를 그대로 받고 필드 이름도 고정돼 있어서 전부 불필요했습니다.

rules.py가 가져다 쓰는 함수 이름/역할은 그대로 유지했으니 rules.py는 안
고쳐도 됩니다.
"""

import re
from typing import Any, Dict, List


CircuitJson = Dict[str, Any]
Connection = Dict[str, Any]


def _to_lower(value: Any) -> str:
    """None 방어 + 문자열 소문자 변환"""
    return str(value or "").strip().lower()


def normalize_pin(pin: Any) -> str:
    """핀 이름 정규화. gnd -> GND, +5v -> 5V, d3 -> D3"""
    raw = str(pin or "").strip().upper()
    aliases = {"GROUND": "GND", "+5V": "5V", "3V3": "3.3V", "VDD": "VCC"}
    return aliases.get(raw, raw)


def is_io_pin(pin: Any) -> bool:
    """D3, A0처럼 아두이노 디지털/아날로그 핀 이름인지 판별."""
    return bool(re.fullmatch(r"[DA]\d+", normalize_pin(pin)))


def load_circuit_json(source: Any) -> CircuitJson:
    """
    회로 JSON을 받는다. 백엔드가 이미 파싱해서 dict로 넘겨주는 게 기본이고,
    혹시 JSON 문자열로 오면 그것도 파싱해준다 (파일 경로 입력은 지원 안 함 —
    백엔드 함수 호출에서는 필요 없음).
    """
    if isinstance(source, dict):
        return source
    if isinstance(source, str):
        import json
        return json.loads(source)
    raise ValueError("회로 JSON은 dict 또는 JSON 문자열이어야 합니다.")


def convert_edges_to_connections(circuit_json: CircuitJson) -> List[Connection]:
    """
    nodes + edges(componentKey/sourceHandle/targetHandle 확정 스키마)를
    검증 규칙에서 쓰기 쉬운 connections 구조로 변환한다.
    """
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


def get_connected_pins_by_node(circuit_json: CircuitJson) -> Dict[str, List[str]]:
    """node id별로 연결된 핀 목록을 만든다."""
    connected: Dict[str, List[str]] = {}
    for edge in circuit_json.get("edges", []):
        source, target = edge.get("source"), edge.get("target")
        if source:
            connected.setdefault(str(source), []).append(normalize_pin(edge.get("sourceHandle")))
        if target:
            connected.setdefault(str(target), []).append(normalize_pin(edge.get("targetHandle")))
    return connected


_PIN_CALL_PATTERN = re.compile(
    r"(?:pinMode|digitalWrite|digitalRead|analogRead|analogWrite)\s*\(\s*([A-Za-z]?\d+)"
)


def extract_used_pins_from_code(circuit_json: CircuitJson) -> List[str]:
    """code 문자열에서 pinMode/digitalWrite 등에 실제 쓰인 핀을 뽑는다."""
    code = circuit_json.get("code", "")
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