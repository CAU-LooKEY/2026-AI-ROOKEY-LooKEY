"""Inspect likely through-hole contact clusters in the lower part of a GLB.

Run with:
  blender --background --factory-startup --python inspect_contact_clusters_blender.py \
    -- <file.glb> [cluster-count] [lower-height-fraction]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _arguments_after_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _kmeans_xy(points: list[Vector], count: int) -> list[list[Vector]]:
    ordered = sorted(points, key=lambda point: (point.x, point.y))
    seeds = [
        ordered[round(index * (len(ordered) - 1) / max(count - 1, 1))]
        for index in range(count)
    ]
    centers = [Vector((seed.x, seed.y)) for seed in seeds]
    clusters: list[list[Vector]] = [[] for _ in range(count)]

    for _ in range(50):
        clusters = [[] for _ in range(count)]
        for point in points:
            xy = Vector((point.x, point.y))
            distances = [(xy - center).length_squared for center in centers]
            clusters[min(range(count), key=distances.__getitem__)].append(point)

        if any(not cluster for cluster in clusters):
            raise RuntimeError("Could not form non-empty contact clusters")

        updated = [
            sum(
                (Vector((point.x, point.y)) for point in cluster),
                Vector((0, 0)),
            )
            / len(cluster)
            for cluster in clusters
        ]
        if all((updated[index] - centers[index]).length < 1e-10 for index in range(count)):
            break
        centers = updated

    return clusters


def main() -> None:
    arguments = _arguments_after_separator()
    if not arguments:
        raise SystemExit("Expected a GLB path after --")

    source_path = Path(arguments[0]).resolve()
    cluster_count = int(arguments[1]) if len(arguments) > 1 else 4
    lower_fraction = float(arguments[2]) if len(arguments) > 2 else 0.25

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source_path))

    mesh_points: list[Vector] = []
    mesh_summaries = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        mesh_points.extend(points)
        mesh_summaries.append(
            {
                "name": obj.name,
                "vertexCount": len(points),
                "zMin": min(point.z for point in points),
                "zMax": max(point.z for point in points),
            }
        )

    if not mesh_points:
        raise RuntimeError("The source GLB contains no mesh vertices")

    z_min = min(point.z for point in mesh_points)
    z_max = max(point.z for point in mesh_points)
    threshold = z_min + (z_max - z_min) * lower_fraction
    selected = [point for point in mesh_points if point.z <= threshold]
    if len(selected) < cluster_count:
        raise RuntimeError("Not enough lower-region vertices for contact clustering")

    clusters = _kmeans_xy(selected, cluster_count)
    result = {
        "source": str(source_path),
        "zRange": [z_min, z_max],
        "threshold": threshold,
        "selectedVertexCount": len(selected),
        "meshes": mesh_summaries,
        "clusters": sorted(
            [
                {
                    "vertexCount": len(cluster),
                    "centerXY": [
                        sum(point.x for point in cluster) / len(cluster),
                        sum(point.y for point in cluster) / len(cluster),
                    ],
                    "xRange": [min(point.x for point in cluster), max(point.x for point in cluster)],
                    "yRange": [min(point.y for point in cluster), max(point.y for point in cluster)],
                    "zRange": [min(point.z for point in cluster), max(point.z for point in cluster)],
                }
                for cluster in clusters
            ],
            key=lambda cluster: (cluster["centerXY"][0], cluster["centerXY"][1]),
        ),
    }
    print("CODEX_CONTACT_CLUSTERS=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
