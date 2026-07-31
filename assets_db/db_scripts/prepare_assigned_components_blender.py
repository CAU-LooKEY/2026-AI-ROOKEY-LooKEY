"""Normalize the assigned HC-SR04, resistor, and pushbutton GLBs.

The generated assets use meters, a mounting plane at the origin, runtime +Y
up, runtime +Z front, and named pin anchor nodes.

Run with:
  blender --background --factory-startup --python prepare_assigned_components_blender.py \
    -- <component-slug> <source.glb> <output.glb>
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


HC_PIN_PITCH_METER = 0.00254
HC_INSERTION_DEPTH_METER = 0.006
BUTTON_INSERTION_DEPTH_METER = 0.0035
RESISTOR_BODY_LENGTH_METER = 0.0065
RESISTOR_BODY_DIAMETER_METER = 0.0023
RESISTOR_SPAN_METER = 0.01016
RESISTOR_BODY_CENTER_HEIGHT_METER = 0.003
RESISTOR_LEAD_DEPTH_METER = 0.003


def _arguments_after_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _world_points(obj) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def _point_bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(
            (
                min(point.x for point in points),
                min(point.y for point in points),
                min(point.z for point in points),
            )
        ),
        Vector(
            (
                max(point.x for point in points),
                max(point.y for point in points),
                max(point.z for point in points),
            )
        ),
    )


def _bounds_for_objects(objects) -> tuple[Vector, Vector]:
    return _point_bounds(
        [point for obj in objects if obj.type == "MESH" for point in _world_points(obj)]
    )


def _flatten_mesh(obj, transform) -> None:
    points = _world_points(obj)
    obj.data = obj.data.copy()
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    for vertex, point in zip(obj.data.vertices, points):
        vertex.co = transform(point)
    obj.data.update()


def _remove_non_mesh_objects() -> None:
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)


def _create_root(component_slug: str):
    root = bpy.data.objects.new(component_slug, None)
    root["componentSlug"] = component_slug
    root["schemaVersion"] = "1.0.0"
    root["assetStatus"] = "candidate"
    bpy.context.scene.collection.objects.link(root)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.parent is None:
            obj.parent = root
    return root


def _add_pin_anchor(
    root,
    name: str,
    pin_key: str,
    location: Vector,
    *,
    connector_form: str,
    insertion_depth_meter: float,
):
    anchor = bpy.data.objects.new(name, None)
    anchor.empty_display_type = "ARROWS"
    anchor.empty_display_size = 0.00075
    anchor.location = location
    anchor.rotation_euler = (math.pi, 0, 0)
    anchor["pinKey"] = pin_key
    anchor["connectorGender"] = "male"
    anchor["connectorForm"] = connector_form
    anchor["insertionDepthMillimeter"] = round(insertion_depth_meter * 1000, 3)
    anchor["authoringOutwardAxis"] = "-Z"
    anchor["runtimeOutwardAxis"] = "-Y"
    anchor.parent = root
    bpy.context.scene.collection.objects.link(anchor)
    return anchor


def _runtime_position(authoring_position: Vector) -> list[float]:
    return [authoring_position.x, authoring_position.z, -authoring_position.y]


def _kmeans_xy(points: list[Vector], count: int) -> list[list[Vector]]:
    min_point, max_point = _point_bounds(points)
    seeds = [
        Vector((min_point.x, min_point.y)),
        Vector((min_point.x, max_point.y)),
        Vector((max_point.x, min_point.y)),
        Vector((max_point.x, max_point.y)),
    ][:count]
    centers = seeds
    clusters: list[list[Vector]] = [[] for _ in range(count)]
    for _ in range(50):
        clusters = [[] for _ in range(count)]
        for point in points:
            xy = Vector((point.x, point.y))
            distances = [(xy - center).length_squared for center in centers]
            clusters[min(range(count), key=distances.__getitem__)].append(point)
        if any(not cluster for cluster in clusters):
            raise RuntimeError("Could not identify all contact clusters")
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


def _prepare_hc_sr04(meshes) -> tuple[object, list[dict], dict]:
    global_min, global_max = _bounds_for_objects(meshes)
    global_size = global_max - global_min
    pin_candidates = []
    for obj in meshes:
        minimum, maximum = _point_bounds(_world_points(obj))
        size = maximum - minimum
        if (
            size.x < global_size.x * 0.05
            and minimum.z < global_min.z + global_size.z * 0.05
            and size.z > global_size.z * 0.2
        ):
            pin_candidates.append(
                {
                    "object": obj,
                    "center": (minimum + maximum) / 2,
                    "minimum": minimum,
                    "maximum": maximum,
                }
            )
    pin_candidates.sort(key=lambda candidate: candidate["center"].x)
    if len(pin_candidates) != 4:
        raise RuntimeError(f"Expected 4 HC-SR04 pin meshes, found {len(pin_candidates)}")

    source_pitch = (
        pin_candidates[-1]["center"].x - pin_candidates[0]["center"].x
    ) / 3
    scale = HC_PIN_PITCH_METER / source_pitch
    origin_x = (
        pin_candidates[0]["center"].x + pin_candidates[-1]["center"].x
    ) / 2
    origin_y = sum(candidate["center"].y for candidate in pin_candidates) / 4
    pin_tip_z = min(candidate["minimum"].z for candidate in pin_candidates)
    origin_z = pin_tip_z + HC_INSERTION_DEPTH_METER / scale

    def transform(point: Vector) -> Vector:
        return Vector(
            (
                (point.x - origin_x) * scale,
                (point.y - origin_y) * scale,
                (point.z - origin_z) * scale,
            )
        )

    for obj in meshes:
        _flatten_mesh(obj, transform)
    _remove_non_mesh_objects()
    root = _create_root("hc-sr04")

    anchors = []
    for pin_key, candidate in zip(("VCC", "TRIG", "ECHO", "GND"), pin_candidates):
        location = Vector(((candidate["center"].x - origin_x) * scale, 0, 0))
        _add_pin_anchor(
            root,
            f"pin_{pin_key.lower()}",
            pin_key,
            location,
            connector_form="pin",
            insertion_depth_meter=HC_INSERTION_DEPTH_METER,
        )
        anchors.append(
            {
                "pinKey": pin_key,
                "nodeName": f"pin_{pin_key.lower()}",
                "authoringPosition": list(location),
                "runtimePosition": _runtime_position(location),
            }
        )
    return root, anchors, {
        "sourcePitch": source_pitch,
        "scaleFactor": scale,
        "targetPitchMeter": HC_PIN_PITCH_METER,
        "insertionDepthMeter": HC_INSERTION_DEPTH_METER,
    }


def _create_lead_curve(name: str, points: list[Vector], material, root):
    curve = bpy.data.curves.new(name=name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = 0.00022
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = root
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj


def _prepare_resistor(meshes) -> tuple[object, list[dict], dict]:
    measured = []
    for obj in meshes:
        minimum, maximum = _point_bounds(_world_points(obj))
        measured.append(
            {"object": obj, "minimum": minimum, "maximum": maximum, "size": maximum - minimum}
        )
    wire = max(measured, key=lambda item: item["size"].z)
    body = max(
        (item for item in measured if item is not wire),
        key=lambda item: item["size"].z,
    )
    body_center = (body["minimum"] + body["maximum"]) / 2
    axial_scale = RESISTOR_BODY_LENGTH_METER / body["size"].z
    radial_scale = RESISTOR_BODY_DIAMETER_METER / max(body["size"].x, body["size"].y)

    wire_object = wire["object"]
    remaining = [obj for obj in meshes if obj is not wire_object]
    bpy.data.objects.remove(wire_object, do_unlink=True)

    def transform(point: Vector) -> Vector:
        return Vector(
            (
                (point.z - body_center.z) * axial_scale,
                (point.y - body_center.y) * radial_scale,
                RESISTOR_BODY_CENTER_HEIGHT_METER
                + (point.x - body_center.x) * radial_scale,
            )
        )

    for obj in remaining:
        _flatten_mesh(obj, transform)
    _remove_non_mesh_objects()
    root = _create_root("resistor-220-ohm")

    lead_material = bpy.data.materials.new("resistor_lead_metal")
    lead_material.diffuse_color = (0.62, 0.65, 0.68, 1)
    lead_material.metallic = 0.8
    lead_material.roughness = 0.3
    half_body = RESISTOR_BODY_LENGTH_METER / 2
    half_span = RESISTOR_SPAN_METER / 2
    for side, name in ((-1, "lead_a_geometry"), (1, "lead_b_geometry")):
        _create_lead_curve(
            name,
            [
                Vector((side * half_body, 0, RESISTOR_BODY_CENTER_HEIGHT_METER)),
                Vector((side * (half_span - 0.00035), 0, RESISTOR_BODY_CENTER_HEIGHT_METER)),
                Vector((side * half_span, 0, RESISTOR_BODY_CENTER_HEIGHT_METER - 0.00035)),
                Vector((side * half_span, 0, -RESISTOR_LEAD_DEPTH_METER)),
            ],
            lead_material,
            root,
        )

    anchors = []
    for pin_key, x_position in (("LEAD_A", -half_span), ("LEAD_B", half_span)):
        location = Vector((x_position, 0, 0))
        node_name = f"pin_{pin_key.lower()}"
        _add_pin_anchor(
            root,
            node_name,
            pin_key,
            location,
            connector_form="lead",
            insertion_depth_meter=RESISTOR_LEAD_DEPTH_METER,
        )
        anchors.append(
            {
                "pinKey": pin_key,
                "nodeName": node_name,
                "authoringPosition": list(location),
                "runtimePosition": _runtime_position(location),
            }
        )
    return root, anchors, {
        "axialScaleFactor": axial_scale,
        "radialScaleFactor": radial_scale,
        "bodyLengthMeter": RESISTOR_BODY_LENGTH_METER,
        "bodyDiameterMeter": RESISTOR_BODY_DIAMETER_METER,
        "recommendedSpanMeter": RESISTOR_SPAN_METER,
        "insertionDepthMeter": RESISTOR_LEAD_DEPTH_METER,
    }


def _prepare_pushbutton(meshes) -> tuple[object, list[dict], dict]:
    points = [point for obj in meshes for point in _world_points(obj)]
    minimum, maximum = _point_bounds(points)
    height = maximum.z - minimum.z
    lower_points = [point for point in points if point.z <= minimum.z + height * 0.15]
    clusters = _kmeans_xy(lower_points, 4)
    centers = [
        Vector(
            (
                sum(point.x for point in cluster) / len(cluster),
                sum(point.y for point in cluster) / len(cluster),
            )
        )
        for cluster in clusters
    ]
    origin_x = sum(center.x for center in centers) / 4
    origin_y = sum(center.y for center in centers) / 4
    origin_z = minimum.z + BUTTON_INSERTION_DEPTH_METER

    def transform(point: Vector) -> Vector:
        return Vector((point.x - origin_x, point.y - origin_y, point.z - origin_z))

    for obj in meshes:
        _flatten_mesh(obj, transform)
    _remove_non_mesh_objects()
    root = _create_root("pushbutton-6x6")

    left = sorted((center for center in centers if center.x < origin_x), key=lambda center: center.y)
    right = sorted((center for center in centers if center.x >= origin_x), key=lambda center: center.y)
    ordered = {
        "A1": left[-1],
        "A2": left[0],
        "B1": right[-1],
        "B2": right[0],
    }
    anchors = []
    for pin_key, center in ordered.items():
        location = Vector((center.x - origin_x, center.y - origin_y, 0))
        node_name = f"pin_{pin_key.lower()}"
        _add_pin_anchor(
            root,
            node_name,
            pin_key,
            location,
            connector_form="lead",
            insertion_depth_meter=BUTTON_INSERTION_DEPTH_METER,
        )
        anchors.append(
            {
                "pinKey": pin_key,
                "nodeName": node_name,
                "authoringPosition": list(location),
                "runtimePosition": _runtime_position(location),
            }
        )
    return root, anchors, {
        "sourceUnit": "meter",
        "insertionDepthMeter": BUTTON_INSERTION_DEPTH_METER,
        "measuredContactCenters": [list(center) for center in centers],
    }


def _runtime_bounds() -> dict:
    points = [
        _runtime_position(point)
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        for point in _world_points(obj)
    ]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {
        "min": minimum,
        "max": maximum,
        "size": [maximum[index] - minimum[index] for index in range(3)],
    }


def main() -> None:
    arguments = _arguments_after_separator()
    if len(arguments) != 3:
        raise SystemExit("Expected component slug, source GLB, and output GLB after --")

    component_slug = arguments[0]
    source_path = Path(arguments[1]).resolve()
    output_path = Path(arguments[2]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("The source GLB contains no meshes")

    if component_slug == "hc-sr04":
        root, anchors, details = _prepare_hc_sr04(meshes)
    elif component_slug == "resistor-220-ohm":
        root, anchors, details = _prepare_resistor(meshes)
    elif component_slug == "pushbutton-6x6":
        root, anchors, details = _prepare_pushbutton(meshes)
    else:
        raise RuntimeError(f"Unsupported component slug: {component_slug}")

    bounds = _runtime_bounds()
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_extras=True,
    )
    print(
        "CODEX_COMPONENT_PREP="
        + json.dumps(
            {
                "componentSlug": component_slug,
                "source": str(source_path),
                "output": str(output_path),
                "rootName": root.name,
                "bounds": bounds,
                "anchors": anchors,
                "details": details,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
