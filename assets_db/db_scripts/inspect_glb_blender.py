"""Inspect a GLB with Blender and print machine-readable geometry facts.

Run with:
  blender --background --factory-startup --python inspect_glb_blender.py -- <file.glb>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def _arguments_after_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _bounds(values: list[float]) -> list[float]:
    return [min(values), max(values)]


def _cluster_lower_vertices(vertices, z_min: float, height: float) -> list[dict]:
    """Find the two likely lead columns in the lower half of an axial part."""
    selected = [vertex for vertex in vertices if vertex.z <= z_min + height * 0.55]
    if len(selected) < 2:
        return []

    centers = [
        [selected[0].x, selected[0].y],
        [selected[-1].x, selected[-1].y],
    ]
    for _ in range(20):
        clusters = [[], []]
        for vertex in selected:
            distances = [
                (vertex.x - center[0]) ** 2 + (vertex.y - center[1]) ** 2
                for center in centers
            ]
            clusters[0 if distances[0] <= distances[1] else 1].append(vertex)
        updated = [
            [
                sum(vertex.x for vertex in cluster) / len(cluster),
                sum(vertex.y for vertex in cluster) / len(cluster),
            ]
            for cluster in clusters
        ]
        if updated == centers:
            break
        centers = updated

    candidates = []
    for index, cluster in enumerate(clusters):
        cluster_z_min = min(vertex.z for vertex in cluster)
        tip_vertices = [
            vertex
            for vertex in cluster
            if vertex.z <= cluster_z_min + height * 0.005
        ]
        candidates.append(
            {
                "cluster": index,
                "vertexCount": len(cluster),
                "centerXY": centers[index],
                "zRange": _bounds([vertex.z for vertex in cluster]),
                "tipCentroid": [
                    sum(vertex.x for vertex in tip_vertices) / len(tip_vertices),
                    sum(vertex.y for vertex in tip_vertices) / len(tip_vertices),
                    sum(vertex.z for vertex in tip_vertices) / len(tip_vertices),
                ],
                "tipVertexCount": len(tip_vertices),
            }
        )
    return sorted(candidates, key=lambda candidate: candidate["tipCentroid"][2])


def main() -> None:
    arguments = _arguments_after_separator()
    if len(arguments) != 1:
        raise SystemExit("Expected one GLB path after --")

    source_path = Path(arguments[0]).resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source_path))

    objects = []
    for obj in bpy.context.scene.objects:
        item = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotationEuler": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "dimensions": list(obj.dimensions),
        }
        if obj.type == "MESH":
            vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
            x_values = [vertex.x for vertex in vertices]
            y_values = [vertex.y for vertex in vertices]
            z_values = [vertex.z for vertex in vertices]
            z_min = min(z_values)
            height = max(z_values) - z_min

            bottom_slices = []
            for fraction in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05):
                selected = [
                    vertex
                    for vertex in vertices
                    if vertex.z <= z_min + (height * fraction)
                ]
                bottom_slices.append(
                    {
                        "heightFraction": fraction,
                        "vertexCount": len(selected),
                        "xRange": _bounds([vertex.x for vertex in selected]),
                        "yRange": _bounds([vertex.y for vertex in selected]),
                        "centroid": [
                            sum(vertex.x for vertex in selected) / len(selected),
                            sum(vertex.y for vertex in selected) / len(selected),
                            sum(vertex.z for vertex in selected) / len(selected),
                        ],
                    }
                )

            vertical_profile = []
            for index in range(20):
                lower = z_min + height * (index / 20)
                upper = z_min + height * ((index + 1) / 20)
                selected = [
                    vertex for vertex in vertices if lower <= vertex.z <= upper
                ]
                if not selected:
                    continue
                vertical_profile.append(
                    {
                        "rangeFraction": [index / 20, (index + 1) / 20],
                        "vertexCount": len(selected),
                        "xRange": _bounds([vertex.x for vertex in selected]),
                        "yRange": _bounds([vertex.y for vertex in selected]),
                    }
                )

            item.update(
                {
                    "vertexCount": len(obj.data.vertices),
                    "polygonCount": len(obj.data.polygons),
                    "worldBounds": {
                        "x": _bounds(x_values),
                        "y": _bounds(y_values),
                        "z": _bounds(z_values),
                    },
                    "bottomSlices": bottom_slices,
                    "verticalProfile": vertical_profile,
                    "lowerRegionClusters": _cluster_lower_vertices(
                        vertices, z_min, height
                    ),
                }
            )
        objects.append(item)

    result = {
        "source": str(source_path),
        "objects": objects,
        "images": [
            {
                "name": image.name,
                "size": list(image.size),
                "packed": image.packed_file is not None,
            }
            for image in bpy.data.images
            if image.name not in {"Render Result", "Viewer Node"}
        ],
    }
    print("CODEX_GLTF_INSPECTION=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
