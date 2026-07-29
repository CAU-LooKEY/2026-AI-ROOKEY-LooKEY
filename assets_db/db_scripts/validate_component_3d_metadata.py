from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_ROOT = REPO_ROOT / "assets_db" / "3d_models" / "component_metadata"
SCHEMA_PATH = METADATA_ROOT / "schema" / "component-3d-metadata.schema.json"
PIN_CATALOG_PATH = (
    REPO_ROOT / "assets_db" / "db_scripts" / "all_component_pin_coordinates.json"
)

EXPECTED_STATUS = {
    "examples": "example",
    "candidates": "candidate",
    "approved": "approved",
}
ALLOWED_METHODS = {
    "blender-empty",
    "threejs-picker",
    "manual-measure",
    "projected-2d",
    "cad-import",
    "other",
}
ALLOWED_GENDERS = {"male", "female", "genderless", "unknown"}
ALLOWED_CONNECTOR_FORMS = {
    "lead",
    "pin",
    "socket",
    "hole",
    "pad",
    "wire-end",
    "terminal",
    "other",
}
PIN_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_+\-]*$")
NODE_NAME_PATTERN = re.compile(
    r"^pin_(?:[A-Z][A-Z0-9_+\-]*|[a-z0-9_]+)$"
)
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNIT_VECTOR_TOLERANCE = 0.05


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_finite_number(value: Any) -> bool:
    return is_number(value) and math.isfinite(float(value))


def check_vector(
    value: Any,
    label: str,
    errors: list[str],
    *,
    length: int = 3,
    require_unit: bool = False,
) -> None:
    if not isinstance(value, list) or len(value) != length:
        errors.append(f"{label} must be an array of {length} finite numbers")
        return
    if not all(is_finite_number(item) for item in value):
        errors.append(f"{label} must contain only finite numbers")
        return
    if require_unit:
        magnitude = math.sqrt(sum(float(item) ** 2 for item in value))
        if abs(magnitude - 1.0) > UNIT_VECTOR_TOLERANCE:
            errors.append(
                f"{label} must be a unit vector; measured magnitude {magnitude:.6f}"
            )


def check_positive(value: Any, label: str, errors: list[str]) -> None:
    if not is_finite_number(value) or float(value) <= 0:
        errors.append(f"{label} must be a positive finite number")


