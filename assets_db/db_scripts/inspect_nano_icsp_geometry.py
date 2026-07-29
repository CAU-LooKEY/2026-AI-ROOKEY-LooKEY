"""Print Arduino Nano mesh bounds and candidate ICSP pin center clusters."""

from collections import defaultdict
import sys
from pathlib import Path

import bpy
from mathutils import Vector


path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(path))

for obj in sorted((item for item in bpy.context.scene.objects if item.type == "MESH"), key=lambda item: item.name):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum = Vector(min(point[i] for point in points) for i in range(3))
    maximum = Vector(max(point[i] for point in points) for i in range(3))
    print(
        "MESH",
        obj.name,
        "verts",
        len(points),
        "min_mm",
        tuple(round(value * 1000, 4) for value in minimum),
        "max_mm",
        tuple(round(value * 1000, 4) for value in maximum),
    )

    # ICSP posts are the only tall metal geometry at the +Y end. Group their
    # high vertices into 0.1 mm XY buckets so the six post centers are obvious.
    candidates = [
        point
        for point in points
        if point.y > 0.014 and point.z > 0.009
    ]
    if not candidates:
        continue
    buckets = defaultdict(list)
    for point in candidates:
        key = (round(point.x * 10000), round(point.y * 10000))
        buckets[key].append(point)
    occupied = [
        (
            len(bucket),
            sum(point.x for point in bucket) / len(bucket) * 1000,
            sum(point.y for point in bucket) / len(bucket) * 1000,
            min(point.z for point in bucket) * 1000,
            max(point.z for point in bucket) * 1000,
        )
        for bucket in buckets.values()
        if len(bucket) >= 2
    ]
    for count, x, y, z_min, z_max in sorted(occupied, reverse=True)[:40]:
        print(
            "  CLUSTER",
            count,
            "center_xy_mm",
            (round(x, 4), round(y, 4)),
            "z_mm",
            (round(z_min, 4), round(z_max, 4)),
        )
