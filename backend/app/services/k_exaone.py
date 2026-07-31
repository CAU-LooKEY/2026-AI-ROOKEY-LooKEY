import json
import logging
import uuid
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.settings import Settings
from app.schemas.circuit import CircuitGenerationResponse
from app.services.circuit_contract import normalize_circuit_contract
from app.services.component_rules import component_prompt_catalog
from app.services.physical_assembly import PhysicalAssemblyPlanEngine


logger = logging.getLogger(__name__)

MAX_GENERATION_ATTEMPTS = 3
MAX_RESPONSE_TOKENS = 8192
MAX_REPAIR_CANDIDATE_CHARS = 12000


SYSTEM_PROMPT = f"""You generate safe Arduino circuit projects for beginners.
Return only valid JSON matching the supplied JSON schema. Do not use Markdown.

Rules:
- Use only the componentKey and pin values in this catalog:
{component_prompt_catalog()}
- Every circuit part id must be unique. Every connection source and target must
  refer to an existing part id.
- In every connection, source and target are part ids, while sourcePin and
  targetPin are pin names. Never put a pin name in source or target, and never
  put a part id in sourcePin or targetPin.
- Treat every connection as one physical jumper wire. Do not return
  sourceConnector, targetConnector, or wireType; the server derives those
  fields from the connected component types.
- Use red (#dc2626) for power, dark gray (#1f2937) for ground, and distinct
  colors for separate signal wires. The server normalizes these values.
- Include a current-limiting resistor for every LED.
- Do not draw unsupported parts. Put their names in unsupportedComponents.
- Keep part positions inside an 850 by 450 canvas and avoid overlapping parts.
- codeMeta.used_pins must agree with the pins used by the Arduino code.
- Return Arduino source code as codeLines, an array containing one source line
  per item. Do not return a code field. Keep each code line free of newline
  escape sequences.
- Keep the response compact: use at most 40 codeLines, 5 tutorSteps, 4
  warnings, and 6 validationResults. Keep descriptions to one short sentence.
- validationResults must describe safety and circuit consistency checks.
- validationResults.level must be PASS, WARNING, or ERROR. Use PASS when a
  check is satisfied, WARNING for a usable circuit that needs attention, and
  ERROR only when the returned circuit is actually invalid.
- Write all user-facing explanations in Korean.
"""


