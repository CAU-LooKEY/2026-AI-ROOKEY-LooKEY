import json
import unittest

import httpx

from app.core.settings import Settings
from app.services.k_exaone import KExaoneClient


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
                "color": "#7c3aed",
            },
            {
                "id": "e2",
                "source": "led",
                "sourcePin": "CATHODE",
                "target": "resistor",
                "targetPin": "LEAD_A",
                "label": "CATHODE → 저항",
                "color": "#f97316",
            },
        ],
    },
    "codeLines": ["void setup() {}", "void loop() {}"],
    "codeMeta": {"used_pins": ["D3", "GND"]},
    "tutorSteps": [
        {"title": "1. 연결", "desc": "LED와 저항을 연결합니다."}
    ],
    "warnings": ["LED에 저항을 연결하세요."],
    "validationResults": [
        {
            "ruleId": "R006",
            "level": "PASS",
            "message": "전류 제한 저항이 포함되어 있습니다.",
        }
    ],
    "unsupportedComponents": [],
}


class KExaoneClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_generates_and_validates_circuit_response(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            request_body = json.loads(request.content)
            self.assertEqual(request_body["model"], "test-endpoint")
            self.assertFalse(request_body["stream"])
            self.assertFalse(
                request_body["chat_template_kwargs"]["enable_thinking"]
            )
            self.assertEqual(request_body["response_format"]["type"], "json_schema")
            serialized_schema = json.dumps(request_body["response_format"])
            self.assertNotIn("$ref", serialized_schema)
            self.assertNotIn("$defs", serialized_schema)
            response_properties = request_body["response_format"]["json_schema"][
                "schema"
            ]["properties"]
            self.assertIn("codeLines", response_properties)
            self.assertNotIn("code", response_properties)
            connection_properties = response_properties["circuit"]["properties"][
                "connections"
            ]["items"]["properties"]
            self.assertNotIn("sourceConnector", connection_properties)
            self.assertNotIn("targetConnector", connection_properties)
            self.assertNotIn("wireType", connection_properties)

            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    SAMPLE_CIRCUIT,
                                    ensure_ascii=False,
                                ),
                            },
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        settings = Settings(
            k_exaone_api_key="test-token",
            k_exaone_endpoint_id="test-endpoint",
            k_exaone_api_url="https://example.test/chat/completions",
            k_exaone_timeout_seconds=5,
        )
        client = KExaoneClient(
            settings,
            transport=httpx.MockTransport(handler),
        )

        result = await client.generate_circuit("LED를 켜줘")

        self.assertEqual(result.title, "LED 켜기")
        self.assertEqual(result.code, "void setup() {}\nvoid loop() {}")
        self.assertEqual(result.circuit.parts[1].component_key, "led-5mm-blue")
        self.assertEqual(
            result.circuit.connections[0].source_connector,
            "male",
        )
        self.assertEqual(
            result.circuit.connections[0].target_connector,
            "female",
        )
        self.assertEqual(
            result.circuit.connections[0].wire_type,
            "male-female",
        )
        self.assertEqual(result.circuit.connections[0].color, "#2563eb")
        self.assertEqual(result.validation_results[0].level, "PASS")

    async def test_repairs_an_invalid_model_response_once(self):
        request_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            request_body = json.loads(request.content)

            response_circuit = json.loads(json.dumps(SAMPLE_CIRCUIT))
            if request_count == 1:
                response_circuit["circuit"]["connections"][0][
                    "sourcePin"
                ] = "NOT_A_PIN"
            else:
                self.assertEqual(len(request_body["messages"]), 4)
                self.assertIn(
                    "Validation error",
                    request_body["messages"][-1]["content"],
                )

            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(response_circuit),
                            },
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        settings = Settings(
            k_exaone_api_key="test-token",
            k_exaone_endpoint_id="test-endpoint",
            k_exaone_api_url="https://example.test/chat/completions",
            k_exaone_timeout_seconds=5,
        )
        client = KExaoneClient(
            settings,
            transport=httpx.MockTransport(handler),
        )

        result = await client.generate_circuit("LED를 켜줘")

        self.assertEqual(result.title, "LED 켜기")
        self.assertEqual(request_count, 2)

    def test_parses_markdown_wrapped_json_as_fallback(self):
        content = "```json\n{\"title\": \"LED 켜기\"}\n```"
        self.assertEqual(
            KExaoneClient._parse_json_content(content),
            {"title": "LED 켜기"},
        )


if __name__ == "__main__":
    unittest.main()
