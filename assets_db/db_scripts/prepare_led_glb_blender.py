"""Normalize and optimize a two-lead LED GLB for the LooKEY runtime.

The source is never modified. The generated GLB uses meters, a common mounting
plane at the origin, a 2.54 mm lead pitch, and named pin anchor nodes.

Run with:
  blender --background --factory-startup --python prepare_led_glb_blender.py \
    -- <source.glb> <output.glb>
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


TARGET_DIAMETER_METER = 0.005
TARGET_PIN_PITCH_METER = 0.00254
TARGET_POLYGON_COUNT = 30_000
MAX_TEXTURE_EDGE = 512
MOUNTING_PLANE_HEIGHT_FRACTION = 0.55
BODY_START_HEIGHT_FRACTION = 0.75


def _arguments_after_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _kmeans_two(vertices: list[Vector]) -> list[list[Vector]]:
    centers = [
        Vector((vertices[0].x, vertices[0].y)),
        Vector((vertices[-1].x, vertices[-1].y)),
    ]
    clusters: list[list[Vector]] = [[], []]
    for _ in range(30):
        clusters = [[], []]
        for vertex in vertices:
            point = Vector((vertex.x, vertex.y))
            distances = [(point - center).length_squared for center in centers]
            clusters[0 if distances[0] <= distances[1] else 1].append(vertex)
        updated = [
            sum((Vector((v.x, v.y)) for v in cluster), Vector((0, 0)))
            / len(cluster)
            for cluster in clusters
        ]
        if all((updated[i] - centers[i]).length < 1e-9 for i in range(2)):
            break
        centers = updated
    return clusters


def _cluster_center(cluster: list[Vector]) -> Vector:
    return sum(cluster, Vector()) / len(cluster)


def _rotate_xy(point: Vector, angle: float) -> Vector:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return Vector(
        (
            point.x * cosine - point.y * sine,
            point.x * sine + point.y * cosine,
            point.z,
        )
    )


def _resize_images() -> list[dict]:
    resized = []
    for image in bpy.data.images:
        if image.name in {"Render Result", "Viewer Node"}:
            continue
        width, height = image.size
        longest = max(width, height)
        if longest <= MAX_TEXTURE_EDGE:
            continue
        ratio = MAX_TEXTURE_EDGE / longest
        new_size = [max(1, round(width * ratio)), max(1, round(height * ratio))]
        image.scale(*new_size)
        resized.append({"name": image.name, "from": [width, height], "to": new_size})
    return resized


def _add_pin_anchor(root, name: str, pin_key: str, x_position: float):
    anchor = bpy.data.objects.new(name, None)
    anchor.empty_display_type = "ARROWS"
    anchor.empty_display_size = 0.00075
    anchor.location = (x_position, 0, 0)
    anchor.rotation_euler = (math.pi, 0, 0)
    anchor["pinKey"] = pin_key
    anchor["connectorGender"] = "male"
    anchor["connectorForm"] = "lead"
    anchor["authoringOutwardAxis"] = "-Z"
    anchor["runtimeOutwardAxis"] = "-Y"
    anchor.parent = root
    bpy.context.scene.collection.objects.link(anchor)
    return anchor


def main() -> None:
    arguments = _arguments_after_separator()
    if len(arguments) != 2:
        raise SystemExit("Expected source and output GLB paths after --")

    source_path = Path(arguments[0]).resolve()
    output_path = Path(arguments[1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("The source GLB contains no mesh")

    mesh_object = max(mesh_objects, key=lambda obj: len(obj.data.vertices))
    mesh_object.name = "led_body"
    bpy.context.view_layer.objects.active = mesh_object
    mesh_object.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    original_vertices = [vertex.co.copy() for vertex in mesh_object.data.vertices]
    x_values = [vertex.x for vertex in original_vertices]
    y_values = [vertex.y for vertex in original_vertices]
    z_values = [vertex.z for vertex in original_vertices]
    z_min = min(z_values)
    z_max = max(z_values)
    height = z_max - z_min
    lower_vertices = [
        vertex
        for vertex in original_vertices
        if vertex.z <= z_min + height * MOUNTING_PLANE_HEIGHT_FRACTION
    ]
    clusters = _kmeans_two(lower_vertices)
    centers = [_cluster_center(cluster) for cluster in clusters]
    tip_heights = [min(vertex.z for vertex in cluster) for cluster in clusters]
    anode_index = 0 if tip_heights[0] < tip_heights[1] else 1
    cathode_index = 1 - anode_index

    lead_midpoint = (centers[anode_index] + centers[cathode_index]) / 2
    cathode_to_anode = centers[anode_index] - centers[cathode_index]
    rotation_angle = -math.atan2(cathode_to_anode.y, cathode_to_anode.x)
    diameter = max(max(x_values) - min(x_values), max(y_values) - min(y_values))
    scale = TARGET_DIAMETER_METER / diameter
    mounting_z = z_min + height * MOUNTING_PLANE_HEIGHT_FRACTION
    body_start_z = z_min + height * BODY_START_HEIGHT_FRACTION

    transformed_centers = []
    for center in centers:
        centered = Vector(
            (center.x - lead_midpoint.x, center.y - lead_midpoint.y, center.z - mounting_z)
        )
        transformed_centers.append(_rotate_xy(centered, rotation_angle) * scale)

    target_x = {
        anode_index: TARGET_PIN_PITCH_METER / 2,
        cathode_index: -TARGET_PIN_PITCH_METER / 2,
    }
    shifts = {
        index: Vector(
            (
                target_x[index] - transformed_centers[index].x,
                -transformed_centers[index].y,
                0,
            )
        )
        for index in range(2)
    }

    for mesh_vertex, original in zip(mesh_object.data.vertices, original_vertices):
        distances = [
            (original.x - center.x) ** 2 + (original.y - center.y) ** 2
            for center in centers
        ]
        cluster_index = 0 if distances[0] <= distances[1] else 1
        centered = Vector(
            (
                original.x - lead_midpoint.x,
                original.y - lead_midpoint.y,
                original.z - mounting_z,
            )
        )
        transformed = _rotate_xy(centered, rotation_angle) * scale
        if original.z <= mounting_z:
            shift_weight = 1
        elif original.z < body_start_z:
            shift_weight = 1 - (
                (original.z - mounting_z) / (body_start_z - mounting_z)
            )
        else:
            shift_weight = 0
        mesh_vertex.co = transformed + shifts[cluster_index] * shift_weight

    pre_weld_vertex_count = len(mesh_object.data.vertices)
    editable_mesh = bmesh.new()
    editable_mesh.from_mesh(mesh_object.data)
    bmesh.ops.remove_doubles(
        editable_mesh, verts=list(editable_mesh.verts), dist=1e-8
    )
    editable_mesh.to_mesh(mesh_object.data)
    editable_mesh.free()
    mesh_object.data.update()
    for polygon in mesh_object.data.polygons:
        polygon.use_smooth = True

    welded_vertex_count = len(mesh_object.data.vertices)
    original_polygon_count = len(mesh_object.data.polygons)
    for pass_index in range(3):
        current_polygon_count = len(mesh_object.data.polygons)
        if current_polygon_count <= TARGET_POLYGON_COUNT:
            break
        modifier = mesh_object.modifiers.new(name="web_decimate", type="DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = max(0.01, TARGET_POLYGON_COUNT / current_polygon_count)
        bpy.context.view_layer.objects.active = mesh_object
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        if len(mesh_object.data.polygons) >= current_polygon_count:
            break

    root = bpy.data.objects.new("led-5mm-red", None)
    root["componentSlug"] = "led-5mm-red"
    root["schemaVersion"] = "1.0.0"
    bpy.context.scene.collection.objects.link(root)
    mesh_object.parent = root
    _add_pin_anchor(
        root, "pin_anode", "ANODE", TARGET_PIN_PITCH_METER / 2
    )
    _add_pin_anchor(
        root, "pin_cathode", "CATHODE", -TARGET_PIN_PITCH_METER / 2
    )

    resized_images = _resize_images()
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_extras=True,
    )

    print(
        "CODEX_LED_PREP="
        + json.dumps(
            {
                "source": str(source_path),
                "output": str(output_path),
                "sourcePolygonCount": original_polygon_count,
                "outputPolygonCount": len(mesh_object.data.polygons),
                "sourceVertexCount": pre_weld_vertex_count,
                "weldedVertexCount": welded_vertex_count,
                "outputVertexCount": len(mesh_object.data.vertices),
                "sourceDiameterMeter": diameter,
                "scaleFactor": scale,
                "pinPitchMeter": TARGET_PIN_PITCH_METER,
                "anodeWasLongLead": True,
                "resizedImages": resized_images,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
