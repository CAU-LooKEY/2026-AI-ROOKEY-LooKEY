"""Add six ICSP pin-tip anchors to an already-normalized Arduino Nano GLB.

Run with Blender:
  blender --background --python add_nano_icsp_anchors.py -- INPUT.glb OUTPUT.glb
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


# Centers measured from the six post meshes after the normalized GLB round trip.
# Blender coordinates: +X right, +Y toward the ICSP end, +Z up.
ICSP_X = (-0.00267, 0.0, 0.00267)
ICSP_Y_OUTER = 0.021152
ICSP_Y_INNER = 0.018456
ICSP_TIP_Z = 0.0148467
SIDE_HEADER_INSERTION_Z = 0.004

# Official Arduino Nano ICSP numbering, viewed from the top:
#   1 3 5  (outer board edge)
#   2 4 6  (board interior)
ICSP_PINS = (
    ("ICSP_CIPO", ICSP_X[0], ICSP_Y_OUTER, 1),
    ("ICSP_5V", ICSP_X[0], ICSP_Y_INNER, 2),
    ("ICSP_SCK", ICSP_X[1], ICSP_Y_OUTER, 3),
    ("ICSP_COPI", ICSP_X[1], ICSP_Y_INNER, 4),
    ("ICSP_RESET", ICSP_X[2], ICSP_Y_OUTER, 5),
    ("ICSP_GND", ICSP_X[2], ICSP_Y_INNER, 6),
)


def arguments() -> tuple[Path, Path]:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 2:
        raise SystemExit("Expected INPUT.glb OUTPUT.glb")
    return Path(argv[0]).resolve(), Path(argv[1]).resolve()


def main() -> None:
    input_path, output_path = arguments()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(input_path))

    root = bpy.data.objects.get("ARDUINO_NANO_ROOT")
    if root is None:
        raise RuntimeError("ARDUINO_NANO_ROOT is missing")

    # The two 15-pin rows snap to the breadboard surface at the insertion
    # plane, 4 mm above their downward-facing tips.
    for pin in bpy.context.scene.objects:
        if (
            pin.type == "EMPTY"
            and pin.name.startswith("pin_")
            and not pin.name.startswith("pin_ICSP_")
        ):
            pin.location.z = SIDE_HEADER_INSERTION_Z

    for pin_key, x, y, number in ICSP_PINS:
        node_name = f"pin_{pin_key}"
        old = bpy.data.objects.get(node_name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        pin = bpy.data.objects.new(node_name, None)
        pin.empty_display_type = "PLAIN_AXES"
        pin.empty_display_size = 0.001
        pin.location = (x, y, ICSP_TIP_Z)
        pin.parent = root
        pin["pin_key"] = pin_key
        pin["anchor_role"] = "electrical_terminal"
        pin["connector_group"] = "ICSP"
        pin["icsp_pin_number"] = number
        pin["coordinate_unit"] = "meter"
        bpy.context.scene.collection.objects.link(pin)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
    )
    print(f"Added {len(ICSP_PINS)} ICSP anchors to {output_path}")


if __name__ == "__main__":
    main()
