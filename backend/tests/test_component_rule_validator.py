import unittest

from pydantic import ValidationError

from app.schemas.circuit import CircuitGenerationResponse
from app.services.asset_metadata import (
    load_breadboard_geometry,
    load_component_footprint,
)
from app.services.component_rules import (
    load_component_rules,
    supported_component_pins,
)
from app.services.physical_assembly import (
    BreadboardAllocator,
    PhysicalAssemblyPlanEngine,
)
from test_assembly_plan import circuit_fixture, part, wire


BOARD = part("uno", "arduino-uno-r3", 0, 260)


def build_plan(name, parts, connections):
    response = CircuitGenerationResponse.model_validate(
        circuit_fixture(name, parts, connections)
    )
    return response, PhysicalAssemblyPlanEngine().build(response)


class ComponentRuleCatalogTest(unittest.TestCase):
    def test_catalog_supports_integrated_component_pack(self):
        rules = load_component_rules()
        expected = {
            "arduino-uno-r3",
            "arduino-nano",
            "hc-sr04",
            "led-5mm-blue",
            "led-5mm-red",
            "led-rgb-5mm",
            "resistor-220-ohm",
            "pushbutton-6x6",
            "potentiometer-10k",
            "slide-switch-spdt",
            "servo-sg90",
        }
        self.assertTrue(expected <= set(rules))
        self.assertEqual(
            supported_component_pins()["led-rgb-5mm"],
            {"RED", "COMMON_CATHODE", "GREEN", "BLUE"},
        )

    def test_component_key_enum_is_exposed_to_structured_output_schema(self):
        schema = CircuitGenerationResponse.model_json_schema(by_alias=True)
        component_key = schema["$defs"]["CircuitPart"]["properties"][
            "componentKey"
        ]
        self.assertIn("potentiometer-10k", component_key["enum"])
        self.assertIn("servo-sg90", component_key["enum"])

    def test_unknown_component_is_rejected(self):
        fixture = circuit_fixture(
            "unknown",
            [part("unknown", "not-in-catalog", 0)],
            [],
        )
        with self.assertRaisesRegex(ValidationError, "Unsupported componentKey"):
            CircuitGenerationResponse.model_validate(fixture)

    def test_connector_gender_is_derived_from_component_rules(self):
        nano = part("nano", "arduino-nano", 0, 200)
        servo = part("servo", "servo-sg90", 300, 160)
        response, _ = build_plan("servo", [nano, servo], [
            wire("w1", "nano", "D3", "servo", "SIGNAL"),
            wire("w2", "nano", "5V", "servo", "VCC"),
            wire("w3", "nano", "GND_1", "servo", "GND"),
        ])
        signal = response.circuit.connections[0]
        self.assertEqual(signal.source_connector, "female")
        self.assertEqual(signal.target_connector, "male")
        self.assertEqual(signal.wire_type, "female-male")


class MetadataPlacementTest(unittest.TestCase):
    def test_all_breadboard_components_have_loadable_footprints(self):
        slugs = {
            "hc-sr04",
            "led-5mm-blue",
            "led-5mm-red",
            "led-rgb-5mm",
            "resistor-220-ohm",
            "pushbutton-6x6",
            "potentiometer-10k",
            "slide-switch-spdt",
        }
        for slug in slugs:
            with self.subTest(slug=slug):
                self.assertEqual(load_component_footprint(slug).asset_slug, slug)

    def test_pushbutton_uses_two_dimensional_pin_coordinates(self):
        allocator = BreadboardAllocator(load_breadboard_geometry())
        placement = allocator.allocate(
            "button",
            load_component_footprint("pushbutton-6x6"),
        )
        self.assertIsNotNone(placement)
        addresses = placement.addresses
        self.assertEqual(len(set(addresses.values())), 4)
        self.assertEqual(addresses["A1"][1:], addresses["A2"][1:])
        self.assertEqual(addresses["B1"][1:], addresses["B2"][1:])
        self.assertNotEqual(addresses["A1"][0], addresses["A2"][0])


class ElectricalRuleTest(unittest.TestCase):
    def test_red_led_with_series_resistor_is_valid(self):
        led = part("led", "led-5mm-red", 360)
        resistor = part("resistor", "resistor-220-ohm", 520)
        _, plan = build_plan("red led", [BOARD, led, resistor], [
            wire("w1", "uno", "D3", "resistor", "LEAD_A"),
            wire("w2", "resistor", "LEAD_B", "led", "ANODE"),
            wire("w3", "led", "CATHODE", "uno", "GND_P1"),
        ])
        codes = {item.code for item in plan.warnings}
        self.assertNotIn("LED_REVERSED", codes)
        self.assertNotIn("LED_RESISTOR_MISSING", codes)
        self.assertIn("ASSEMBLY_VALID", codes)

    def test_rgb_led_requires_a_resistor_for_each_used_channel(self):
        led = part("rgb", "led-rgb-5mm", 360)
        resistor = part("resistor", "resistor-220-ohm", 520)
        _, plan = build_plan("rgb led", [BOARD, led, resistor], [
            wire("w1", "uno", "D3", "resistor", "LEAD_A"),
            wire("w2", "resistor", "LEAD_B", "rgb", "RED"),
            wire("w3", "uno", "D5", "rgb", "GREEN"),
            wire("w4", "rgb", "COMMON_CATHODE", "uno", "GND_P1"),
        ])
        missing = [
            item for item in plan.warnings
            if item.code == "LED_RESISTOR_MISSING"
        ]
        self.assertEqual([item.details["pin"] for item in missing], ["GREEN"])

    def test_potentiometer_requires_analog_wiper_and_power_terminals(self):
        pot = part("pot", "potentiometer-10k", 360)
        _, valid_plan = build_plan("pot valid", [BOARD, pot], [
            wire("w1", "uno", "5V", "pot", "CCW"),
            wire("w2", "uno", "A0", "pot", "WIPER"),
            wire("w3", "uno", "GND_P1", "pot", "CW"),
        ])
        valid_codes = {item.code for item in valid_plan.warnings}
        self.assertNotIn("PIN_CAPABILITY_MISMATCH", valid_codes)
        self.assertNotIn("POTENTIOMETER_TERMINAL_ROLE", valid_codes)

        _, invalid_plan = build_plan("pot invalid", [BOARD, pot], [
            wire("w1", "uno", "5V", "pot", "CCW"),
            wire("w2", "uno", "D2", "pot", "WIPER"),
            wire("w3", "uno", "GND_P1", "pot", "CW"),
        ])
        mismatch = next(
            item for item in invalid_plan.warnings
            if item.code == "PIN_CAPABILITY_MISMATCH"
        )
        self.assertEqual(mismatch.details["pin"], "WIPER")

    def test_servo_accepts_digital_signal_but_recommends_pwm_and_external_power(self):
        servo = part("servo", "servo-sg90", 360)
        _, plan = build_plan("servo", [BOARD, servo], [
            wire("w1", "uno", "D2", "servo", "SIGNAL"),
            wire("w2", "uno", "5V", "servo", "VCC"),
            wire("w3", "uno", "GND_P1", "servo", "GND"),
        ])
        codes = {item.code for item in plan.warnings}
        self.assertNotIn("PIN_CAPABILITY_MISMATCH", codes)
        self.assertIn("PIN_CAPABILITY_PREFERRED", codes)
        self.assertIn("EXTERNAL_POWER_RECOMMENDED", codes)


if __name__ == "__main__":
    unittest.main()
