import json

from app.validator.adapter import convert_api_response_to_validator_json
from app.validator.rules import validate_and_attach


SAMPLE_CIRCUIT = {
    "title": "LED 켜기",
    "intent": "LED 제어",
    "difficulty": "초급",
    "estimatedTime": "10분",
    "components": [
        {
            "id": "arduino_uno",
            "name": "Arduino Uno",
            "quantity": 1,
            "role": "LED를 제어합니다.",
        },
        {
            "id": "led",
            "name": "LED",
            "quantity": 1,
            "role": "빛을 냅니다.",
        },
        {
            "id": "resistor",
            "name": "220Ω 저항",
            "quantity": 1,
            "role": "LED 전류를 제한합니다.",
        },
    ],
    "circuit": {
        "parts": [
            {
                "id": "arduino",
                "label": "Arduino Uno",
                "componentKey": "arduino-uno-r3",
                "position": {"x": 80, "y": 120},
                "width": 260,
            },
            {
                "id": "led",
                "label": "LED",
                "componentKey": "led-5mm-blue",
                "position": {"x": 460, "y": 120},
                "width": 120,
            },
            {
                "id": "resistor",
                "label": "220Ω 저항",
                "componentKey": "resistor-220-ohm",
                "position": {"x": 650, "y": 120},
                "width": 160,
            },
        ],
        "connections": [
            {
                "id": "e1",
                "source": "arduino",
                "sourcePin": "D3",
                "target": "led",
                "targetPin": "ANODE",
                "label": "D3 → ANODE",
            },
            {
                "id": "e2",
                "source": "led",
                "sourcePin": "CATHODE",
                "target": "resistor",
                "targetPin": "LEAD_A",
                "label": "CATHODE → 저항",
            },
        ],
    },
    "codeLines": ["void setup() {}", "void loop() {}"],
    "warnings": ["LED에 저항을 연결하세요."],
}


if __name__ == "__main__":
    validator_input = convert_api_response_to_validator_json(SAMPLE_CIRCUIT)
    checked_result = validate_and_attach(validator_input)

    print(json.dumps(checked_result, ensure_ascii=False, indent=2))
    