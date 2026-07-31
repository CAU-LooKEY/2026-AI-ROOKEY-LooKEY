from app.validator.adapter import convert_api_response_to_validator_json
from app.validator.rules import validate_and_attach


SAMPLE_API_RESPONSE = {
    "title": "LED 켜기",
    "intent": "LED 제어",
    "difficulty": "초급",
    "estimatedTime": "10분",
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
            {
                "id": "e3",
                "source": "resistor",
                "sourcePin": "LEAD_B",
                "target": "arduino",
                "targetPin": "GND",
                "label": "저항 → GND",
            },
        ],
    },
    "codeLines": [
        "void setup() {",
        "  pinMode(3, OUTPUT);",
        "}",
        "void loop() {",
        "  digitalWrite(3, HIGH);",
        "}",
    ],
    "warnings": [],
}


def test_convert_api_response_to_validator_json():
    result = convert_api_response_to_validator_json(SAMPLE_API_RESPONSE)

    assert result["title"] == "LED 켜기"
    assert "nodes" in result
    assert "edges" in result
    assert "code" in result

    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 3

    assert result["nodes"][0]["id"] == "arduino"
    assert result["edges"][0]["sourceHandle"] == "D3"
    assert result["edges"][0]["targetHandle"] == "ANODE"

    assert "pinMode(3, OUTPUT)" in result["code"]


def test_validate_converted_api_response_has_validation_results():
    validator_input = convert_api_response_to_validator_json(SAMPLE_API_RESPONSE)
    checked_result = validate_and_attach(validator_input)

    assert "validationResults" in checked_result
    assert isinstance(checked_result["validationResults"], list)
    assert len(checked_result["validationResults"]) > 0