import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import app
from app.services.intent_templates import classify_intent, generate_intent_template


PROMPT_CASES = {
    "proximity-led": [
        "손을 가까이 대면 LED가 켜지게 해줘",
        "손이 접근하면 불이 들어오는 회로",
        "근접했을 때 LED를 점등해 줘",
        "물체가 다가오면 빛이 켜졌으면 좋겠어",
        "초음파 센서로 가까이 온 손을 감지해 LED 켜기",
        "When an object is near, turn on the LED",
        "15cm 안에 물체가 있으면 LED를 켜줘",
    ],
    "button-led": [
        "버튼을 누르면 LED가 켜지게 해줘",
        "스위치를 눌렀을 때 불이 들어오게 해줘",
        "푸시버튼으로 LED를 제어하고 싶어",
        "button을 누르면 led 점등",
        "버튼 입력으로 빛을 켜는 회로",
        "스위치 누르면 LED 켜줘",
    ],
    "distance-alarm": [
        "물체가 가까우면 거리 경보를 보여줘",
        "10cm 이내 접근 시 알람을 켜줘",
        "초음파 거리 센서로 위험 경고를 만들어줘",
        "손이 근접하면 경보 LED를 깜빡여줘",
        "distance가 짧으면 alarm을 표시해줘",
        "가까이 다가오면 경고등을 켜줘",
        "거리 측정값이 작을 때 위험 알람을 줘",
    ],
}

EXPECTED_PARTS = {
    "proximity-led": {"arduino-uno-r3", "hc-sr04", "resistor-220-ohm", "led-5mm-blue"},
    "button-led": {"arduino-uno-r3", "pushbutton-6x6", "resistor-220-ohm", "led-5mm-blue"},
    "distance-alarm": {"arduino-uno-r3", "hc-sr04", "resistor-220-ohm", "led-5mm-blue"},
}


def _warning_codes(result):
    return {warning.code for warning in result.assembly_plan.warnings}


class IntentClassificationTest(unittest.TestCase):
    def test_failure_prompt_fixture_bypasses_deterministic_templates(self):
        fixture_path = Path(__file__).parent / "fixtures" / "intent_failure_prompts.json"
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 10)
        for case in cases:
            with self.subTest(category=case["category"], prompt=case["prompt"]):
                self.assertIsNone(classify_intent(case["prompt"]))
                self.assertIsNone(generate_intent_template(case["prompt"]))

    def test_twenty_representative_prompts_select_expected_parts(self):
        self.assertEqual(sum(map(len, PROMPT_CASES.values())), 20)
        for expected_intent, prompts in PROMPT_CASES.items():
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    match = classify_intent(prompt)
                    self.assertIsNotNone(match)
                    self.assertEqual(match.key, expected_intent)
                    result = generate_intent_template(prompt)
                    self.assertEqual(result.intent, expected_intent)
                    self.assertEqual(
                        {part.component_key for part in result.circuit.parts},
                        EXPECTED_PARTS[expected_intent],
                    )

    def test_proximity_request_never_substitutes_button_for_sensor(self):
        result = generate_intent_template("손을 가까이 대면 LED가 켜지게 해줘")
        keys = {part.component_key for part in result.circuit.parts}
        self.assertIn("hc-sr04", keys)
        self.assertNotIn("pushbutton-6x6", keys)


class TemplateEndToEndTest(unittest.TestCase):
    client = TestClient(app)

    def test_five_demo_prompts_run_from_api_to_3d_assembly_plan(self):
        demos = [
            PROMPT_CASES["proximity-led"][0],
            PROMPT_CASES["proximity-led"][4],
            PROMPT_CASES["button-led"][0],
            PROMPT_CASES["button-led"][2],
            PROMPT_CASES["distance-alarm"][0],
        ]
        for prompt in demos:
            with self.subTest(prompt=prompt):
                response = self.client.post("/api/v1/circuit/generate", json={"prompt": prompt})
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["assemblyPlan"]["schemaVersion"], "1.0")
                self.assertTrue(body["assemblyPlan"]["placements"])
                self.assertEqual(
                    len(body["assemblyPlan"]["components"]),
                    len(body["assemblyPlan"]["placements"]),
                )

    def test_every_template_led_has_a_220_ohm_series_resistor(self):
        for intent, prompts in PROMPT_CASES.items():
            with self.subTest(intent=intent):
                result = generate_intent_template(prompts[0])
                self.assertNotIn("LED_RESISTOR_MISSING", _warning_codes(result))
                self.assertIn("ASSEMBLY_VALID", _warning_codes(result))
                passed = {item.rule_id for item in result.validation_results if item.level == "PASS"}
                self.assertIn("LED_220_OHM", passed)

    def test_unconfigured_ai_error_is_user_facing_korean(self):
        with patch("app.main.get_settings", return_value=Settings(k_exaone_api_key="", k_exaone_endpoint_id="")):
            response = self.client.post(
                "/api/v1/circuit/generate", json={"prompt": "지원되지 않은 임의 회로"}
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("AI 회로 생성 서비스가 설정되지 않았습니다", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