def check_confidence(value: Any, label: str, errors: list[str]) -> None:
    if not is_finite_number(value) or not 0 <= float(value) <= 1:
        errors.append(f"{label} must be between 0 and 1")


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(raw_path: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{label} must be a non-empty repository-relative path")
        return None

    resolved = (REPO_ROOT / raw_path).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        errors.append(f"{label} escapes the repository: {raw_path}")
        return None
    return resolved


def catalog_pin_keys(catalog: dict[str, Any], component_slug: str) -> set[str]:
    component = catalog.get(component_slug)
    if not isinstance(component, dict):
        return set()
    pins = component.get("pins")
    if not isinstance(pins, list):
        return set()
    keys = {
        pin.get("pin_key")
        for pin in pins
        if isinstance(pin, dict) and isinstance(pin.get("pin_key"), str)
    }
    runtime_procedural = component.get("runtime_procedural")
    if isinstance(runtime_procedural, dict):
        columns = runtime_procedural.get("columns")
        rows = runtime_procedural.get("rows_z_meter")
        if (
            isinstance(columns, dict)
            and isinstance(columns.get("count"), int)
            and isinstance(rows, dict)
        ):
            keys.update(
                f"{row}{column}"
                for row in rows
                if isinstance(row, str)
                for column in range(1, columns["count"] + 1)
            )
    rail_runtime = component.get("rail_runtime")
    if isinstance(rail_runtime, dict):
        rows = rail_runtime.get("rows_z_meter")
        segments = rail_runtime.get("segments_per_row")
        holes = rail_runtime.get("holes_per_segment")
        if (
            isinstance(rows, dict)
            and isinstance(segments, int)
            and isinstance(holes, int)
        ):
            keys.update(
                f"RAIL_{rail_name}_S{segment}_{hole}"
                for rail_name in rows
                if isinstance(rail_name, str)
                for segment in range(1, segments + 1)
                for hole in range(1, holes + 1)
            )
    return keys


def validate_metadata(
    path: Path,
    data: Any,
    expected_status: str,
    pin_catalog: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["document root must be a JSON object"]

    required_top_level = {
        "schemaVersion",
        "componentSlug",
        "asset",
        "physicalDimensions",
        "coordinateSystems",
        "origin",
        "orientation",
        "pins",
        "placement",
        "provenance",
        "notes",
    }
    missing = sorted(required_top_level - data.keys())
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")

    if data.get("schemaVersion") != "1.0.0":
        errors.append("schemaVersion must be 1.0.0")

    component_slug = data.get("componentSlug")
    if not isinstance(component_slug, str) or not SLUG_PATTERN.fullmatch(component_slug):
        errors.append("componentSlug must use lowercase kebab-case")
        component_slug = ""

    asset = data.get("asset")
    if not isinstance(asset, dict):
        errors.append("asset must be an object")
        asset = {}

    model_path_value = asset.get("path")
    model_path = resolve_repo_path(model_path_value, "asset.path", errors)
    if model_path is not None:
        if model_path.suffix.lower() != ".glb":
            errors.append("asset.path must point to a .glb file")
        if not model_path.is_file():
            errors.append(f"asset.path does not exist: {model_path_value}")
        else:
            expected_hash = asset.get("sha256")
            if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(
                expected_hash
            ):
                errors.append("asset.sha256 must be 64 lowercase hexadecimal characters")
            else:
                actual_hash = calculate_sha256(model_path)
                if actual_hash != expected_hash:
                    errors.append(
                        "asset.sha256 does not match the current GLB "
                        f"(expected {expected_hash}, actual {actual_hash})"
                    )
        if component_slug and model_path.stem != component_slug:
            errors.append(
                "asset filename stem must match componentSlug "
                f"({model_path.stem} != {component_slug})"
            )

    if asset.get("format") != "glb":
        errors.append("asset.format must be glb")
    scale_status = asset.get("scaleStatus")
    if scale_status not in {"uncalibrated", "real-world"}:
        errors.append("asset.scaleStatus must be uncalibrated or real-world")

    thumbnail_value = asset.get("thumbnailPath")
    if thumbnail_value is not None:
        thumbnail_path = resolve_repo_path(
            thumbnail_value, "asset.thumbnailPath", errors
        )
        if thumbnail_path is not None and not thumbnail_path.is_file():
            errors.append(f"asset.thumbnailPath does not exist: {thumbnail_value}")

    dimensions = data.get("physicalDimensions")
    if not isinstance(dimensions, dict):
        errors.append("physicalDimensions must be an object")
        dimensions = {}
    if dimensions.get("unit") != "millimeter":
        errors.append("physicalDimensions.unit must be millimeter")
    for dimension_name in ("width", "depth", "height"):
        check_positive(
            dimensions.get(dimension_name),
            f"physicalDimensions.{dimension_name}",
            errors,
        )
    check_confidence(
        dimensions.get("confidence"), "physicalDimensions.confidence", errors
    )

    coordinate_systems = data.get("coordinateSystems")
    if not isinstance(coordinate_systems, dict):
        errors.append("coordinateSystems must be an object")
        coordinate_systems = {}
    authoring = coordinate_systems.get("authoring")
    runtime = coordinate_systems.get("runtime")
    if not isinstance(authoring, dict):
        errors.append("coordinateSystems.authoring must be an object")
        authoring = {}
    if not isinstance(runtime, dict):
        errors.append("coordinateSystems.runtime must be an object")
        runtime = {}

    authoring_space = authoring.get("space")
    expected_authoring_up = {
        "blender-object-local": "+Z",
        "threejs-object-local": "+Y",
    }
    if authoring_space not in expected_authoring_up:
        errors.append(
            "coordinateSystems.authoring.space must be blender-object-local "
            "or threejs-object-local"
        )
    elif authoring.get("upAxis") != expected_authoring_up[authoring_space]:
        errors.append(
            "coordinateSystems.authoring.upAxis must match the authoring tool "
            f"({expected_authoring_up[authoring_space]} for {authoring_space})"
        )
    if authoring.get("handedness") != "right":
        errors.append("coordinateSystems.authoring.handedness must be right")

    expected_runtime = {
        "space": "gltf-model-local",
        "handedness": "right",
        "upAxis": "+Y",
    }
    for key, expected_value in expected_runtime.items():
        if runtime.get(key) != expected_value:
            errors.append(f"coordinateSystems.runtime.{key} must be {expected_value}")

    if coordinate_systems.get("anchorsStoredIn") != "runtime":
        errors.append("coordinateSystems.anchorsStoredIn must be runtime")

    runtime_unit = runtime.get("unit")
    units_per_millimeter = runtime.get("modelUnitsPerMillimeter")
    if runtime_unit == "meter":
        if not is_number(units_per_millimeter) or not math.isclose(
            float(units_per_millimeter), 0.001, rel_tol=0, abs_tol=1e-12
        ):
            errors.append(
                "meter runtime models require modelUnitsPerMillimeter = 0.001"
            )
    elif runtime_unit == "model-unit":
        if units_per_millimeter is not None:
            check_positive(
                units_per_millimeter,
                "coordinateSystems.runtime.modelUnitsPerMillimeter",
                errors,
            )
    else:
        errors.append("coordinateSystems.runtime.unit must be meter or model-unit")

    origin = data.get("origin")
    if not isinstance(origin, dict):
        errors.append("origin must be an object")
        origin = {}
    origin_reference = origin.get("targetReference")
    origin_point = origin.get("referencePoint")
    origin_normalized = origin.get("normalized")
    if origin_point is not None:
        check_vector(origin_point, "origin.referencePoint", errors)
    if origin_normalized is True:
        if not isinstance(origin_point, list) or len(origin_point) != 3:
            errors.append("normalized origin requires referencePoint [0, 0, 0]")
        elif any(abs(float(value)) > 1e-9 for value in origin_point):
            errors.append("normalized origin referencePoint must be [0, 0, 0]")

    orientation = data.get("orientation")
    if not isinstance(orientation, dict):
        errors.append("orientation must be an object")
        orientation = {}
    quaternion = orientation.get("defaultRotationQuaternion")
    check_vector(
        quaternion,
        "orientation.defaultRotationQuaternion",
        errors,
        length=4,
        require_unit=True,
    )

    pins = data.get("pins")
    if not isinstance(pins, list) or not pins:
        errors.append("pins must be a non-empty array")
        pins = []

    seen_pin_keys: set[str] = set()
    seen_node_names: set[str] = set()
    metadata_pin_keys: set[str] = set()
    for index, pin in enumerate(pins):
        label = f"pins[{index}]"
        if not isinstance(pin, dict):
            errors.append(f"{label} must be an object")
            continue

        pin_key = pin.get("pinKey")
        if not isinstance(pin_key, str) or not PIN_KEY_PATTERN.fullmatch(pin_key):
            errors.append(f"{label}.pinKey has an invalid format")
        else:
            if pin_key in seen_pin_keys:
                errors.append(f"{label}.pinKey is duplicated: {pin_key}")
            seen_pin_keys.add(pin_key)
            metadata_pin_keys.add(pin_key)

        node_name = pin.get("nodeName")
        if not isinstance(node_name, str) or not NODE_NAME_PATTERN.fullmatch(node_name):
            errors.append(f"{label}.nodeName must match pin_<PIN_KEY>")
        else:
            if node_name in seen_node_names:
                errors.append(f"{label}.nodeName is duplicated: {node_name}")
            seen_node_names.add(node_name)

        check_vector(pin.get("position"), f"{label}.position", errors)
        check_vector(
            pin.get("outwardDirection"),
            f"{label}.outwardDirection",
            errors,
            require_unit=True,
        )
        check_confidence(pin.get("confidence"), f"{label}.confidence", errors)

        connector = pin.get("connector")
        if not isinstance(connector, dict):
            errors.append(f"{label}.connector must be an object")
            connector = {}
        if connector.get("gender") not in ALLOWED_GENDERS:
            errors.append(f"{label}.connector.gender is invalid")
        if connector.get("form") not in ALLOWED_CONNECTOR_FORMS:
            errors.append(f"{label}.connector.form is invalid")
        for optional_measurement in ("pitchMillimeter", "diameterMillimeter"):
            value = connector.get(optional_measurement)
            if value is not None:
                check_positive(
                    value, f"{label}.connector.{optional_measurement}", errors
                )

        mounting = pin.get("mounting")
        if not isinstance(mounting, dict):
            errors.append(f"{label}.mounting must be an object")
            mounting = {}
        insertion_depth = mounting.get("insertionDepthMillimeter")
        if insertion_depth is not None:
            check_positive(
                insertion_depth, f"{label}.mounting.insertionDepthMillimeter", errors
            )

        if expected_status == "approved":
            if not is_number(pin.get("confidence")) or float(pin["confidence"]) < 0.8:
                errors.append(f"{label}.confidence must be at least 0.8 when approved")
            if (
                mounting.get("breadboardCompatible") is True
                and connector.get("gender") == "male"
                and insertion_depth is None
            ):
                errors.append(
                    f"{label} needs insertionDepthMillimeter when approved"
                )

    known_pin_keys = catalog_pin_keys(pin_catalog, component_slug)
    if not known_pin_keys:
        errors.append(
            f"componentSlug is missing from the existing pin catalog: {component_slug}"
        )
    else:
        unknown_keys = sorted(metadata_pin_keys - known_pin_keys)
        if unknown_keys:
            errors.append(
                "metadata contains pin keys not found in the pin catalog: "
                + ", ".join(unknown_keys)
            )
        if expected_status == "approved" and metadata_pin_keys != known_pin_keys:
            missing_keys = sorted(known_pin_keys - metadata_pin_keys)
            extra_keys = sorted(metadata_pin_keys - known_pin_keys)
            if missing_keys:
                errors.append(
                    "approved metadata is missing catalog pins: "
                    + ", ".join(missing_keys)
                )
            if extra_keys:
                errors.append(
                    "approved metadata has extra pins: " + ", ".join(extra_keys)
                )

    markers = orientation.get("markers")
    if not isinstance(markers, list):
        errors.append("orientation.markers must be an array")
    else:
        for index, marker in enumerate(markers):
            if not isinstance(marker, dict):
                errors.append(f"orientation.markers[{index}] must be an object")
                continue
            marker_pin_key = marker.get("pinKey")
            if marker_pin_key is not None and marker_pin_key not in metadata_pin_keys:
                errors.append(
                    f"orientation.markers[{index}].pinKey is not in pins: "
                    f"{marker_pin_key}"
                )

    placement = data.get("placement")
    if not isinstance(placement, dict):
        errors.append("placement must be an object")
        placement = {}
    check_vector(
        placement.get("mountingPlaneNormal"),
        "placement.mountingPlaneNormal",
        errors,
        require_unit=True,
    )
    yaw_values = placement.get("allowedYawDegrees")
    if not isinstance(yaw_values, list):
        errors.append("placement.allowedYawDegrees must be an array")
    else:
        for index, value in enumerate(yaw_values):
            if not is_finite_number(value) or not 0 <= float(value) < 360:
                errors.append(
                    f"placement.allowedYawDegrees[{index}] must be in [0, 360)"
                )
        if len(yaw_values) != len(set(yaw_values)):
            errors.append("placement.allowedYawDegrees contains duplicates")

    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
        provenance = {}
    if provenance.get("status") != expected_status:
        errors.append(
            f"provenance.status must be {expected_status} in {path.parent.name}"
        )
    if provenance.get("method") not in ALLOWED_METHODS:
        errors.append("provenance.method is invalid")

    if expected_status == "candidate" and path.parent.name != component_slug:
        errors.append("candidate path must be candidates/<componentSlug>/<file>.json")

    if expected_status == "approved":
        if path.name != f"{component_slug}.json":
            errors.append("approved filename must be <componentSlug>.json")
        if scale_status != "real-world":
            errors.append("approved asset.scaleStatus must be real-world")
        if runtime_unit != "meter":
            errors.append("approved runtime unit must be meter")
        if origin_reference == "unknown":
            errors.append("approved origin.targetReference cannot be unknown")
        if origin_normalized is not True:
            errors.append("approved origin.normalized must be true")
        if orientation.get("normalized") is not True:
            errors.append("approved orientation.normalized must be true")
        if provenance.get("method") == "projected-2d":
            errors.append("projected-2d metadata cannot be approved")

    return errors


def main() -> int:
    failures = 0
    checked = 0

    try:
        schema = load_json(SCHEMA_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load schema: {exc}")
        return 1
    if schema.get("$id") is None:
        print("ERROR: schema is missing $id")
        return 1

    try:
        pin_catalog = load_json(PIN_CATALOG_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load pin catalog: {exc}")
        return 1
    if not isinstance(pin_catalog, dict):
        print("ERROR: pin catalog root must be an object")
        return 1

    for directory_name, expected_status in EXPECTED_STATUS.items():
        directory = METADATA_ROOT / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            checked += 1
            try:
                data = load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                failures += 1
                print(f"FAIL {path.relative_to(REPO_ROOT)}")
                print(f"  - invalid JSON: {exc}")
                continue

            errors = validate_metadata(path, data, expected_status, pin_catalog)
            if errors:
                failures += 1
                print(f"FAIL {path.relative_to(REPO_ROOT)}")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"PASS {path.relative_to(REPO_ROOT)}")

    if checked == 0:
        print("ERROR: no component metadata JSON files were found")
        return 1
    if failures:
        print(f"\n{failures} of {checked} metadata files failed validation")
        return 1

    print(f"\nAll {checked} component metadata files passed validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
