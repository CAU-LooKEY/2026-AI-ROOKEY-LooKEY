import json
import unittest

import httpx

from app.core.settings import Settings
from app.schemas.circuit import CircuitGenerationResponse
from app.services.k_exaone import KExaoneClient, _RESPONSE_CACHE


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
    def tearDown(self):
        _RESPONSE_CACHE.clear()

    async def test_generates_and_validates_circuit_response(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            request_body = json.loads(request.content)
            self.assertEqual(request_body["model"], "test-endpoint")
            self.assertFalse(request_body["stream"])
            self.assertEqual(request_body["max_tokens"], 3000)
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
            k_exaone_repair_attempts=2,
        )
        client = KExaoneClient(
            settings,
            transport=httpx.MockTransport(handler),
        )

        result = await client.generate_circuit("LED를 켜줘")

        self.assertEqual(result.title, "LED 켜기")
        self.assertEqual(request_count, 2)

    async def test_reuses_cached_response_for_same_prompt(self):
        request_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
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
        client = KExaoneClient(settings, transport=httpx.MockTransport(handler))

        first = await client.generate_circuit("LED를 켜줘")
        second = await client.generate_circuit(" LED를   켜줘 ")

        self.assertEqual(first.title, second.title)
        self.assertEqual(request_count, 1)

    def test_parses_markdown_wrapped_json_as_fallback(self):
        content = "```json\n{\"title\": \"LED 켜기\"}\n```"
        self.assertEqual(
            KExaoneClient._parse_json_content(content),
            {"title": "LED 켜기"},
        )

    def test_rejects_duplicate_arduino_pin_connections(self):
        duplicated = json.loads(json.dumps(SAMPLE_CIRCUIT))
        duplicated["code"] = "\n".join(duplicated.pop("codeLines"))
        duplicated["circuit"]["connections"].append(
            {
                "id": "e3",
                "source": "arduino",
                "sourcePin": "D3",
                "target": "resistor",
                "targetPin": "LEAD_B",
                "label": "D3 duplicate",
                "color": "#059669",
            }
        )

        with self.assertRaisesRegex(ValueError, "Arduino pin"):
            CircuitGenerationResponse.model_validate(duplicated)

    def test_repairs_common_connection_part_id_aliases(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["parts"].append(
            {
                "id": "pushbutton-6x6",
                "label": "버튼",
                "componentKey": "pushbutton-6x6",
                "position": {"x": 560, "y": 240},
                "width": 100,
            }
        )
        payload["circuit"]["connections"] = [
            {
                "id": "button-wire",
                "source": "ardino",
                "sourcePin": "D2",
                "target": "button",
                "targetPin": "A1",
                "label": "D2 to button",
                "color": "#2563eb",
            }
        ]

        KExaoneClient._repair_connection_part_ids(payload)

        self.assertEqual(payload["circuit"]["connections"][0]["source"], "arduino")
        self.assertEqual(payload["circuit"]["connections"][0]["target"], "pushbutton-6x6")

    def test_repairs_unknown_connection_part_id_from_pin_compatibility(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["connections"] = [
            {
                "id": "resistor-wire",
                "source": "arduino",
                "sourcePin": "D3",
                "target": "current_limiter",
                "targetPin": "LEAD_A",
                "label": "D3 to resistor",
                "color": "#000000",
            }
        ]

        KExaoneClient._repair_connection_part_ids(payload)

        self.assertEqual(payload["circuit"]["connections"][0]["target"], "resistor")

    def test_repairs_direct_led_drive_to_use_series_resistor(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["connections"] = [
            {
                "id": "direct-led",
                "source": "ard",
                "sourcePin": "D3",
                "target": "led",
                "targetPin": "ANODE",
                "label": "D3 to LED",
                "color": "#000000",
            },
            {
                "id": "led-ground",
                "source": "led",
                "sourcePin": "CATHODE",
                "target": "resistor",
                "targetPin": "LEAD_A",
                "label": "LED to resistor",
                "color": "#000000",
            },
            {
                "id": "resistor-ground",
                "source": "resistor",
                "sourcePin": "LEAD_B",
                "target": "ard",
                "targetPin": "GND",
                "label": "resistor to ground",
                "color": "#000000",
            },
        ]

        KExaoneClient._repair_connection_part_ids(payload)
        KExaoneClient._repair_connection_pin_aliases(payload)
        KExaoneClient._repair_led_resistor_series(payload)

        direct = payload["circuit"]["connections"][0]
        ground = payload["circuit"]["connections"][1]
        bridge = next(
            connection
            for connection in payload["circuit"]["connections"]
            if connection["id"] == "resistor-led-series"
        )
        self.assertEqual(direct["source"], "arduino")
        self.assertEqual(direct["target"], "resistor")
        self.assertEqual(direct["targetPin"], "LEAD_A")
        self.assertEqual(ground["source"], "led")
        self.assertEqual(ground["sourcePin"], "CATHODE")
        self.assertEqual(ground["target"], "arduino")
        self.assertTrue(ground["targetPin"].startswith("GND_"))
        self.assertEqual(bridge["source"], "resistor")
        self.assertEqual(bridge["sourcePin"], "LEAD_B")
        self.assertEqual(bridge["target"], "led")
        self.assertEqual(bridge["targetPin"], "ANODE")
        self.assertNotIn(
            "resistor-ground",
            {connection["id"] for connection in payload["circuit"]["connections"]},
        )

    def test_repairs_common_pin_aliases_by_component(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["parts"].append(
            {
                "id": "sensor",
                "label": "HC-SR04",
                "componentKey": "hc-sr04",
                "position": {"x": 560, "y": 240},
                "width": 100,
            }
        )
        payload["circuit"]["connections"] = [
            {
                "id": "sensor-gnd",
                "source": "sensor",
                "sourcePin": "GROUND",
                "target": "arduino",
                "targetPin": "GND",
                "label": "sensor ground",
                "color": "#000000",
            },
            {
                "id": "sensor-trig",
                "source": "arduino",
                "sourcePin": "digital 7",
                "target": "sensor",
                "targetPin": "TRIGGER",
                "label": "sensor trigger",
                "color": "#000000",
            },
            {
                "id": "led-ground",
                "source": "led",
                "sourcePin": "negative",
                "target": "arduino",
                "targetPin": "GROUND",
                "label": "led ground",
                "color": "#000000",
            },
        ]

        KExaoneClient._repair_connection_pin_aliases(payload)

        self.assertEqual(payload["circuit"]["connections"][0]["sourcePin"], "GND")
        self.assertEqual(payload["circuit"]["connections"][0]["targetPin"], "GND_P1")
        self.assertEqual(payload["circuit"]["connections"][1]["sourcePin"], "D7")
        self.assertEqual(payload["circuit"]["connections"][1]["targetPin"], "TRIG")
        self.assertEqual(payload["circuit"]["connections"][2]["sourcePin"], "CATHODE")
        self.assertEqual(payload["circuit"]["connections"][2]["targetPin"], "GND_P2")

    def test_repairs_duplicate_arduino_ground_pins(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["parts"].append(
            {
                "id": "button",
                "label": "버튼",
                "componentKey": "pushbutton-6x6",
                "position": {"x": 560, "y": 240},
                "width": 100,
            }
        )
        payload["circuit"]["connections"] = [
            {
                "id": "button-ground",
                "source": "button",
                "sourcePin": "A1",
                "target": "arduino",
                "targetPin": "GND_P1",
                "label": "button ground",
                "color": "#000000",
            },
            {
                "id": "led-ground",
                "source": "led",
                "sourcePin": "CATHODE",
                "target": "arduino",
                "targetPin": "GND_P1",
                "label": "led ground",
                "color": "#000000",
            },
        ]

        KExaoneClient._repair_duplicate_arduino_power_pins(payload)

        self.assertEqual(
            [
                connection["targetPin"]
                for connection in payload["circuit"]["connections"]
            ],
            ["GND_P1", "GND_P2"],
        )

    def test_removes_button_power_connection_for_input_pullup(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["parts"].append(
            {
                "id": "button",
                "label": "버튼",
                "componentKey": "pushbutton-6x6",
                "position": {"x": 560, "y": 240},
                "width": 100,
            }
        )
        payload["circuit"]["connections"] = [
            {
                "id": "button-signal",
                "source": "arduino",
                "sourcePin": "D2",
                "target": "button",
                "targetPin": "A1",
                "label": "button signal",
                "color": "#000000",
            },
            {
                "id": "button-power",
                "source": "arduino",
                "sourcePin": "5V",
                "target": "button",
                "targetPin": "A2",
                "label": "bad button power",
                "color": "#000000",
            },
        ]

        KExaoneClient._repair_button_input_pullup(payload)

        self.assertEqual(
            [connection["id"] for connection in payload["circuit"]["connections"]],
            ["button-signal"],
        )

    def test_removes_extra_led_cathode_resistor_connection(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["connections"] = [
            {
                "id": "good-series",
                "source": "resistor",
                "sourcePin": "LEAD_B",
                "target": "led",
                "targetPin": "ANODE",
                "label": "series",
                "color": "#000000",
            },
            {
                "id": "bad-cathode",
                "source": "led",
                "sourcePin": "CATHODE",
                "target": "resistor",
                "targetPin": "LEAD_A",
                "label": "bad extra",
                "color": "#000000",
            },
        ]

        KExaoneClient._remove_extra_led_resistor_connections(payload)

        self.assertEqual(
            [connection["id"] for connection in payload["circuit"]["connections"]],
            ["good-series"],
        )

    def test_repairs_duplicate_connection_ids(self):
        payload = json.loads(json.dumps(SAMPLE_CIRCUIT))
        payload["circuit"]["connections"][1]["id"] = payload["circuit"]["connections"][0]["id"]

        KExaoneClient._repair_duplicate_connection_ids(payload)

        self.assertEqual(
            [connection["id"] for connection in payload["circuit"]["connections"]],
            ["e1", "e1-2"],
        )


if __name__ == "__main__":
    unittest.main()
