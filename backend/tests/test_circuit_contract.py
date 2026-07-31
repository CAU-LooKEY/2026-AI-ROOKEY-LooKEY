import json
import unittest

from app.services.circuit_contract import (
    CircuitContractError,
    normalize_circuit_contract,
)
from tests.test_k_exaone import SAMPLE_CIRCUIT


def clone_sample() -> dict:
    return json.loads(json.dumps(SAMPLE_CIRCUIT))


class CircuitContractTest(unittest.TestCase):
    def test_assigns_deterministic_canonical_part_ids(self):
        first = normalize_circuit_contract(clone_sample())
        second = normalize_circuit_contract(clone_sample())
        repeated = normalize_circuit_contract(first)

        self.assertEqual(first, second)
        self.assertEqual(first, repeated)
        self.assertEqual(
            [part["id"] for part in first["circuit"]["parts"]],
            [
                "arduino-uno-r3-1",
                "led-5mm-blue-1",
                "resistor-220-ohm-1",
            ],
        )
        self.assertEqual(
            first["circuit"]["connections"][0]["source"],
            "arduino-uno-r3-1",
        )
        self.assertEqual(
            first["circuit"]["connections"][0]["target"],
            "led-5mm-blue-1",
        )

    def test_disambiguates_duplicate_model_ids_with_pin_contracts(self):
        document = clone_sample()
        document["circuit"]["parts"][0]["id"] = "part"
        document["circuit"]["parts"][1]["id"] = "part"
        document["circuit"]["connections"][0]["source"] = "part"
        document["circuit"]["connections"][0]["target"] = "part"
        document["circuit"]["connections"][1]["source"] = "part"

        normalized = normalize_circuit_contract(document)

        first_connection = normalized["circuit"]["connections"][0]
        second_connection = normalized["circuit"]["connections"][1]
        self.assertEqual(first_connection["source"], "arduino-uno-r3-1")
        self.assertEqual(first_connection["target"], "led-5mm-blue-1")
        self.assertEqual(second_connection["source"], "led-5mm-blue-1")

    def test_reports_unknown_part_with_connection_and_bad_id(self):
        document = clone_sample()
        document["circuit"]["connections"][0]["source"] = "missing-board"

        with self.assertRaisesRegex(
            CircuitContractError,
            r"Connection 'e1' source references unknown part id "
            r"'missing-board'",
        ):
            normalize_circuit_contract(document)

    def test_reports_invalid_pin_with_connection_part_and_allowed_pins(self):
        document = clone_sample()
        document["circuit"]["connections"][0]["sourcePin"] = "D99"

        with self.assertRaisesRegex(
            CircuitContractError,
            r"Connection 'e1' source pin 'D99'.*arduino-uno-r3-1"
            r".*Allowed pins:",
        ):
            normalize_circuit_contract(document)

    def test_repairs_pin_case_and_separator_variants(self):
        document = clone_sample()
        document["circuit"]["connections"][1]["targetPin"] = "lead-a"

        normalized = normalize_circuit_contract(document)

        self.assertEqual(
            normalized["circuit"]["connections"][1]["targetPin"],
            "LEAD_A",
        )

    def test_repairs_swapped_part_id_and_pin_fields(self):
        document = clone_sample()
        connection = document["circuit"]["connections"][0]
        connection["source"] = "D3"
        connection["sourcePin"] = "arduino"

        normalized = normalize_circuit_contract(document)
        repaired = normalized["circuit"]["connections"][0]

        self.assertEqual(repaired["source"], "arduino-uno-r3-1")
        self.assertEqual(repaired["sourcePin"], "D3")


if __name__ == "__main__":
    unittest.main()
