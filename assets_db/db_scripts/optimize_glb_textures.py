"""Downscale oversized embedded GLB textures without changing scene transforms.

Usage:
  blender --background --factory-startup --python optimize_glb_textures.py -- \
    input.glb output.glb [max_texture_size] [max_faces_per_mesh]
"""

import sys
from pathlib import Path

import bpy


def cli_args() -> tuple[Path, Path, int, int]:
    if "--" not in sys.argv:
        raise SystemExit("Pass input and output GLB paths after --")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) not in {2, 3, 4}:
        raise SystemExit(
            "Expected input.glb output.glb [max_texture_size] [max_faces_per_mesh]"
        )
    maximum = int(args[2]) if len(args) >= 3 else 2048
    max_faces = int(args[3]) if len(args) == 4 else 150_000
    if maximum < 256:
        raise SystemExit("max_texture_size must be at least 256")
    if max_faces < 10_000:
        raise SystemExit("max_faces_per_mesh must be at least 10000")
    return Path(args[0]).resolve(), Path(args[1]).resolve(), maximum, max_faces


source, destination, max_texture_size, max_faces_per_mesh = cli_args()
if not source.exists():
    raise SystemExit(f"GLB not found: {source}")
if source == destination:
    raise SystemExit("Input and output paths must be different")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))

resized = []
for image in bpy.data.images:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_texture_size:
        continue
    ratio = max_texture_size / longest
    target_width = max(1, round(width * ratio))
    target_height = max(1, round(height * ratio))
    image.scale(target_width, target_height)
    resized.append((image.name, width, height, target_width, target_height))

decimated = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    face_count = len(obj.data.polygons)
    if face_count <= max_faces_per_mesh:
        continue
    modifier = obj.modifiers.new(name="asset_db_decimate", type="DECIMATE")
    modifier.ratio = max_faces_per_mesh / face_count
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    decimated.append((obj.name, face_count, len(obj.data.polygons)))

destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(destination),
    export_format="GLB",
    export_yup=True,
    export_apply=False,
    export_extras=True,
    export_animations=False,
    export_cameras=False,
    export_lights=False,
)

print(f"Optimized {source.name}: {source.stat().st_size} -> {destination.stat().st_size} bytes")
for name, old_width, old_height, width, height in resized:
    print(f"  {name}: {old_width}x{old_height} -> {width}x{height}")
for name, old_faces, faces in decimated:
    print(f"  {name}: {old_faces} -> {faces} faces")
