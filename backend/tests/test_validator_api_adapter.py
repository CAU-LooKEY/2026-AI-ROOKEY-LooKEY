import copy
import unittest

from app.schemas.circuit import CircuitGenerationResponse
from app.services.intent_templates import generate_intent_template
from app.validator.adapter import (
    convert_api_response_to_validator_json,
    extract_used_pins_from_code,
)
from app.validator.rules import validate_and_attach, validate_circuit


def current_api_payload():
    response = generate_intent_template("손을 가까이 대면 LED가 켜지게 해줘")
    assert response is not None
    return response.model_dump(by_alias=True)


class ValidatorApiAdapterTest(unittest.TestCase):
    def test_converts_current_api_parts_and_connections(self):
        converted = convert_api_response_to_validator_json(current_api_payload())

        self.assertEqual(len(converted["nodes"]), 4)
        self.assertEqual(len(converted["edges"]), 7)
        self.assertEqual(converted["nodes"][0]["componentKey"], "arduino-uno-r3")
        self.assertEqual(converted["edges"][0]["sourceHandle"], "5V")

    def test_uses_code_meta_before_source_code_parsing(self):
        converted = convert_api_response_to_validator_json(current_api_payload())

        self.assertEqual(
            extract_used_pins_from_code(converted),
            ["5V", "D3", "D7", "D8", "GND"],
        )

    def test_valid_current_api_response_passes_validator(self):
        results = validate_circuit(current_api_payload())

        self.assertEqual(results[0]["rule"], "PASS")

    def test_attached_results_match_api_response_contract(self):
        attached = validate_and_attach(current_api_payload())

        self.assertEqual(attached["validationResults"][0]["ruleId"], "PASS")
        CircuitGenerationResponse.model_validate(attached)

    def test_reports_code_and_hardware_pin_mismatch(self):
        payload = current_api_payload()
        payload["codeMeta"]["used_pins"] = ["D9"]

        results = validate_circuit(payload)

        mismatch = next(result for result in results if result["rule"] == "R011")
        self.assertEqual(mismatch["target"]["code_pin"], "D9")

    def test_reports_short_circuit_in_current_api_shape(self):
        payload = copy.deepcopy(current_api_payload())
        payload["circuit"]["connections"][0]["targetPin"] = "GND"

        results = validate_circuit(payload)

        self.assertIn("R004", {result["rule"] for result in results})


if __name__ == "__main__":
    unittest.main()
