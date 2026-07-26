import unittest
from unittest.mock import patch

from app.schemas.circuit import CircuitGenerationResponse
from app.services.asset_metadata import (
    AssetMetadataError,
    ComponentFootprint,
    load_breadboard_geometry,
    load_component_footprint,
)
from app.services.physical_assembly import (
    BREADBOARD_ID,
    BreadboardAllocator,
    PhysicalAssemblyPlanEngine,
    parse_physical_address,
)
from test_assembly_plan import (
    FIVE_REPRESENTATIVE_CIRCUITS,
    circuit_fixture,
    part,
)


class IntegratedAssetMetadataTest(unittest.TestCase):
    def test_real_breadboard_geometry_uses_254mm_pitch(self):
        geometry = load_breadboard_geometry()
        a1 = geometry.hole_position("A1")
        a2 = geometry.hole_position("A2")
        self.assertAlmostEqual(a2[0] - a1[0], 0.00254)
        self.assertEqual(geometry.columns, 30)

    def test_real_component_pin_pitch_is_loaded(self):
        resistor = load_component_footprint("resistor-220-ohm")
        sensor = load_component_footprint("hc-sr04")
        self.assertEqual(resistor.offsets, (0, 4))
        self.assertEqual(sensor.offsets, (0, 1, 2, 3))
        self.assertTrue(resistor.normalized)

    def test_terminal_banks_and_segmented_rails_are_distinct(self):
        self.assertEqual(
            parse_physical_address("A1").electrical_group,
            parse_physical_address("E1").electrical_group,
        )
        self.assertNotEqual(
            parse_physical_address("E1").electrical_group,
            parse_physical_address("F1").electrical_group,
        )
        self.assertEqual(
            parse_physical_address("T+1").electrical_group,
            parse_physical_address("T+5").electrical_group,
        )
        self.assertNotEqual(
            parse_physical_address("T+5").electrical_group,
            parse_physical_address("T+6").electrical_group,
        )


class PhysicalAssemblyPlanTest(unittest.TestCase):
    def setUp(self):
        self.engine = PhysicalAssemblyPlanEngine()

    def build(self, fixture_name):
        response = CircuitGenerationResponse.model_validate(
            FIVE_REPRESENTATIVE_CIRCUITS[fixture_name]
        )
        return self.engine.build(response)

    def test_all_five_fixtures_receive_real_physical_placements(self):
        for name in FIVE_REPRESENTATIVE_CIRCUITS:
            with self.subTest(name=name):
                plan = self.build(name)
                self.assertIn(BREADBOARD_ID, {item.instance_id for item in plan.components})
                self.assertEqual(len(plan.components), len(plan.placements))
                for placement in plan.placements:
                    if placement.component_id not in {"uno", BREADBOARD_ID}:
                        self.assertEqual(placement.status, "placed")
                        self.assertTrue(placement.addresses)

    def test_connection_endpoints_contain_allocated_hole_addresses(self):
        plan = self.build("led_with_resistor")
        resistor_wire = next(item for item in plan.connections if item.id == "w2")
        self.assertRegex(resistor_wire.source.address, r"^[A-J](?:[1-9]|[12][0-9]|30)$")
        self.assertRegex(resistor_wire.target.address, r"^[A-J](?:[1-9]|[12][0-9]|30)$")
        self.assertEqual(resistor_wire.electrical_node,
                         next(item for item in plan.connections if item.id == "w2").electrical_node)

    def test_same_input_produces_byte_identical_plan(self):
        first = self.build("ultrasonic_sensor").model_dump_json(by_alias=True)
        second = self.build("ultrasonic_sensor").model_dump_json(by_alias=True)
        self.assertEqual(first, second)

    def test_failure_code_is_returned_when_board_has_no_candidate(self):
        parts = [part(f"led-{index:03}", "led-5mm-blue", index * 10) for index in range(80)]
        fixture = circuit_fixture("배치 용량 초과", parts, [])
        plan = self.engine.build(CircuitGenerationResponse.model_validate(fixture))
        failed = [item for item in plan.placements if item.status == "failed"]
        self.assertTrue(failed)
        self.assertTrue(all(item.failure_code == "NO_PLACEMENT_CANDIDATE" for item in failed))
        warning = next(item for item in plan.warnings if item.code == "NO_PLACEMENT_CANDIDATE")
        self.assertEqual(warning.severity, "ERROR")
        self.assertTrue(warning.suggestion)
        self.assertIn("assetSlug", warning.details)

    def test_missing_breadboard_metadata_returns_partial_plan(self):
        response = CircuitGenerationResponse.model_validate(
            FIVE_REPRESENTATIVE_CIRCUITS["led_with_resistor"]
        )
        with patch(
            "app.services.physical_assembly.load_breadboard_geometry",
            side_effect=AssetMetadataError("missing"),
        ):
            plan = self.engine.build(response)
        self.assertIn("BREADBOARD_METADATA_MISSING", {item.code for item in plan.warnings})
        failed = [item for item in plan.placements]
        self.assertTrue(all(item.status == "failed" for item in failed))

    def test_allocator_rejects_impossible_keep_out(self):
        geometry = load_breadboard_geometry()
        allocator = BreadboardAllocator(geometry)
        impossible = ComponentFootprint(
            asset_slug="oversized",
            pins=("A", "B"),
            offsets=(0, 1),
            width_meter=1,
            depth_meter=1,
            keep_out_meter=1,
            normalized=True,
        )
        first = allocator.allocate("first", impossible)
        self.assertIsNone(first)


if __name__ == "__main__":
    unittest.main()
