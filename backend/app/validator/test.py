"""
    python test_examples.py
"""

import json

from app.validator.rules import validate_and_attach


# ---------------------------------------------------------
# 예제 1: 정상 회로 (센서 -> 아두이노, 전원/GND 다 있음)
# ---------------------------------------------------------
circuit_ok = {
    "nodes": [
        {"id": "arduino-1", "componentKey": "arduino_uno", "type": "board", "label": "Arduino Uno"},
        {"id": "sensor-1", "componentKey": "ultrasonic_sensor", "type": "input", "label": "Ultrasonic Sensor"},
    ],
    "edges": [
        {"id": "e1", "source": "arduino-1", "target": "sensor-1", "sourceHandle": "5V", "targetHandle": "VCC"},
        {"id": "e2", "source": "sensor-1", "target": "arduino-1", "sourceHandle": "GND", "targetHandle": "GND"},
        {"id": "e3", "source": "arduino-1", "target": "sensor-1", "sourceHandle": "D2", "targetHandle": "TRIG"},
        {"id": "e4", "source": "sensor-1", "target": "arduino-1", "sourceHandle": "ECHO", "targetHandle": "D3"},
    ],
    "code": "void setup(){ pinMode(2, OUTPUT); pinMode(3, INPUT); }",
    "warnings": [],
}

# ---------------------------------------------------------
# 예제 2: LED에 저항 없이 직결 (R006 나와야 함)
# ---------------------------------------------------------
circuit_missing_resistor = {
    "nodes": [
        {"id": "arduino-1", "componentKey": "arduino_uno", "type": "board", "label": "Arduino Uno"},
        {"id": "led-1", "componentKey": "led", "type": "output", "label": "Red LED"},
    ],
    "edges": [
        {"id": "e1", "source": "arduino-1", "target": "led-1", "sourceHandle": "D9", "targetHandle": "anode"},
        {"id": "e2", "source": "led-1", "target": "arduino-1", "sourceHandle": "cathode", "targetHandle": "GND"},
    ],
    "code": "void setup(){ pinMode(9, OUTPUT); }",
    "warnings": [],
}

# ---------------------------------------------------------
# 예제 3: 5V-GND 직결 합선 (R004 나와야 함)
# ---------------------------------------------------------
circuit_short = {
    "nodes": [
        {"id": "arduino-1", "componentKey": "arduino_uno", "type": "board", "label": "Arduino Uno"},
    ],
    "edges": [
        {"id": "e1", "source": "arduino-1", "target": "arduino-1", "sourceHandle": "5V", "targetHandle": "GND"},
    ],
    "warnings": [],
}


def run(name: str, circuit: dict) -> None:
    print(f"\n=== {name} ===")
    result = validate_and_attach(circuit)
    print(json.dumps(result["validationResults"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run("예제 1: 정상 회로", circuit_ok)
    run("예제 2: LED 저항 누락", circuit_missing_resistor)
    run("예제 3: 5V-GND 합선", circuit_short)