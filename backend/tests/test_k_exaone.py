import json
import unittest

import httpx

from app.core.settings import Settings
from app.services.k_exaone import (
    KExaoneClient,
    KExaoneError,
    MAX_GENERATION_ATTEMPTS,
    MAX_RESPONSE_TOKENS,
)


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
            self.assertEqual(request_body["temperature"], 0)
            self.assertEqual(
                request_body["max_tokens"],
                MAX_RESPONSE_TOKENS,
            )
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
            self.assertNotIn("assemblyPlan", response_properties)
            self.assertEqual(response_properties["codeLines"]["maxItems"], 40)
            self.assertEqual(response_properties["tutorSteps"]["maxItems"], 5)
            self.assertEqual(response_properties["warnings"]["maxItems"], 4)
            self.assertEqual(
                response_properties["validationResults"]["maxItems"],
                6,
            )
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
        self.assertIsNotNone(result.assembly_plan)
        self.assertEqual(result.assembly_plan.schema_version, "1.0")
        self.assertEqual(result.assembly_plan.components[0].asset_slug, "arduino-uno-r3")

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

    async def test_retries_truncated_response_without_replaying_it(self):
        request_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            request_body = json.loads(request.content)

            if request_count == 1:
                content = '{"title": "truncated'
                finish_reason = "length"
            else:
                self.assertEqual(len(request_body["messages"]), 3)
                self.assertEqual(request_body["messages"][-1]["role"], "user")
                self.assertIn(
                    "token limit was reached",
                    request_body["messages"][-1]["content"],
                )
                self.assertIn(
                    "substantially shorter",
                    request_body["messages"][-1]["content"],
                )
                content = json.dumps(SAMPLE_CIRCUIT)
                finish_reason = "stop"

            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": content,
                            },
                            "finish_reason": finish_reason,
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

        result = await client.generate_circuit("LED circuit")

        self.assertEqual(result.circuit.parts[0].id, "arduino-uno-r3-1")
        self.assertEqual(request_count, 2)

    async def test_final_error_contains_request_id_and_specific_failure(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            invalid = json.loads(json.dumps(SAMPLE_CIRCUIT))
            invalid["circuit"]["connections"][0]["source"] = "missing-board"
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(invalid),
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

        with self.assertRaisesRegex(
            KExaoneError,
            rf"after {MAX_GENERATION_ATTEMPTS} attempts "
            r"\(request_id=[0-9a-f]{32}\).*Connection 'e1'.*missing-board",
        ):
            await client.generate_circuit("LED circuit")

    async def test_retries_transient_api_error_with_a_fresh_request(self):
        request_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            request_body = json.loads(request.content)
            self.assertEqual(len(request_body["messages"]), 2)

            if request_count == 1:
                return httpx.Response(503, json={"detail": "temporary"})
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(SAMPLE_CIRCUIT),
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

        result = await client.generate_circuit("LED circuit")

        self.assertEqual(result.circuit.parts[0].id, "arduino-uno-r3-1")
        self.assertEqual(request_count, 2)

    def test_parses_markdown_wrapped_json_as_fallback(self):
        content = "```json\n{\"title\": \"LED 켜기\"}\n```"
        self.assertEqual(
            KExaoneClient._parse_json_content(content),
            {"title": "LED 켜기"},
        )


if __name__ == "__main__":
    unittest.main()
