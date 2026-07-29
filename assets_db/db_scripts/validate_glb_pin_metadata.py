"""Validate GLB pin nodes against component 3D metadata.

Run with Blender:
  blender --background --python validate_glb_pin_metadata.py -- metadata.json

The metadata stores glTF runtime coordinates (+Y up). Blender imports those as
(X, -Z, Y), so comparisons are performed after that deterministic conversion.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
POSITION_TOLERANCE_M = 0.00001
DIMENSION_TOLERANCE_M = 0.00002


def arguments() -> Path:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    if len(argv) != 1:
        raise SystemExit("Expected one component metadata JSON path")
    return Path(argv[0]).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gltf_to_blender(position: list[float]) -> Vector:
    return Vector((position[0], -position[2], position[1]))


def mesh_bounds() -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points:
        raise RuntimeError("GLB contains no mesh geometry")
    return (
        Vector(min(point[i] for point in points) for i in range(3)),
        Vector(max(point[i] for point in points) for i in range(3)),
    )


def main() -> None:
    metadata_path = arguments()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_path = REPO_ROOT / metadata["asset"]["path"]
    errors: list[str] = []

    actual_hash = sha256(model_path)
    if actual_hash != metadata["asset"]["sha256"]:
        errors.append(
            f"SHA256 mismatch: metadata={metadata['asset']['sha256']} actual={actual_hash}"
        )

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(model_path))

    glb_pin_nodes = {
        obj.name: obj
        for obj in bpy.context.scene.objects
        if obj.name.lower().startswith("pin_")
    }
    metadata_node_names = {pin["nodeName"] for pin in metadata["pins"]}

    missing = sorted(metadata_node_names - glb_pin_nodes.keys())
    extra = sorted(glb_pin_nodes.keys() - metadata_node_names)
    if missing:
        errors.append("Missing GLB pin nodes: " + ", ".join(missing))
    if extra:
        errors.append("Unexpected GLB pin nodes: " + ", ".join(extra))

    max_position_error = 0.0
    for pin in metadata["pins"]:
        node = glb_pin_nodes.get(pin["nodeName"])
        if node is None:
            continue
        expected = gltf_to_blender(pin["position"])
        actual = node.matrix_world.translation
        distance = (actual - expected).length
        max_position_error = max(max_position_error, distance)
        if distance > POSITION_TOLERANCE_M:
            errors.append(
                f"{pin['pinKey']} position differs by {distance * 1000:.6f} mm "
                f"(expected {tuple(expected)}, actual {tuple(actual)})"
            )

    root_name = metadata["componentSlug"].replace("-", "_").upper() + "_ROOT"
    root = bpy.data.objects.get(root_name)
    if root is None:
        errors.append(f"Missing normalized root node: {root_name}")
    else:
        if root.parent is not None:
            errors.append(f"{root_name} must not have a parent")
        if root.location.length > POSITION_TOLERANCE_M:
            errors.append(f"{root_name} location is not zero")
        if any(abs(angle) > 1e-6 for angle in root.rotation_euler):
            errors.append(f"{root_name} rotation is not zero")
        if any(abs(value - 1) > 1e-6 for value in root.scale):
            errors.append(f"{root_name} scale is not one")

    minimum, maximum = mesh_bounds()
    size = maximum - minimum
    expected_width = metadata["physicalDimensions"]["width"] / 1000
    expected_depth = metadata["physicalDimensions"]["depth"] / 1000
    if abs(size.x - expected_width) > DIMENSION_TOLERANCE_M:
        errors.append(
            f"Width mismatch: expected {expected_width} m, measured {size.x} m"
        )
    if abs(size.y - expected_depth) > DIMENSION_TOLERANCE_M:
        errors.append(
            f"Depth mismatch: expected {expected_depth} m, measured {size.y} m"
        )

    report = {
        "component": metadata["componentSlug"],
        "model": str(model_path),
        "pinNodeCount": len(glb_pin_nodes),
        "metadataPinCount": len(metadata["pins"]),
        "maximumPinPositionErrorMillimeter": max_position_error * 1000,
        "meshSizeMillimeter": [size.x * 1000, size.y * 1000, size.z * 1000],
        "rootNode": root_name,
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    print("GLB_METADATA_VALIDATION_BEGIN")
    print(json.dumps(report, indent=2))
    print("GLB_METADATA_VALIDATION_END")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
