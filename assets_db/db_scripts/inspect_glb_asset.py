"""Inspect a GLB with Blender and print deterministic geometry diagnostics.

Usage:
  blender --background --python inspect_glb_asset.py -- path/to/model.glb
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args():
    if "--" not in sys.argv:
        raise SystemExit("Pass a GLB path after --")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 1:
        raise SystemExit("Expected exactly one GLB path")
    return Path(args[0]).resolve()


def world_bounds(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise SystemExit("Imported GLB contains no mesh geometry")

    minimum = Vector(min(point[index] for point in points) for index in range(3))
    maximum = Vector(max(point[index] for point in points) for index in range(3))
    return minimum, maximum


glb_path = cli_args()
if not glb_path.exists():
    raise SystemExit(f"GLB not found: {glb_path}")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(glb_path))

objects = sorted(bpy.context.scene.objects, key=lambda obj: obj.name.lower())
minimum, maximum = world_bounds(objects)
size = maximum - minimum

result = {
    "file": glb_path.name,
    "bytes": glb_path.stat().st_size,
    "bounds": {
        "min": [round(value, 9) for value in minimum],
        "max": [round(value, 9) for value in maximum],
        "size": [round(value, 9) for value in size],
    },
    "objectCount": len(objects),
    "meshCount": sum(obj.type == "MESH" for obj in objects),
    "emptyCount": sum(obj.type == "EMPTY" for obj in objects),
    "pinNodeCount": sum(obj.name.lower().startswith("pin_") for obj in objects),
    "objects": [
        {
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "location": [round(value, 9) for value in obj.location],
            "rotationEuler": [round(value, 9) for value in obj.rotation_euler],
            "scale": [round(value, 9) for value in obj.scale],
        }
        for obj in objects
    ],
}

print("ASSET_INSPECTION_JSON_BEGIN")
print(json.dumps(result, ensure_ascii=False, indent=2))
print("ASSET_INSPECTION_JSON_END")
