from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "db_scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_assets import (  # noqa: E402
    CheckResult,
    Finding,
    changed_slugs,
    markdown_report,
    read_glb_nodes,
    report_payload,
    validate_coverage,
    validate_glb_pin_nodes,
    validate_physical_dimensions,
)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_glb(path: Path, nodes: list[dict]) -> None:
    document = json.dumps({"asset": {"version": "2.0"}, "nodes": nodes}).encode()
    padding = b" " * ((4 - len(document) % 4) % 4)
    json_chunk = document + padding
    raw = (
        struct.pack("<4sII", b"glTF", 2, 20 + len(json_chunk))
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


class ChangedAssetPolicyTest(unittest.TestCase):
    def test_changed_glb_and_metadata_paths_resolve_to_slugs(self):
        manifest = [{
            "component_slug": "servo-sg90",
            "storage_path": "3d_models/glb/servo-sg90.glb",
        }]
        paths = [
            "assets_db/3d_models/glb/servo-sg90.glb",
            "assets_db/3d_models/component_metadata/candidates/hc-sr04/user.json",
            "assets_db/3d_models/component_metadata/approved/led-5mm-red.json",
        ]
        self.assertEqual(
            changed_slugs(paths, manifest),
            {"servo-sg90", "hc-sr04", "led-5mm-red"},
        )

    def test_changed_glb_without_metadata_fails_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_glb(
                root / "assets_db/3d_models/glb/new-sensor.glb",
                [{"name": "pin_SIGNAL", "translation": [0, 0, 0]}],
            )
            write_json(
                root / "assets_db/3d_models/glb_model_manifest.json",
                [{
                    "component_slug": "new-sensor",
                    "storage_path": "3d_models/glb/new-sensor.glb",
                }],
            )
            result = validate_coverage(
                "pr",
                ["assets_db/3d_models/glb/new-sensor.glb"],
                root,
            )
            self.assertEqual(result.status, "failed")
            self.assertIn("METADATA_REQUIRED", {item.code for item in result.findings})

    def test_candidate_allows_pr_but_not_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_glb(root / "assets_db/3d_models/glb/new-sensor.glb", [])
            write_json(
                root / "assets_db/3d_models/glb_model_manifest.json",
                [{
                    "component_slug": "new-sensor",
                    "storage_path": "3d_models/glb/new-sensor.glb",
                }],
            )
            write_json(
                root / (
                    "assets_db/3d_models/component_metadata/"
                    "candidates/new-sensor/test.json"
                ),
                {"componentSlug": "new-sensor"},
            )
            changed = ["assets_db/3d_models/glb/new-sensor.glb"]
            self.assertEqual(validate_coverage("pr", changed, root).status, "passed")
            release = validate_coverage("release", [], root)
            self.assertEqual(release.status, "failed")
            self.assertIn(
                "APPROVED_METADATA_REQUIRED",
                {item.code for item in release.findings},
            )


class GlbPinNodeTest(unittest.TestCase):
    def test_glb_reader_returns_embedded_pin_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "part.glb"
            write_glb(path, [{"name": "pin_VCC", "translation": [0.1, 0.2, 0.3]}])
            self.assertEqual(read_glb_nodes(path)["pin_VCC"], [0.1, 0.2, 0.3])

    def test_pin_position_mismatch_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            glb_path = root / "assets_db/3d_models/glb/part.glb"
            write_glb(
                glb_path,
                [{"name": "pin_VCC", "translation": [0.001, 0.002, 0.003]}],
            )
            write_json(
                root / (
                    "assets_db/3d_models/component_metadata/"
                    "candidates/part/test.json"
                ),
                {
                    "componentSlug": "part",
                    "asset": {"path": "assets_db/3d_models/glb/part.glb"},
                    "pins": [{
                        "pinKey": "VCC",
                        "nodeName": "pin_VCC",
                        "position": [0.001, 0.002, 0.02],
                    }],
                },
            )
            result = validate_glb_pin_nodes(root)
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.findings[0].code, "PIN_POSITION_MISMATCH")


class PhysicalDimensionsTest(unittest.TestCase):
    def test_body_only_dimensions_are_not_compared_with_overall_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "assets_db/3d_models/glb_model_manifest.json",
                [{
                    "component_slug": "part",
                    "bounds": {"size": [0.01, 0.05, 0.02]},
                }],
            )
            write_json(
                root / (
                    "assets_db/3d_models/component_metadata/"
                    "candidates/part/test.json"
                ),
                {
                    "componentSlug": "part",
                    "asset": {"scaleStatus": "real-world"},
                    "coordinateSystems": {"runtime": {"unit": "meter"}},
                    "physicalDimensions": {
                        "unit": "millimeter",
                        "width": 10,
                        "depth": 20,
                        "height": 5,
                        "measurementScope": "body-only",
                    },
                },
            )
            result = validate_physical_dimensions(root)
            self.assertEqual(result.status, "passed")

    def test_real_world_dimension_mismatch_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "assets_db/3d_models/glb_model_manifest.json",
                [{
                    "component_slug": "part",
                    "bounds": {"size": [0.01, 0.005, 0.02]},
                }],
            )
            write_json(
                root / (
                    "assets_db/3d_models/component_metadata/"
                    "candidates/part/test.json"
                ),
                {
                    "componentSlug": "part",
                    "asset": {"scaleStatus": "real-world"},
                    "coordinateSystems": {"runtime": {"unit": "meter"}},
                    "physicalDimensions": {
                        "unit": "millimeter",
                        "width": 99,
                        "depth": 20,
                        "height": 5,
                    },
                },
            )
            result = validate_physical_dimensions(root)
            self.assertEqual(result.status, "failed")
            self.assertEqual(
                {item.code for item in result.findings},
                {"PHYSICAL_DIMENSION_MISMATCH"},
            )


class ReportTest(unittest.TestCase):
    def test_json_and_markdown_summarize_findings(self):
        results = [
            CheckResult("ok", "정상 검사", "passed", 0.1),
            CheckResult(
                "bad",
                "오류 검사",
                "failed",
                0.2,
                findings=[Finding("error", "BROKEN_ASSET", "고쳐야 합니다.", "part")],
            ),
        ]
        payload = report_payload("pr", ["part.glb"], results)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["summary"]["errors"], 1)
        markdown = markdown_report(payload)
        self.assertIn("BROKEN_ASSET", markdown)
        self.assertIn("고쳐야 합니다.", markdown)


if __name__ == "__main__":
    unittest.main()
