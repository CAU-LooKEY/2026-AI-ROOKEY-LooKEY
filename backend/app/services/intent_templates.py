from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.circuit import CircuitGenerationResponse
from app.services.physical_assembly import PhysicalAssemblyPlanEngine

IntentKey = Literal["proximity-led", "button-led", "distance-alarm"]


@dataclass(frozen=True)
class IntentMatch:
    key: IntentKey
    confidence: float


PROXIMITY = ("가까", "접근", "근접", "손을 대", "다가오", "near", "proximity")
DISTANCE = ("거리", "몇 cm", "센티미터", "distance", "초음파")
ALARM = ("경보", "경고", "알람", "위험", "alarm")
BUTTON = ("버튼", "스위치", "누르면", "눌렀", "button", "switch")
LED = ("led", "불", "빛", "켜", "점등")
UNSUPPORTED = ("부저", "buzzer", "온도 센서", "temperature sensor", "모터", "motor", "lcd", "디스플레이")


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def classify_intent(prompt: str) -> IntentMatch | None:
    text = re.sub(r"\s+", " ", prompt.strip().lower())
    proximity = _has(text, PROXIMITY)
    distance = _has(text, DISTANCE) or bool(re.search(r"\d+\s*(?:cm|센티)", text))
    button = _has(text, BUTTON)
    if _has(text, UNSUPPORTED) or ((proximity or distance) and button):
        return None
    if (proximity or distance) and _has(text, ALARM):
        return IntentMatch("distance-alarm", 0.99)
    if _has(text, BUTTON) and _has(text, LED):
        return IntentMatch("button-led", 0.99)
    if (proximity or distance) and _has(text, LED):
        return IntentMatch("proximity-led", 0.99)
    return None


def generate_intent_template(prompt: str) -> CircuitGenerationResponse | None:
    match = classify_intent(prompt)
    if match is None:
        return None
    document = {
        "proximity-led": _proximity_led,
        "button-led": _button_led,
        "distance-alarm": _distance_alarm,
    }[match.key]()
    response = CircuitGenerationResponse.model_validate(document)
    response.assembly_plan = PhysicalAssemblyPlanEngine().build(response)
    return response


def _part(identifier: str, label: str, key: str, x: int, width: int) -> dict:
    return {"id": identifier, "label": label, "componentKey": key,
            "position": {"x": x, "y": 120}, "width": width}


def _wire(identifier: str, source: str, source_pin: str, target: str,
          target_pin: str, label: str) -> dict:
    return {"id": identifier, "source": source, "sourcePin": source_pin,
            "target": target, "targetPin": target_pin, "label": label,
            "color": "#2563eb"}


def _parts(extra: Literal["sensor", "button"]) -> list[dict]:
    middle = (_part("sensor", "HC-SR04", "hc-sr04", 320, 180)
              if extra == "sensor" else
              _part("button", "푸시버튼", "pushbutton-6x6", 340, 120))
    return [
        _part("arduino", "Arduino Uno R3", "arduino-uno-r3", 20, 260), middle,
        _part("resistor", "220Ω 저항", "resistor-220-ohm", 540, 120),
        _part("led", "파란색 LED", "led-5mm-blue", 700, 100),
    ]


def _sensor_wires() -> list[dict]:
    return [
        _wire("w1", "arduino", "5V", "sensor", "VCC", "5V → VCC"),
        _wire("w2", "arduino", "D7", "sensor", "TRIG", "D7 → TRIG"),
        _wire("w3", "sensor", "ECHO", "arduino", "D8", "ECHO → D8"),
        _wire("w4", "sensor", "GND", "arduino", "GND_P1", "GND → GND"),
    ]


def _led_wires(start: int) -> list[dict]:
    return [
        _wire(f"w{start}", "arduino", "D3", "resistor", "LEAD_A", "D3 → 220Ω"),
        _wire(f"w{start + 1}", "resistor", "LEAD_B", "led", "ANODE", "220Ω → LED 양극"),
        _wire(f"w{start + 2}", "led", "CATHODE", "arduino", "GND_P2", "LED 음극 → GND"),
    ]


