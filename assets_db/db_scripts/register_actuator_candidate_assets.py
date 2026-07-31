"""Register actuator candidate GLBs and their canonical pin catalogs."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "assets_db"
GLB_ROOT = ASSET_ROOT / "3d_models" / "glb"
METADATA_ROOT = ASSET_ROOT / "3d_models" / "component_metadata" / "candidates"
MANIFEST_PATH = ASSET_ROOT / "3d_models" / "glb_model_manifest.json"
PIN_CATALOG_PATHS = (
    ASSET_ROOT / "db_scripts" / "all_component_pin_coordinates.json",
    REPO_ROOT / "frontend" / "src" / "assets" / "all_component_pin_coordinates.json",
)

ACTUATOR_SLUGS = (
    "active-buzzor",
    "passive-buzzor",
    "dc-motor",
    "l298n",
    "servo-sg90",
)

RUNTIME_BOUNDS = {
    "active-buzzor": {
        "min": [-0.280606598, -0.497127682, -0.280497104],
        "max": [0.280690908, 0.501585543, 0.280510575],
        "size": [0.561297506, 0.998713225, 0.561007679],
    },
    "passive-buzzor": {
        "min": [-0.280606598, -0.497127682, -0.280497104],
        "max": [0.280690908, 0.501585543, 0.280510575],
        "size": [0.561297506, 0.998713225, 0.561007679],
    },
    "dc-motor": {
        "min": [-0.112181403, -0.397362322, -0.500538409],
        "max": [0.114061303, 0.396373808, 0.500390708],
        "size": [0.226242706, 0.79373613, 1.000929117],
    },
    "l298n": {
        "min": [-0.501513422, -0.251632899, -0.500722528],
        "max": [0.501825273, 0.250872403, 0.502003491],
        "size": [1.003338695, 0.502505302, 1.002726019],
    },
    "servo-sg90": {
        "min": [-0.500648379, -0.250052303, -0.360089451],
        "max": [0.500145495, 0.25079459, 0.358300567],
        "size": [1.000793874, 0.500846893, 0.718390018],
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_glb_json(path: Path) -> tuple[int, dict[str, Any], bytes]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise ValueError(f"Invalid GLB: {path}")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise ValueError(f"Missing JSON chunk: {path}")
    document = json.loads(data[20 : 20 + json_length].decode("utf-8").rstrip(" \x00"))
    return version, document, data


def catalog_pin(
    pin_key: str,
    label: str,
    signal_type: str,
    x_px: int,
    y_px: int,
    aliases: list[str],
    sort_order: int,
) -> dict[str, Any]:
    return {
        "pin_key": pin_key,
        "label": label,
        "signal_type": signal_type,
        "side": "bottom",
        "x_px": x_px,
        "y_px": y_px,
        "aliases": aliases,
        "sort_order": sort_order,
    }


def candidate_catalog_entries() -> dict[str, dict[str, Any]]:
    shared = {
        "board_family": None,
        "grid_width": 2,
        "grid_height": 2,
        "pixel_width": 1000,
        "pixel_height": 1000,
        "license_status": "candidate",
        "trademark_notes": None,
        "image": {
            "path": None,
            "mime_type": None,
            "width_px": 1000,
            "height_px": 1000,
            "coordinate_origin": "top-left",
            "background": "unknown",
        },
    }
    return {
        "active-buzzor": {
            "component_slug": "active-buzzor",
            "display_name": "Active Buzzer",
            "category": "output",
            "description": "Candidate active buzzer pin catalog for 3D metadata validation.",
            **shared,
            "pins": [
                catalog_pin("NEGATIVE", "-", "ground", 350, 900, ["GND", "-"], 0),
                catalog_pin("POSITIVE", "+", "power", 650, 900, ["VCC", "+", "S"], 1),
            ],
            "notes": ["The project currently preserves the uploaded filename spelling: buzzor."],
        },
        "passive-buzzor": {
            "component_slug": "passive-buzzor",
            "display_name": "Passive Buzzer",
            "category": "output",
            "description": "Candidate passive buzzer pin catalog for 3D metadata validation.",
            **shared,
            "pins": [
                catalog_pin("NEGATIVE", "-", "ground", 350, 900, ["GND", "-"], 0),
                catalog_pin("POSITIVE", "+", "power", 650, 900, ["VCC", "+", "S"], 1),
            ],
            "notes": ["The project currently preserves the uploaded filename spelling: buzzor."],
        },
        "dc-motor": {
            "component_slug": "dc-motor",
            "display_name": "DC Motor",
            "category": "actuator",
            "description": "Candidate two-terminal DC motor pin catalog for 3D metadata validation.",
            **shared,
            "pins": [
                catalog_pin("NEGATIVE", "M-", "motor", 400, 900, ["-", "black"], 0),
                catalog_pin("POSITIVE", "M+", "motor", 600, 900, ["+", "red"], 1),
            ],
            "notes": ["Use through a motor driver; do not connect a motor directly to a GPIO pin."],
        },
    }


def update_pin_catalogs() -> None:
    entries = candidate_catalog_entries()
    for path in PIN_CATALOG_PATHS:
        catalog = read_json(path)
        catalog.update(entries)
        write_json(path, catalog)


def manifest_row(slug: str) -> dict[str, Any]:
    glb_path = GLB_ROOT / f"{slug}.glb"
    version, document, data = read_glb_json(glb_path)
    return {
        "component_slug": slug,
        "target": glb_path.name,
        "source": glb_path.name,
        "audit_status": "needs_review",
        "model_kind": "candidate_3d",
        "notes": (
            "Uncalibrated candidate optimized to 1K textures and a reduced mesh; "
            "verify physical scale, source license, and measurements before approval."
        ),
        "storage_path": f"3d_models/glb/{glb_path.name}",
        "mime_type": "model/gltf-binary",
        "format": "glb",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "version": version,
        "nodes": len(document.get("nodes", [])),
        "meshes": len(document.get("meshes", [])),
        "materials": len(document.get("materials", [])),
        "textures": len(document.get("textures", [])),
        "images": len(document.get("images", [])),
        "extensions_used": document.get("extensionsUsed", []),
        "bounds": RUNTIME_BOUNDS[slug],
        "unit": "model-unit",
    }


def update_manifest_and_metadata_hashes() -> None:
    manifest = read_json(MANIFEST_PATH)
    indexes = {row["component_slug"]: index for index, row in enumerate(manifest)}
    for slug in ACTUATOR_SLUGS:
        row = manifest_row(slug)
        if slug in indexes:
            manifest[indexes[slug]] = row
        else:
            manifest.append(row)

        metadata_path = METADATA_ROOT / slug / "metadata.json"
        metadata = read_json(metadata_path)
        metadata["asset"]["sha256"] = row["sha256"]
        optimization_note = (
            "GLB texture resolution and mesh density were reduced for web delivery; "
            "the asset remains an uncalibrated candidate."
        )
        notes = metadata.setdefault("notes", [])
        if optimization_note not in notes:
            notes.append(optimization_note)
        write_json(metadata_path, metadata)

    write_json(MANIFEST_PATH, manifest)


if __name__ == "__main__":
    update_pin_catalogs()
    update_manifest_and_metadata_hashes()
    print("Registered actuator candidate catalogs, GLBs, and metadata hashes.")
