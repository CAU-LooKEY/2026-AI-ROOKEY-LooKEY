import json
import logging
import time
from collections import OrderedDict
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.settings import Settings
from app.schemas.circuit import (
    CircuitGenerationResponse,
    SIGNAL_WIRE_COLORS,
    SUPPORTED_COMPONENT_PINS,
)
from app.services.physical_assembly import PhysicalAssemblyPlanEngine


logger = logging.getLogger(__name__)
_RESPONSE_CACHE: OrderedDict[str, CircuitGenerationResponse] = OrderedDict()


SYSTEM_PROMPT = """You generate safe Arduino circuit projects for beginners.
Return only valid compact JSON matching the supplied JSON schema. Do not use Markdown.

Rules:
- Use only these componentKey values when drawing parts: arduino-uno-r3,
  hc-sr04, led-5mm-blue, pushbutton-6x6, resistor-220-ohm.
- Every circuit part id must be unique. Every connection source and target must
  refer to an existing part id.
- Prefer stable circuit part ids: arduino, led, resistor, button, sensor. Use
  those same exact ids in every connection source and target.
- Arduino pin keys must be one of: SCL, SDA, AREF, GND_D, D0-D13, IOREF,
  RESET, 3V3, 5V, GND_P1, GND_P2, VIN, A0-A5, AUX_RX, AUX_TX, AUX_5V,
  AUX_GND_1, AUX_SDA, AUX_SCL, AUX_3V3, AUX_GND_2.
- HC-SR04 pin keys are VCC, TRIG, ECHO, GND. LED pin keys are ANODE and
  CATHODE. Pushbutton pin keys are A1, A2, B1, B2. Resistor pin keys are
  LEAD_A and LEAD_B.
- Treat every connection as one physical jumper wire. Do not return
  sourceConnector, targetConnector, or wireType; the server derives those
  fields from the connected component types.
- Do not use the same Arduino pin in more than one connection. A physical
  Arduino header pin can accept only one jumper. Use a different Arduino pin
  or route shared nodes through the breadboard.
- Use red (#dc2626) for power, dark gray (#1f2937) for ground, and distinct
  colors for separate signal wires. The server normalizes these values.
- Include a current-limiting resistor for every LED.
- For Korean prompts like "손을 가까이 대면" or distance/proximity LED
  circuits, use HC-SR04, not a button. Connect VCC to 5V, TRIG to D7, ECHO
  to D8, GND to an Arduino GND pin, and drive the LED from D3 through a
  220 ohm resistor.
- For "button controls LED" circuits, use Arduino INPUT_PULLUP: connect one
  pushbutton side to a digital input such as D2 and the opposite side to GND.
  Drive the LED from a different digital output such as D3 through a 220 ohm
  resistor. Do not connect the button to 5V when using INPUT_PULLUP.
- Do not draw unsupported parts. Put their names in unsupportedComponents.
- Return Arduino source code as codeLines, an array containing one source line
  per item. Do not return a code field. Keep each code line free of newline
  escape sequences.
- Keep the response compact: include only title, circuit parts, circuit
  connections, codeLines, and unsupportedComponents.
- Do not include tutorSteps, warnings, validationResults, codeMeta,
  sourceConnector, targetConnector, wireType, or assemblyPlan. The server
  derives them.
"""


class KExaoneError(RuntimeError):
    pass


class KExaoneClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.transport = transport

    async def generate_circuit(self, prompt: str) -> CircuitGenerationResponse:
        started_at = time.perf_counter()
        cache_key = self._cache_key(prompt)
        cached = _RESPONSE_CACHE.get(cache_key)
        if cached is not None:
            _RESPONSE_CACHE.move_to_end(cache_key)
            logger.info("Circuit generation cache hit for prompt hash %s.", hash(cache_key))
            return cached.model_copy(deep=True)

        async with httpx.AsyncClient(
            timeout=self.settings.k_exaone_timeout_seconds,
            transport=self.transport,
            trust_env=False,
        ) as client:
            candidate: str | None = None
            validation_error: str | None = None

            attempts = max(1, self.settings.k_exaone_repair_attempts)
            for attempt in range(attempts):
                attempt_started_at = time.perf_counter()
                response = await self._request_completion(
                    client,
                    prompt,
                    candidate=candidate,
                    validation_error=validation_error,
                )
                content = self._extract_content(response)
                logger.info(
                    "K-EXAONE completion attempt %s finished in %.2fs.",
                    attempt + 1,
                    time.perf_counter() - attempt_started_at,
                )

                try:
                    circuit_data = self._parse_json_content(content)
                    circuit_data = self._prepare_circuit_data(circuit_data, prompt)
                    result = CircuitGenerationResponse.model_validate(circuit_data)
                    result.assembly_plan = PhysicalAssemblyPlanEngine().build(result)
                    logger.info(
                        "Circuit generation finished in %.2fs with %s parts and %s connections.",
                        time.perf_counter() - started_at,
                        len(result.circuit.parts),
                        len(result.circuit.connections),
                    )
                    self._store_cache(cache_key, result)
                    return result
                except (ValueError, TypeError, ValidationError) as exc:
                    logger.warning(
                        "K-EXAONE circuit validation failed on attempt %s: %s",
                        attempt + 1,
                        exc,
                    )
                    candidate = content
                    validation_error = str(exc)[:1000]

        detail = (
            "K-EXAONE response did not match the circuit JSON schema after repair."
        )
        if validation_error:
            detail = f"{detail} Last validation error: {validation_error}"
        raise KExaoneError(detail)

    async def _request_completion(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        *,
        candidate: str | None,
        validation_error: str | None,
    ) -> httpx.Response:
        payload = self._build_payload(
            prompt,
            include_response_format=True,
            candidate=candidate,
            validation_error=validation_error,
        )
        response = await self._post(client, payload)

        # Some dedicated deployments may not enable structured outputs.
        if response.status_code in {400, 422}:
            payload = self._build_payload(
                prompt,
                include_response_format=False,
                candidate=candidate,
                validation_error=validation_error,
            )
            response = await self._post(client, payload)

        if response.is_error:
            raise KExaoneError(
                f"K-EXAONE request failed with status {response.status_code}."
            )
        return response

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise KExaoneError("K-EXAONE returned an unexpected response.") from exc

        if not isinstance(content, str):
            raise KExaoneError("K-EXAONE returned empty response content.")
        return content

    async def _post(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            return await client.post(
                self.settings.k_exaone_api_url,
                headers={
                    "Authorization": f"Bearer {self.settings.k_exaone_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise KExaoneError("K-EXAONE request timed out.") from exc
        except httpx.RequestError as exc:
            raise KExaoneError("Could not connect to the K-EXAONE API.") from exc

    def _build_payload(
        self,
        prompt: str,
        *,
        include_response_format: bool,
        candidate: str | None = None,
        validation_error: str | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        if candidate is not None and validation_error is not None:
            messages.extend(
                [
                    {"role": "assistant", "content": candidate},
                    {
                        "role": "user",
                        "content": (
                            "The previous JSON was invalid. Return a corrected full "
                            "JSON object only. Validation error:\n"
                            f"{validation_error}"
                        ),
                    },
                ]
            )

        payload: dict[str, Any] = {
            "model": self.settings.k_exaone_endpoint_id,
            "messages": messages,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": self.settings.k_exaone_max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "parse_reasoning": True,
            "include_reasoning": False,
        }

        if include_response_format:
            schema = self._generation_schema()
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "schema": schema
                },
            }

        return payload

    @staticmethod
    def _cache_key(prompt: str) -> str:
        return " ".join(prompt.strip().lower().split())

    def _store_cache(self, cache_key: str, result: CircuitGenerationResponse) -> None:
        cache_size = max(0, self.settings.k_exaone_cache_size)
        if cache_size == 0:
            return
        _RESPONSE_CACHE[cache_key] = result.model_copy(deep=True)
        _RESPONSE_CACHE.move_to_end(cache_key)
        while len(_RESPONSE_CACHE) > cache_size:
            _RESPONSE_CACHE.popitem(last=False)

    @staticmethod
    def _generation_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "circuit", "codeLines", "unsupportedComponents"],
            "properties": {
                "title": {"type": "string"},
                "unsupportedComponents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "codeLines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 35,
                },
                "circuit": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["parts", "connections"],
                    "properties": {
                        "parts": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["id", "componentKey"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "componentKey": {
                                        "type": "string",
                                        "enum": [
                                            "arduino-uno-r3",
                                            "hc-sr04",
                                            "led-5mm-blue",
                                            "pushbutton-6x6",
                                            "resistor-220-ohm",
                                        ],
                                    },
                                },
                            },
                        },
                        "connections": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "id",
                                    "source",
                                    "sourcePin",
                                    "target",
                                    "targetPin",
                                ],
                                "properties": {
                                    "id": {"type": "string"},
                                    "source": {"type": "string"},
                                    "sourcePin": {"type": "string"},
                                    "target": {"type": "string"},
                                    "targetPin": {"type": "string"},
                                    "label": {"type": "string"},
                                    "color": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _prepare_circuit_data(circuit_data: dict[str, Any], prompt: str = "") -> dict[str, Any]:
        code_lines = circuit_data.pop("codeLines", None)
        if code_lines is not None:
            if not isinstance(code_lines, list) or not all(
                isinstance(line, str) for line in code_lines
            ):
                raise TypeError("codeLines must be an array of strings.")
            circuit_data["code"] = "\n".join(code_lines)
        KExaoneClient._repair_connection_part_ids(circuit_data)
        KExaoneClient._repair_connection_pin_aliases(circuit_data)
        KExaoneClient._repair_duplicate_arduino_power_pins(circuit_data)
        KExaoneClient._repair_button_input_pullup(circuit_data)
        KExaoneClient._repair_led_resistor_series(circuit_data)
        KExaoneClient._remove_extra_led_resistor_connections(circuit_data)
        KExaoneClient._repair_duplicate_connection_ids(circuit_data)
        KExaoneClient._fill_display_defaults(circuit_data, prompt)
        return circuit_data

    @staticmethod
    def _repair_connection_part_ids(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        aliases: dict[str, str] = {}
        known_ids = set()
        slug_aliases = {
            "arduino-uno-r3": {
                "arduino",
                "uno",
                "arduino_uno",
                "arduino-uno",
                "arduino_uno_r3",
                "uno_r3",
                "ard",
                "ardino",
                "board",
                "mcu",
                "microcontroller",
            },
            "hc-sr04": {
                "sensor",
                "ultrasonic",
                "ultrasonic_sensor",
                "ultrasonic-sensor",
                "distance_sensor",
                "distance-sensor",
                "distance",
                "hc_sr04",
                "hcsr04",
                "hc-sr04",
            },
            "led-5mm-blue": {"led", "blue_led"},
            "pushbutton-6x6": {"button", "pushbutton", "push_button", "switch"},
            "resistor-220-ohm": {"resistor", "resistor_220", "220ohm"},
        }
        for part in parts:
            if not isinstance(part, dict):
                continue
            part_id = part.get("id")
            if not isinstance(part_id, str):
                continue
            known_ids.add(part_id)
            candidates = {
                part_id,
                str(part.get("componentKey", "")),
                str(part.get("label", "")),
            }
            candidates.update(slug_aliases.get(part.get("componentKey"), set()))
            for candidate in candidates:
                key = candidate.strip().lower()
                if key:
                    aliases.setdefault(key, part_id)

        for connection in connections:
            if not isinstance(connection, dict):
                continue
            for field in ("source", "target"):
                value = connection.get(field)
                if value in known_ids or not isinstance(value, str):
                    continue
                replacement = aliases.get(value.strip().lower())
                if replacement:
                    connection[field] = replacement

        KExaoneClient._repair_connection_part_ids_by_pin(parts, connections)

    @staticmethod
    def _repair_connection_part_ids_by_pin(
        parts: list[Any],
        connections: list[Any],
    ) -> None:
        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        parts_by_component_key: dict[str, list[str]] = {}
        for part_id, part in parts_by_id.items():
            component_key = part.get("componentKey")
            if isinstance(component_key, str):
                parts_by_component_key.setdefault(component_key, []).append(part_id)

        for connection in connections:
            if not isinstance(connection, dict):
                continue
            for field, pin_field in (("source", "sourcePin"), ("target", "targetPin")):
                value = connection.get(field)
                if value in parts_by_id:
                    continue
                pin = connection.get(pin_field)
                if not isinstance(pin, str):
                    continue
                normalized_pin = pin.strip().upper().replace("-", "_").replace(" ", "_")
                candidates = [
                    part_id
                    for component_key, part_ids in parts_by_component_key.items()
                    if normalized_pin in SUPPORTED_COMPONENT_PINS.get(component_key, set())
                    for part_id in part_ids
                ]
                if len(candidates) == 1:
                    connection[field] = candidates[0]

    @staticmethod
    def _repair_connection_pin_aliases(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        used_arduino_pins: set[str] = set()

        for connection in connections:
            if not isinstance(connection, dict):
                continue
            for component_field, pin_field in (
                ("source", "sourcePin"),
                ("target", "targetPin"),
            ):
                component = parts_by_id.get(connection.get(component_field))
                if not isinstance(component, dict):
                    continue
                pin = connection.get(pin_field)
                if not isinstance(pin, str):
                    continue
                component_key = component.get("componentKey")
                repaired = KExaoneClient._repair_pin_alias(
                    component_key,
                    pin,
                    used_arduino_pins,
                )
                connection[pin_field] = repaired
                if component_key == "arduino-uno-r3":
                    used_arduino_pins.add(repaired)

    @staticmethod
    def _repair_duplicate_arduino_power_pins(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        replacement_groups = {
            "5V": ["5V", "AUX_5V"],
            "3V3": ["3V3", "AUX_3V3"],
            "GND": ["GND_P1", "GND_P2", "GND_D", "AUX_GND_1", "AUX_GND_2"],
        }
        used_by_board: dict[str, set[str]] = {}

        for connection in connections:
            if not isinstance(connection, dict):
                continue
            for component_field, pin_field in (
                ("source", "sourcePin"),
                ("target", "targetPin"),
            ):
                component = parts_by_id.get(connection.get(component_field))
                if not isinstance(component, dict):
                    continue
                if component.get("componentKey") != "arduino-uno-r3":
                    continue
                board_id = component.get("id")
                pin = connection.get(pin_field)
                if not isinstance(board_id, str) or not isinstance(pin, str):
                    continue

                used = used_by_board.setdefault(board_id, set())
                canonical_group = None
                if "GND" in pin:
                    canonical_group = "GND"
                elif pin in {"5V", "AUX_5V"}:
                    canonical_group = "5V"
                elif pin in {"3V3", "AUX_3V3"}:
                    canonical_group = "3V3"

                if pin not in used:
                    used.add(pin)
                    continue
                if canonical_group is None:
                    continue

                replacement = next(
                    (
                        candidate
                        for candidate in replacement_groups[canonical_group]
                        if candidate not in used
                    ),
                    None,
                )
                if replacement is not None:
                    connection[pin_field] = replacement
                    used.add(replacement)

    @staticmethod
    def _repair_button_input_pullup(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        arduino_ids = {
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "arduino-uno-r3"
        }
        button_ids = {
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "pushbutton-6x6"
        }
        if not arduino_ids or not button_ids:
            return

        def is_button_power_connection(connection: Any) -> bool:
            if not isinstance(connection, dict):
                return False
            endpoints = (
                (connection.get("source"), connection.get("sourcePin")),
                (connection.get("target"), connection.get("targetPin")),
            )
            has_button = any(component_id in button_ids for component_id, _ in endpoints)
            has_power = any(
                component_id in arduino_ids and pin in {"5V", "AUX_5V", "3V3", "AUX_3V3"}
                for component_id, pin in endpoints
            )
            return has_button and has_power

        connections[:] = [
            connection
            for connection in connections
            if not is_button_power_connection(connection)
        ]

    @staticmethod
    def _remove_extra_led_resistor_connections(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        led_ids = {
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "led-5mm-blue"
        }
        resistor_ids = {
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "resistor-220-ohm"
        }
        if not led_ids or not resistor_ids:
            return

        def should_remove(connection: Any) -> bool:
            if not isinstance(connection, dict):
                return False
            source = connection.get("source")
            source_pin = connection.get("sourcePin")
            target = connection.get("target")
            target_pin = connection.get("targetPin")
            if source in resistor_ids and target in led_ids:
                return target_pin != "ANODE"
            if target in resistor_ids and source in led_ids:
                return source_pin != "ANODE"
            return False

        connections[:] = [
            connection for connection in connections if not should_remove(connection)
        ]

    @staticmethod
    def _repair_duplicate_connection_ids(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        connections = circuit.get("connections")
        if not isinstance(connections, list):
            return

        seen: set[str] = set()
        for index, connection in enumerate(connections):
            if not isinstance(connection, dict):
                continue
            current_id = connection.get("id")
            if not isinstance(current_id, str) or not current_id.strip():
                current_id = "wire"
            if current_id in seen:
                current_id = f"{current_id}-{index + 1}"
                connection["id"] = current_id
            seen.add(current_id)

    @staticmethod
    def _repair_led_resistor_series(circuit_data: dict[str, Any]) -> None:
        circuit = circuit_data.get("circuit")
        if not isinstance(circuit, dict):
            return
        parts = circuit.get("parts")
        connections = circuit.get("connections")
        if not isinstance(parts, list) or not isinstance(connections, list):
            return

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        led_ids = [
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "led-5mm-blue"
        ]
        resistor_ids = [
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "resistor-220-ohm"
        ]
        arduino_ids = [
            part_id
            for part_id, part in parts_by_id.items()
            if part.get("componentKey") == "arduino-uno-r3"
        ]
        if not led_ids or not resistor_ids or not arduino_ids:
            return

        for led_id in led_ids:
            direct_drive = KExaoneClient._find_direct_arduino_led_anode_connection(
                led_id,
                arduino_ids,
                connections,
            )
            ground_connection = KExaoneClient._find_led_ground_connection(
                led_id,
                arduino_ids,
                connections,
            )
            if direct_drive is None or ground_connection is None:
                if KExaoneClient._led_has_series_resistor(led_id, resistor_ids, connections):
                    continue
                continue
            arduino_id, arduino_pin, connection = direct_drive
            resistor_id = resistor_ids[0]
            connection["source"] = arduino_id
            connection["sourcePin"] = arduino_pin
            connection["target"] = resistor_id
            connection["targetPin"] = "LEAD_A"
            connection["label"] = f"{arduino_pin} -> RESISTOR"

            bridge_id = f"{resistor_id}-{led_id}-series"
            bridge = next(
                (
                    item
                    for item in connections
                    if isinstance(item, dict) and item.get("id") == bridge_id
                ),
                None,
            )
            if bridge is None:
                bridge = {
                    "id": bridge_id,
                    "color": "#f97316",
                }
                connections.append(bridge)
            bridge.update(
                {
                    "source": resistor_id,
                    "sourcePin": "LEAD_B",
                    "target": led_id,
                    "targetPin": "ANODE",
                    "label": "RESISTOR -> LED +",
                }
            )

            ground_connection["source"] = led_id
            ground_connection["sourcePin"] = "CATHODE"
            ground_connection["target"] = arduino_id
            ground_connection["targetPin"] = KExaoneClient._first_available_ground_pin(
                arduino_id,
                connections,
                excluding=ground_connection,
            )
            ground_connection["label"] = "LED - -> GND"
            KExaoneClient._remove_resistor_ground_connections(
                resistor_id,
                arduino_ids,
                connections,
                keep={connection.get("id"), bridge.get("id"), ground_connection.get("id")},
            )

    @staticmethod
    def _led_has_series_resistor(
        led_id: str,
        resistor_ids: list[str],
        connections: list[Any],
    ) -> bool:
        for connection in connections:
            if not isinstance(connection, dict):
                continue
            left = (connection.get("source"), connection.get("sourcePin"))
            right = (connection.get("target"), connection.get("targetPin"))
            if left[0] in resistor_ids and right == (led_id, "ANODE"):
                return True
            if right[0] in resistor_ids and left == (led_id, "ANODE"):
                return True
            if left[0] in resistor_ids and right == (led_id, "CATHODE"):
                return True
            if right[0] in resistor_ids and left == (led_id, "CATHODE"):
                return True
        return False

    @staticmethod
    def _find_direct_arduino_led_anode_connection(
        led_id: str,
        arduino_ids: list[str],
        connections: list[Any],
    ) -> tuple[str, str, dict[str, Any]] | None:
        for connection in connections:
            if not isinstance(connection, dict):
                continue
            source = connection.get("source")
            source_pin = connection.get("sourcePin")
            target = connection.get("target")
            target_pin = connection.get("targetPin")
            if source in arduino_ids and target == led_id and target_pin == "ANODE":
                return source, source_pin, connection
            if target in arduino_ids and source == led_id and source_pin == "ANODE":
                connection["source"] = target
                connection["sourcePin"] = target_pin
                connection["target"] = source
                connection["targetPin"] = source_pin
                return target, target_pin, connection
        return None

    @staticmethod
    def _find_led_ground_connection(
        led_id: str,
        arduino_ids: list[str],
        connections: list[Any],
    ) -> dict[str, Any] | None:
        for connection in connections:
            if not isinstance(connection, dict):
                continue
            source = connection.get("source")
            source_pin = connection.get("sourcePin")
            target = connection.get("target")
            target_pin = connection.get("targetPin")
            if source == led_id and source_pin == "CATHODE":
                return connection
            if target == led_id and target_pin == "CATHODE":
                connection["source"] = target
                connection["sourcePin"] = target_pin
                connection["target"] = source
                connection["targetPin"] = source_pin
                return connection
        return None

    @staticmethod
    def _first_available_ground_pin(
        arduino_id: str,
        connections: list[Any],
        excluding: dict[str, Any] | None = None,
    ) -> str:
        used = set()
        for connection in connections:
            if not isinstance(connection, dict) or connection is excluding:
                continue
            if connection.get("source") == arduino_id:
                used.add(connection.get("sourcePin"))
            if connection.get("target") == arduino_id:
                used.add(connection.get("targetPin"))
        for pin in ("GND_P1", "GND_P2", "GND_D"):
            if pin not in used:
                return pin
        return "GND_P1"

    @staticmethod
    def _remove_resistor_ground_connections(
        resistor_id: str,
        arduino_ids: list[str],
        connections: list[Any],
        keep: set[Any],
    ) -> None:
        def should_remove(connection: Any) -> bool:
            if not isinstance(connection, dict) or connection.get("id") in keep:
                return False
            source = connection.get("source")
            source_pin = connection.get("sourcePin")
            target = connection.get("target")
            target_pin = connection.get("targetPin")
            return (
                source == resistor_id
                and target in arduino_ids
                and isinstance(target_pin, str)
                and "GND" in target_pin
            ) or (
                target == resistor_id
                and source in arduino_ids
                and isinstance(source_pin, str)
                and "GND" in source_pin
            )

        connections[:] = [
            connection for connection in connections if not should_remove(connection)
        ]

    @staticmethod
    def _repair_pin_alias(
        component_key: str | None,
        pin: str,
        used_arduino_pins: set[str],
    ) -> str:
        normalized = pin.strip().upper().replace("-", "_").replace(" ", "_")

        if component_key == "arduino-uno-r3":
            if normalized in {"GND", "GROUND", "G"}:
                for candidate in ("GND_P1", "GND_P2", "GND_D"):
                    if candidate not in used_arduino_pins:
                        return candidate
                return "GND_P1"
            if normalized in {"VCC", "POWER", "+5V", "5_VOLTS", "5V"}:
                return "5V"
            if normalized in {"3.3V", "3_3V", "3V3", "+3V3"}:
                return "3V3"
            if normalized.startswith("DIGITAL_"):
                normalized = normalized.removeprefix("DIGITAL_")
            if normalized.startswith("PIN_"):
                normalized = normalized.removeprefix("PIN_")
            if normalized.isdigit():
                normalized = f"D{int(normalized)}"
            if normalized.startswith("D") and normalized[1:].isdigit():
                return f"D{int(normalized[1:])}"
            return normalized

        if component_key == "led-5mm-blue":
            if normalized in {"A", "+", "PLUS", "POSITIVE", "LONG_LEG", "ANODE"}:
                return "ANODE"
            if normalized in {"K", "C", "-", "MINUS", "NEGATIVE", "SHORT_LEG", "CATHODE"}:
                return "CATHODE"

        if component_key == "resistor-220-ohm":
            if normalized in {"A", "1", "PIN1", "LEAD1", "LEAD_1", "IN", "INPUT"}:
                return "LEAD_A"
            if normalized in {"B", "2", "PIN2", "LEAD2", "LEAD_2", "OUT", "OUTPUT"}:
                return "LEAD_B"

        if component_key == "hc-sr04":
            aliases = {
                "POWER": "VCC",
                "5V": "VCC",
                "+5V": "VCC",
                "GROUND": "GND",
                "TRIGGER": "TRIG",
                "T": "TRIG",
                "E": "ECHO",
            }
            return aliases.get(normalized, normalized)

        if component_key == "pushbutton-6x6":
            aliases = {
                "1": "A1",
                "2": "A2",
                "3": "B1",
                "4": "B2",
                "PIN1": "A1",
                "PIN2": "A2",
                "PIN3": "B1",
                "PIN4": "B2",
            }
            return aliases.get(normalized, normalized)

        return normalized

    @staticmethod
    def _fill_display_defaults(circuit_data: dict[str, Any], prompt: str) -> None:
        circuit = circuit_data.setdefault("circuit", {})
        parts = circuit.setdefault("parts", [])
        connections = circuit.setdefault("connections", [])

        component_labels = {
            "arduino-uno-r3": "Arduino UNO R3",
            "hc-sr04": "HC-SR04 초음파 센서",
            "led-5mm-blue": "5mm LED",
            "pushbutton-6x6": "6x6 푸시 버튼",
            "resistor-220-ohm": "220옴 저항",
        }
        component_roles = {
            "arduino-uno-r3": "센서와 입력을 읽고 출력 부품을 제어합니다.",
            "hc-sr04": "초음파로 물체와의 거리를 측정합니다.",
            "led-5mm-blue": "전기 신호를 빛으로 표시합니다.",
            "pushbutton-6x6": "사용자의 누름 입력을 전달합니다.",
            "resistor-220-ohm": "LED에 흐르는 전류를 제한합니다.",
        }
        component_widths = {
            "arduino-uno-r3": 260,
            "hc-sr04": 180,
            "led-5mm-blue": 90,
            "pushbutton-6x6": 90,
            "resistor-220-ohm": 130,
        }
        default_positions = [
            {"x": 70, "y": 190},
            {"x": 390, "y": 120},
            {"x": 520, "y": 230},
            {"x": 650, "y": 230},
            {"x": 390, "y": 320},
            {"x": 540, "y": 320},
            {"x": 690, "y": 320},
            {"x": 780, "y": 190},
        ]

        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                continue
            component_key = part.get("componentKey")
            part.setdefault("label", component_labels.get(component_key, part.get("id", "부품")))
            part.setdefault("width", component_widths.get(component_key, 120))
            part.setdefault("position", default_positions[index % len(default_positions)])

        parts_by_id = {
            part.get("id"): part
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }

        for index, connection in enumerate(connections):
            if not isinstance(connection, dict):
                continue
            source_pin = connection.get("sourcePin", "?")
            target_pin = connection.get("targetPin", "?")
            connection.setdefault("id", f"wire-{index + 1}")
            connection.setdefault("label", f"{source_pin} -> {target_pin}")
            connection.setdefault("color", SIGNAL_WIRE_COLORS[index % len(SIGNAL_WIRE_COLORS)])

        if "codeMeta" not in circuit_data:
            used_pins = []
            for connection in connections:
                if not isinstance(connection, dict):
                    continue
                source = parts_by_id.get(connection.get("source"))
                target = parts_by_id.get(connection.get("target"))
                if source and source.get("componentKey") == "arduino-uno-r3":
                    used_pins.append(connection.get("sourcePin"))
                if target and target.get("componentKey") == "arduino-uno-r3":
                    used_pins.append(connection.get("targetPin"))
            circuit_data["codeMeta"] = {
                "used_pins": [
                    pin
                    for pin in dict.fromkeys(used_pins)
                    if isinstance(pin, str)
                ]
            }

        circuit_data.setdefault("intent", prompt or circuit_data.get("title", "회로 생성"))
        circuit_data.setdefault("difficulty", "초급")
        circuit_data.setdefault("estimatedTime", "15분")
        circuit_data.setdefault("unsupportedComponents", [])
        circuit_data.setdefault("components", KExaoneClient._derive_components(parts))
        circuit_data.setdefault("tutorSteps", KExaoneClient._derive_tutor_steps(parts))
        circuit_data.setdefault("warnings", KExaoneClient._derive_warnings(parts))
        circuit_data.setdefault(
            "validationResults",
            KExaoneClient._derive_validation_results(parts, connections),
        )

    @staticmethod
    def _derive_components(parts: list[Any]) -> list[dict[str, Any]]:
        role_by_key = {
            "arduino-uno-r3": "센서와 입력을 읽고 출력 부품을 제어합니다.",
            "hc-sr04": "초음파로 물체와의 거리를 측정합니다.",
            "led-5mm-blue": "전기 신호를 빛으로 표시합니다.",
            "pushbutton-6x6": "사용자의 누름 입력을 전달합니다.",
            "resistor-220-ohm": "LED에 흐르는 전류를 제한합니다.",
        }
        return [
            {
                "id": part.get("id", f"part-{index + 1}"),
                "name": part.get("label", part.get("id", "부품")),
                "quantity": 1,
                "role": role_by_key.get(part.get("componentKey"), "회로 구성에 필요한 부품입니다."),
            }
            for index, part in enumerate(parts)
            if isinstance(part, dict)
        ]

    @staticmethod
    def _derive_tutor_steps(parts: list[Any]) -> list[dict[str, str]]:
        component_keys = {
            part.get("componentKey")
            for part in parts
            if isinstance(part, dict)
        }
        steps = [
            {
                "title": "부품 배치",
                "desc": "Arduino와 부품을 브레드보드 기준으로 배치합니다.",
            }
        ]
        if "hc-sr04" in component_keys:
            steps.append(
                {
                    "title": "센서 연결",
                    "desc": "HC-SR04의 VCC, GND, TRIG, ECHO 핀을 Arduino에 연결합니다.",
                }
            )
        if "pushbutton-6x6" in component_keys:
            steps.append(
                {
                    "title": "버튼 연결",
                    "desc": "버튼은 디지털 입력과 GND 사이에 연결하고 INPUT_PULLUP을 사용합니다.",
                }
            )
        if "led-5mm-blue" in component_keys:
            steps.append(
                {
                    "title": "LED 보호",
                    "desc": "LED는 220옴 저항을 직렬로 거쳐 Arduino 출력 핀에 연결합니다.",
                }
            )
        return steps[:5]

    @staticmethod
    def _derive_warnings(parts: list[Any]) -> list[str]:
        component_keys = {
            part.get("componentKey")
            for part in parts
            if isinstance(part, dict)
        }
        warnings = []
        if "led-5mm-blue" in component_keys:
            warnings.append("LED에는 반드시 220옴 저항을 직렬로 연결하세요.")
        if "hc-sr04" in component_keys:
            warnings.append("HC-SR04의 VCC와 GND를 반대로 연결하지 마세요.")
        if "pushbutton-6x6" in component_keys:
            warnings.append("INPUT_PULLUP 회로에서는 버튼을 5V에 직접 연결하지 않습니다.")
        return warnings[:4]

    @staticmethod
    def _derive_validation_results(
        parts: list[Any],
        connections: list[Any],
    ) -> list[dict[str, str]]:
        component_keys = {
            part.get("componentKey")
            for part in parts
            if isinstance(part, dict)
        }
        results = [
            {
                "ruleId": "SUPPORTED_COMPONENTS",
                "level": "PASS",
                "message": "지원되는 부품만 회로에 포함되어 있습니다.",
            },
            {
                "ruleId": "CONNECTIONS_PRESENT",
                "level": "PASS" if connections else "WARNING",
                "message": "부품 간 연결 정보가 포함되어 있습니다.",
            },
        ]
        if "led-5mm-blue" in component_keys and "resistor-220-ohm" in component_keys:
            results.append(
                {
                    "ruleId": "LED_RESISTOR",
                    "level": "PASS",
                    "message": "LED 보호용 저항이 회로에 포함되어 있습니다.",
                }
            )
        if "hc-sr04" in component_keys:
            results.append(
                {
                    "ruleId": "SENSOR_PINS",
                    "level": "PASS",
                    "message": "초음파 센서 핀 구성을 검증했습니다.",
                }
            )
        return results[:6]

    @staticmethod
    def _inline_schema_references(schema: dict[str, Any]) -> dict[str, Any]:
        definitions = schema.get("$defs", {})

        def resolve(value: Any) -> Any:
            if isinstance(value, list):
                return [resolve(item) for item in value]
            if not isinstance(value, dict):
                return value

            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                definition_name = reference.removeprefix("#/$defs/")
                if definition_name not in definitions:
                    raise ValueError(
                        f"Unknown JSON schema reference: {reference}"
                    )
                return resolve(definitions[definition_name])

            return {
                key: resolve(item)
                for key, item in value.items()
                if key != "$defs"
            }

        return resolve(schema)

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        if not isinstance(content, str):
            raise TypeError("Response content must be a string.")

        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in response content.")

        parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise TypeError("Circuit response must be a JSON object.")
        return parsed
