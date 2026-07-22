"""Render a transparent front-view thumbnail for a normalized GLB.

Run with:
  blender --background --factory-startup --python render_glb_thumbnail_blender.py \
    -- <source.glb> <output.png>
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector


THUMBNAIL_SIZE = 512
FRAME_MARGIN = 1.2


def _arguments_after_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _point_at(obj, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    arguments = _arguments_after_separator()
    if len(arguments) != 2:
        raise SystemExit("Expected source GLB and output PNG paths after --")

    source_path = Path(arguments[0]).resolve()
    output_path = Path(arguments[1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("The source GLB contains no mesh")

    world_corners = [
        obj.matrix_world @ Vector(corner)
        for obj in mesh_objects
        for corner in obj.bound_box
    ]
    x_min = min(corner.x for corner in world_corners)
    x_max = max(corner.x for corner in world_corners)
    z_min = min(corner.z for corner in world_corners)
    z_max = max(corner.z for corner in world_corners)
    target = Vector(((x_min + x_max) / 2, 0, (z_min + z_max) / 2))

    bpy.ops.object.camera_add(location=(target.x, -0.08, target.z))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(x_max - x_min, z_max - z_min) * FRAME_MARGIN
    camera.data.clip_start = 0.001
    camera.data.clip_end = 1
    _point_at(camera, target)

    for location, energy, size in (
        ((0.03, -0.04, 0.04), 3, 0.04),
        ((-0.03, -0.02, 0.01), 1.5, 0.03),
        ((0, 0.02, 0.04), 2, 0.03),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        _point_at(light, target)

    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = THUMBNAIL_SIZE
    scene.render.resolution_y = THUMBNAIL_SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filepath = str(output_path)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("thumbnail_world")
    scene.world.color = (0.04, 0.04, 0.04)
    bpy.ops.render.render(write_still=True)

    print(f"CODEX_THUMBNAIL={output_path}")


if __name__ == "__main__":
    main()
