"""Print machine-readable component state from a GLB imported by Blender."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


glb_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(glb_path))

mesh_points = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    mesh_points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)

minimum = [min(point[index] for point in mesh_points) for index in range(3)]
maximum = [max(point[index] for point in mesh_points) for index in range(3)]

pins = []
for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name):
    if not obj.name.startswith("pin_"):
        continue
    location = obj.matrix_world.translation
    pins.append(
        {
            "nodeName": obj.name,
            "blenderPosition": [round(value, 9) for value in location],
            "gltfPosition": [
                round(location.x, 9),
                round(location.z, 9),
                round(-location.y, 9),
            ],
        }
    )

roots = []
for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name):
    if not obj.name.endswith("_ROOT"):
        continue
    roots.append(
        {
            "name": obj.name,
            "location": [round(value, 9) for value in obj.location],
            "rotationQuaternion": [
                round(value, 9) for value in obj.rotation_quaternion
            ],
            "scale": [round(value, 9) for value in obj.scale],
        }
    )

print(
    "COMPONENT_STATE "
    + json.dumps(
        {
            "glb": str(glb_path),
            "bounds": {
                "minimum": [round(value, 9) for value in minimum],
                "maximum": [round(value, 9) for value in maximum],
                "size": [
                    round(maximum[index] - minimum[index], 9)
                    for index in range(3)
                ],
            },
            "roots": roots,
            "pins": pins,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
)