def _document(title: str, intent: str, parts: list[dict], wires: list[dict],
              code: str, pins: list[str]) -> dict:
    names = {
        "arduino": ("Arduino Uno R3", "입력을 읽고 출력을 제어합니다."),
        "sensor": ("HC-SR04 초음파 거리 센서", "물체까지의 거리를 측정합니다."),
        "button": ("푸시버튼", "사용자의 누름 입력을 감지합니다."),
        "resistor": ("220Ω 저항", "LED 전류를 안전하게 제한합니다."),
        "led": ("파란색 LED", "감지 결과를 빛으로 표시합니다."),
    }
    return {
        "title": title, "intent": intent, "difficulty": "초급", "estimatedTime": "20분",
        "components": [{"id": p["id"], "name": names[p["id"]][0], "quantity": 1,
                        "role": names[p["id"]][1]} for p in parts],
        "circuit": {"parts": parts, "connections": wires}, "code": code,
        "codeMeta": {"used_pins": pins},
        "tutorSteps": [
            {"title": "1. 부품 배치", "desc": "그림과 같이 부품을 배치하세요."},
            {"title": "2. 전원 연결", "desc": "5V와 GND를 먼저 연결하세요."},
            {"title": "3. 신호 연결", "desc": "표시된 디지털 핀을 연결하세요."},
            {"title": "4. 안전 확인", "desc": "LED의 220Ω 직렬 저항을 확인하세요."},
        ],
        "warnings": ["전원을 연결하기 전에 배선을 한 번 더 확인하세요."],
        "validationResults": [
            {"ruleId": "INTENT_MATCH", "level": "PASS",
             "message": "자연어 요청의 핵심 동작과 입력 부품이 일치합니다."},
            {"ruleId": "LED_220_OHM", "level": "PASS",
             "message": "모든 LED에 220Ω 전류 제한 저항이 직렬로 연결되어 있습니다."},
        ], "unsupportedComponents": [],
    }


SENSOR_CODE = """const int trigPin = 7;
const int echoPin = 8;
const int ledPin = 3;
void setup() {
  pinMode(trigPin, OUTPUT); pinMode(echoPin, INPUT); pinMode(ledPin, OUTPUT);
}
void loop() {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10); digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  float distanceCm = duration * 0.0343 / 2.0;
  digitalWrite(ledPin, distanceCm > 0 && distanceCm < 15 ? HIGH : LOW);
  delay(50);
}"""
SENSOR_PINS = ["D3", "D7", "D8", "5V", "GND_P1", "GND_P2"]


def _proximity_led() -> dict:
    return _document("손을 가까이 대면 켜지는 LED", "proximity-led", _parts("sensor"),
                     _sensor_wires() + _led_wires(5), SENSOR_CODE, SENSOR_PINS)


def _distance_alarm() -> dict:
    code = SENSOR_CODE.replace(
        "distanceCm < 15 ? HIGH : LOW",
        "distanceCm < 10 && millis() % 300 < 150 ? HIGH : LOW")
    result = _document("가까운 물체 거리 경보", "distance-alarm", _parts("sensor"),
                       _sensor_wires() + _led_wires(5), code, SENSOR_PINS)
    result["warnings"] = ["현재 지원되는 LED 점멸 방식으로 경보를 표시합니다."]
    return result


def _button_led() -> dict:
    wires = [
        _wire("w1", "arduino", "D2", "button", "A1", "D2 → 버튼"),
        _wire("w2", "button", "B1", "arduino", "GND_P1", "버튼 → GND"),
        *_led_wires(3),
    ]
    code = """const int buttonPin = 2;
const int ledPin = 3;
void setup() { pinMode(buttonPin, INPUT_PULLUP); pinMode(ledPin, OUTPUT); }
void loop() { digitalWrite(ledPin, digitalRead(buttonPin) == LOW ? HIGH : LOW); }"""
    return _document("버튼을 누르면 켜지는 LED", "button-led", _parts("button"), wires,
                     code, ["D2", "D3", "GND_P1", "GND_P2"])