class KExaoneError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class KExaoneClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.transport = transport

    async def generate_circuit(self, prompt: str) -> CircuitGenerationResponse:
        request_id = uuid.uuid4().hex
        async with httpx.AsyncClient(
            timeout=self.settings.k_exaone_timeout_seconds,
            transport=self.transport,
        ) as client:
            candidate: str | None = None
            validation_error: str | None = None

            for attempt in range(MAX_GENERATION_ATTEMPTS):
                try:
                    response = await self._request_completion(
                        client,
                        prompt,
                        candidate=candidate,
                        validation_error=validation_error,
                    )
                    content, finish_reason = self._extract_completion(response)
                except KExaoneError as exc:
                    logger.warning(
                        "K-EXAONE request failed request_id=%s attempt=%s: %s",
                        request_id,
                        attempt + 1,
                        exc,
                    )
                    if (
                        not exc.retryable
                        or attempt + 1 == MAX_GENERATION_ATTEMPTS
                    ):
                        raise KExaoneError(
                            f"{exc} (request_id={request_id})"
                        ) from exc
                    candidate = None
                    validation_error = None
                    continue

                logger.info(
                    "K-EXAONE response request_id=%s attempt=%s "
                    "finish_reason=%s chars=%s",
                    request_id,
                    attempt + 1,
                    finish_reason,
                    len(content),
                )
                logger.info(
                    "K-EXAONE raw response request_id=%s attempt=%s content=%s",
                    request_id,
                    attempt + 1,
                    content,
                )

                try:
                    if finish_reason == "length":
                        raise ValueError(
                            "K-EXAONE response was truncated because the token "
                            "limit was reached."
                        )
                    circuit_data = self._parse_json_content(content)
                    circuit_data = self._prepare_circuit_data(circuit_data)
                    circuit_data = normalize_circuit_contract(circuit_data)
                    result = CircuitGenerationResponse.model_validate(circuit_data)
                    result.assembly_plan = PhysicalAssemblyPlanEngine().build(result)
                    return result
                except (ValueError, TypeError, ValidationError) as exc:
                    logger.warning(
                        "K-EXAONE validation failed request_id=%s attempt=%s: %s",
                        request_id,
                        attempt + 1,
                        exc,
                    )
                    candidate = (
                        content
                        if finish_reason != "length"
                        and len(content) <= MAX_REPAIR_CANDIDATE_CHARS
                        else None
                    )
                    validation_error = str(exc)[:2000]

        raise KExaoneError(
            "K-EXAONE response validation failed after "
            f"{MAX_GENERATION_ATTEMPTS} attempts "
            f"(request_id={request_id}): {validation_error}"
        )

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
                f"K-EXAONE request failed with status {response.status_code}.",
                retryable=(
                    response.status_code == 429
                    or response.status_code >= 500
                ),
            )
        return response

    @staticmethod
    def _extract_completion(response: httpx.Response) -> tuple[str, str | None]:
        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise KExaoneError(
                "K-EXAONE returned an unexpected response.",
                retryable=True,
            ) from exc

        if not isinstance(content, str):
            raise KExaoneError(
                "K-EXAONE returned empty response content.",
                retryable=True,
            )
        if finish_reason is not None and not isinstance(finish_reason, str):
            finish_reason = str(finish_reason)
        return content, finish_reason

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        content, _ = KExaoneClient._extract_completion(response)
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
            raise KExaoneError(
                "K-EXAONE request timed out.",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise KExaoneError(
                "Could not connect to the K-EXAONE API.",
                retryable=True,
            ) from exc

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
        if validation_error is not None:
            if candidate is not None:
                messages.append({"role": "assistant", "content": candidate})
            compact_instruction = ""
            if "truncated" in validation_error.casefold():
                compact_instruction = (
                    "\nThe response hit the token limit. Make the replacement "
                    "substantially shorter: minimize labels and descriptions, "
                    "omit code comments, and keep only essential code lines."
                )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous response was invalid. Return a corrected full "
                        "JSON object only. Validation error:\n"
                        f"{validation_error}{compact_instruction}"
                    ),
                }
            )

        payload: dict[str, Any] = {
            "model": self.settings.k_exaone_endpoint_id,
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "max_tokens": MAX_RESPONSE_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False},
            "parse_reasoning": True,
            "include_reasoning": False,
        }

        if include_response_format:
            schema = self._inline_schema_references(
                CircuitGenerationResponse.model_json_schema(by_alias=True)
            )
            schema = self._use_code_lines_schema(schema)
            schema = self._remove_server_derived_connection_fields(schema)
            schema["properties"].pop("assemblyPlan", None)
            schema["required"] = [
                item
                for item in schema.get("required", [])
                if item != "assemblyPlan"
            ]
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"schema": schema},
            }

        return payload

    @staticmethod
    def _use_code_lines_schema(schema: dict[str, Any]) -> dict[str, Any]:
        properties = schema.get("properties", {})
        properties.pop("code", None)
        properties["codeLines"] = {
            "title": "Arduino source code lines",
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 40,
        }

        required = schema.get("required", [])
        schema["required"] = [
            "codeLines" if item == "code" else item for item in required
        ]
        return schema

    @staticmethod
    def _remove_server_derived_connection_fields(
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        connection_schema = schema["properties"]["circuit"]["properties"][
            "connections"
        ]["items"]
        derived_fields = {
            "sourceConnector",
            "targetConnector",
            "wireType",
        }

        for field_name in derived_fields:
            connection_schema["properties"].pop(field_name, None)
        connection_schema["required"] = [
            field_name
            for field_name in connection_schema.get("required", [])
            if field_name not in derived_fields
        ]
        return schema

    @staticmethod
    def _prepare_circuit_data(circuit_data: dict[str, Any]) -> dict[str, Any]:
        code_lines = circuit_data.pop("codeLines", None)
        if code_lines is not None:
            if not isinstance(code_lines, list) or not all(
                isinstance(line, str) for line in code_lines
            ):
                raise TypeError("codeLines must be an array of strings.")
            circuit_data["code"] = "\n".join(code_lines)
        return circuit_data

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
