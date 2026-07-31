import unittest

from app.schemas.circuit import CircuitGenerationResponse
from app.services.assembly_plan import (
    AssemblyPlanEngine,
    generate_leg_candidates,
    parse_address,
)


def circuit_fixture(name, parts, connections):
    return {
        "title": name,
        "intent": name,
        "difficulty": "초급",
        "estimatedTime": "10분",
        "components": [
            {"id": part["id"], "name": part["label"], "quantity": 1, "role": "테스트"}
            for part in parts
        ],
        "circuit": {"parts": parts, "connections": connections},
        "code": "void setup() {}\nvoid loop() {}",
        "codeMeta": {"used_pins": []},
        "tutorSteps": [],
        "warnings": [],
        "validationResults": [],
        "unsupportedComponents": [],
    }


def part(identifier, slug, x, width=120):
    return {"id": identifier, "label": identifier, "componentKey": slug,
            "position": {"x": x, "y": 100}, "width": width}


def wire(identifier, source, source_pin, target, target_pin):
    return {"id": identifier, "source": source, "sourcePin": source_pin,
            "target": target, "targetPin": target_pin, "label": identifier,
            "color": "#000000"}


BOARD = part("uno", "arduino-uno-r3", 0, 260)
LED = part("led", "led-5mm-blue", 380)
RESISTOR = part("resistor", "resistor-220-ohm", 560)
SENSOR = part("sensor", "hc-sr04", 400, 180)

FIVE_REPRESENTATIVE_CIRCUITS = {
    "led_with_resistor": circuit_fixture("정상 LED", [BOARD, LED, RESISTOR], [
        wire("w1", "uno", "D3", "resistor", "LEAD_A"),
        wire("w2", "resistor", "LEAD_B", "led", "ANODE"),
        wire("w3", "led", "CATHODE", "uno", "GND_P1"),
    ]),
    "ultrasonic_sensor": circuit_fixture("초음파 센서", [BOARD, SENSOR], [
        wire("w1", "uno", "5V", "sensor", "VCC"),
        wire("w2", "uno", "D7", "sensor", "TRIG"),
        wire("w3", "sensor", "ECHO", "uno", "D8"),
        wire("w4", "sensor", "GND", "uno", "GND_P1"),
    ]),
    "reversed_led": circuit_fixture("역극성 LED", [BOARD, LED, RESISTOR], [
        wire("w1", "uno", "GND_P1", "led", "ANODE"),
        wire("w2", "led", "CATHODE", "resistor", "LEAD_A"),
        wire("w3", "resistor", "LEAD_B", "uno", "D3"),
    ]),
    "led_without_resistor": circuit_fixture("저항 없는 LED", [BOARD, LED], [
        wire("w1", "uno", "D3", "led", "ANODE"),
        wire("w2", "led", "CATHODE", "uno", "GND_P1"),
    ]),
    "power_ground_short": circuit_fixture("전원 단락", [BOARD], [
        wire("w1", "uno", "5V", "uno", "GND_P1"),
    ]),
}


class AddressParserTest(unittest.TestCase):
    def test_board_breadboard_and_rail_addresses(self):
        self.assertEqual(parse_address("A1").electrical_node, "bb:ABCDE:1")
        self.assertEqual(parse_address("E1").electrical_node, "bb:ABCDE:1")
        self.assertEqual(parse_address("F1").electrical_node, "bb:FGHIJ:1")
        self.assertEqual(parse_address("J30").canonical, "J30")
        self.assertEqual(parse_address("L+1").electrical_node,
                         parse_address("L+30").electrical_node)
        self.assertEqual(parse_address("GND_P1").electrical_node, "board:GND")
        self.assertEqual(parse_address("BOARD:A1").electrical_node, "board:A1")

    def test_invalid_addresses_are_rejected(self):
        for address in ("B0", "J31", "K1", "D31", ""):
            with self.subTest(address=address), self.assertRaises(ValueError):
                parse_address(address)

    def test_leg_spacing_candidates(self):
        self.assertEqual(generate_leg_candidates("led-5mm-blue", "A1"),
                         [{"ANODE": "A1", "CATHODE": "A2"}])
        self.assertEqual(generate_leg_candidates("resistor-220-ohm", "J27"),
                         [{"LEAD_A": "J27", "LEAD_B": "J30"}])
        self.assertEqual(generate_leg_candidates("hc-sr04", "A28"), [])


class AssemblyPlanEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = AssemblyPlanEngine()

    def build(self, fixture_name):
        response = CircuitGenerationResponse.model_validate(
            FIVE_REPRESENTATIVE_CIRCUITS[fixture_name]
        )
        return self.engine.build(response)

    def test_five_representative_fixtures_build(self):
        for name in FIVE_REPRESENTATIVE_CIRCUITS:
            with self.subTest(name=name):
                plan = self.build(name)
                self.assertEqual(len(plan.components), len(plan.placements))
                self.assertEqual(plan.schema_version, "1.0")

    def test_same_input_always_produces_same_plan(self):
        first = self.build("led_with_resistor").model_dump_json(by_alias=True)
        second = self.build("led_with_resistor").model_dump_json(by_alias=True)
        self.assertEqual(first, second)

    def test_overlapping_input_positions_are_spaced(self):
        fixture = circuit_fixture("겹침", [
            part("uno", "arduino-uno-r3", 100, 260),
            part("led", "led-5mm-blue", 100, 120),
        ], [wire("w1", "uno", "D3", "led", "ANODE")])
        plan = self.engine.build(CircuitGenerationResponse.model_validate(fixture))
        positions = [(item.transform.position.x, item.transform.position.z)
                     for item in plan.placements]
        self.assertEqual(len(positions), len(set(positions)))

    def test_led_and_sensor_rules(self):
        self.assertNotIn("LED_RESISTOR_MISSING",
                         {item.code for item in self.build("led_with_resistor").warnings})
        self.assertIn("LED_REVERSED",
                      {item.code for item in self.build("reversed_led").warnings})
        self.assertIn("LED_RESISTOR_MISSING",
                      {item.code for item in self.build("led_without_resistor").warnings})
        self.assertNotIn("SENSOR_PIN_ROLE",
                         {item.code for item in self.build("ultrasonic_sensor").warnings})

    def test_power_ground_short_rule(self):
        self.assertIn("POWER_GROUND_SHORT",
                      {item.code for item in self.build("power_ground_short").warnings})


if __name__ == "__main__":
    unittest.main()
