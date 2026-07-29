"""Normalize the Arduino Nano GLB and add physical header pin anchors.

Run with Blender:
  blender --background --python normalize_arduino_nano.py -- INPUT.glb OUTPUT.glb

Coordinate contract:
  - meters
  - +X: right in top view
  - +Y: toward the ICSP end (USB is -Y)
  - +Z: up
  - model bottom/pin-tip plane: Z = 0
  - root transform: identity
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


WIDTH_M = 0.018
LENGTH_M = 0.045
HEADER_ROW_X_M = 0.01524 / 2
HEADER_PITCH_M = 0.00254
FIRST_PIN_Y_M = 7 * HEADER_PITCH_M
HEADER_INSERTION_DEPTH_M = 0.004

LEFT_PINS = [
    "D12", "D11", "D10", "D9", "D8", "D7", "D6", "D5",
    "D4", "D3", "D2", "GND_2", "RESET_2", "D0", "D1",
]
RIGHT_PINS = [
    "D13", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4",
    "A5", "A6", "A7", "5V", "RESET_1", "GND_1", "VIN",
]


def arguments() -> tuple[Path, Path]:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    if len(argv) != 2:
        raise SystemExit("Expected INPUT.glb OUTPUT.glb")
    return Path(argv[0]).resolve(), Path(argv[1]).resolve()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def mesh_bounds(objects: list[bpy.types.Object]) -> tuple[list[float], list[float]]:
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("Imported GLB contains no mesh geometry")
    return (
        [min(point[i] for point in points) for i in range(3)],
        [max(point[i] for point in points) for i in range(3)],
    )


def add_pin(root: bpy.types.Object, name: str, x: float, y: float) -> dict:
    pin = bpy.data.objects.new(f"pin_{name}", None)
    pin.empty_display_type = "PLAIN_AXES"
    pin.empty_display_size = 0.0015
    # Store the snap anchor at the breadboard surface, not at the sharp pin
    # tip. With a 4 mm insertion depth this plane is 4 mm above the tip.
    pin.location = (x, y, HEADER_INSERTION_DEPTH_M)
    pin.parent = root
    pin["pin_key"] = name
    pin["anchor_role"] = "electrical_terminal"
    pin["coordinate_unit"] = "meter"
    bpy.context.scene.collection.objects.link(pin)
    return {
        "pin_key": name,
        "model_anchor_name": pin.name,
        "position": {"x": x, "y": y, "z": HEADER_INSERTION_DEPTH_M},
    }


def main() -> None:
    input_path, output_path = arguments()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(input_path))
    imported = list(bpy.context.scene.objects)
    imported_roots = [obj for obj in imported if obj.parent is None]

    minimum, maximum = mesh_bounds(imported)
    size = [maximum[i] - minimum[i] for i in range(3)]
    center_x = (minimum[0] + maximum[0]) / 2
    center_y = (minimum[1] + maximum[1]) / 2

    scale_x = WIDTH_M / size[0]
    scale_y = LENGTH_M / size[1]
    scale_z = scale_y
    normalize = Matrix(
        (
            (scale_x, 0, 0, -center_x * scale_x),
            (0, scale_y, 0, -center_y * scale_y),
            (0, 0, scale_z, -minimum[2] * scale_z),
            (0, 0, 0, 1),
        )
    )

    root = bpy.data.objects.new("ARDUINO_NANO_ROOT", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.005
    root["component_slug"] = "arduino-nano"
    root["dimensions_mm"] = [18.0, 45.0]
    root["coordinate_system"] = "+X right, +Y ICSP, +Z up"
    root["source"] = "Existing repository GLB; normalized to official Arduino Nano dimensions"
    bpy.context.scene.collection.objects.link(root)

    for obj in imported_roots:
        old_world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = normalize @ old_world

    anchors = []
    for index, pin_name in enumerate(LEFT_PINS):
        anchors.append(
            add_pin(
                root,
                pin_name,
                -HEADER_ROW_X_M,
                FIRST_PIN_Y_M - index * HEADER_PITCH_M,
            )
        )
    for index, pin_name in enumerate(RIGHT_PINS):
        anchors.append(
            add_pin(
                root,
                pin_name,
                HEADER_ROW_X_M,
                FIRST_PIN_Y_M - index * HEADER_PITCH_M,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
    )

    final_min, final_max = mesh_bounds(list(bpy.context.scene.objects))
    report = {
        "output": str(output_path),
        "root": root.name,
        "root_transform": {
            "location": list(root.location),
            "rotation_euler": list(root.rotation_euler),
            "scale": list(root.scale),
        },
        "mesh_bounds_m": {"min": final_min, "max": final_max},
        "mesh_size_m": [final_max[i] - final_min[i] for i in range(3)],
        "pin_count": len(anchors),
        "pin_pitch_m": HEADER_PITCH_M,
        "header_row_spacing_m": HEADER_ROW_X_M * 2,
        "anchors": anchors,
    }
    print("NORMALIZE_REPORT_BEGIN")
    print(json.dumps(report, indent=2))
    print("NORMALIZE_REPORT_END")


if __name__ == "__main__":
    main()
