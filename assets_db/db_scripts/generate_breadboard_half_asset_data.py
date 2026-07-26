from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = REPO_ROOT / "assets_db"
GLB_PATH = ASSETS_ROOT / "3d_models" / "glb" / "breadboard-half.glb"
PIN_PATH = (
    ASSETS_ROOT
    / "db_scripts"
    / "pin_coordinates"
    / "breadboard-half-pin-coordinates.json"
)
LAYOUT_PATH = (
    ASSETS_ROOT
    / "db_scripts"
    / "breadboard_layouts"
    / "breadboard-half-layout.json"
)
CATALOG_PATH = ASSETS_ROOT / "db_scripts" / "all_component_pin_coordinates.json"
MANIFEST_PATH = ASSETS_ROOT / "3d_models" / "glb_model_manifest.json"
METADATA_PATH = (
    ASSETS_ROOT
    / "3d_models"
    / "component_metadata"
    / "candidates"
    / "breadboard-half"
    / "quality1435-blender-empty.json"
)
ANCHOR_PATH = (
    ASSETS_ROOT
    / "3d_models"
    / "pin_anchors"
    / "breadboard-half-3d-pin-anchors.json"
)
ALL_ANCHORS_PATH = (
    ASSETS_ROOT / "3d_models" / "pin_anchors" / "all_3d_pin_anchors.json"
)
JUMPER_SPEC_PATH = (
    ASSETS_ROOT
    / "db_scripts"
    / "jumper_connectors"
    / "breadboard-half-jumper-fit.json"
)

X_START_MM = -37.495
PITCH_MM = 2.54
SOCKET_OPENING_MM = 0.723666
SOCKET_INSERTION_DEPTH_MM = 7.09568
JUMPER_MALE_PIN_MM = 0.64
ROW_Y_MM = {
    "A": 14.725,
    "B": 12.185,
    "C": 9.645,
    "D": 7.105,
    "E": 4.565,
    "F": -3.235,
    "G": -5.775,
    "H": -8.315,
    "I": -10.855,
    "J": -13.395,
}
ROW_Y_PX = {
    "A": 69.2,
    "B": 79.7,
    "C": 90.1,
    "D": 100.6,
    "E": 110.9,
    "F": 142.0,
    "G": 152.1,
    "H": 162.9,
    "I": 173.1,
    "J": 183.8,
}
X_START_PX = 32.1
X_PITCH_PX = 10.45
RAIL_X_START_MM = -36.225
RAIL_HOLE_PITCH_MM = 2.54
RAIL_SEGMENT_PITCH_MM = 15.24
RAIL_Y_MM = {
    "TOP_POS": 24.690,
    "TOP_NEG": 22.150,
    "BOTTOM_POS": -20.820,
    "BOTTOM_NEG": -23.360,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def terminal_pin_records() -> list[dict]:
    records = []
    for row_index, row in enumerate(ROW_Y_MM):
        bank = "upper" if row <= "E" else "lower"
        for column in range(1, 31):
            x_mm = X_START_MM + (column - 1) * PITCH_MM
            y_mm = ROW_Y_MM[row]
            pin_key = f"{row}{column}"
            records.append(
                {
                    "pin_key": pin_key,
                    "label": pin_key,
                    "signal_type": "component",
                    "side": "center",
                    "x_px": round(
                        X_START_PX + (column - 1) * X_PITCH_PX, 4
                    ),
                    "y_px": ROW_Y_PX[row],
                    "aliases": [],
                    "notes": (
                        f"Procedural terminal hole; electrically common with "
                        f"{bank} bank column {column}."
                    ),
                    "sort_order": 100 + row_index * 30 + column - 1,
                    "runtime": {
                        "node_name": f"pin_{pin_key}",
                        "position_meter": [
                            round(x_mm / 1000, 9),
                            0,
                            round(-y_mm / 1000, 9),
                        ],
                        "outward_direction": [0, 1, 0],
                    },
                }
            )
    return records


def metadata_pin_records() -> list[dict]:
    records = []
    for row, y_mm in ROW_Y_MM.items():
        bank = "AE" if row <= "E" else "FJ"
        for column in range(1, 31):
            x_mm = X_START_MM + (column - 1) * PITCH_MM
            pin_key = f"{row}{column}"
            records.append(
                {
                    "pinKey": pin_key,
                    "label": pin_key,
                    "nodeName": f"pin_{pin_key}",
                    "position": [
                        round(x_mm / 1000, 9),
                        0,
                        round(-y_mm / 1000, 9),
                    ],
                    "outwardDirection": [0, 1, 0],
                    "connector": {
                        "gender": "female",
                        "form": "hole",
                        "pitchMillimeter": PITCH_MM,
                        "diameterMillimeter": SOCKET_OPENING_MM,
                    },
                    "electrical": {
                        "role": "passive",
                        "aliases": [f"terminal-{bank}-{column}"],
                    },
                    "mounting": {
                        "breadboardCompatible": True,
                        "insertionDepthMillimeter": SOCKET_INSERTION_DEPTH_MM,
                    },
                    "confidence": 0.95,
                    "sourceObject": f"pin_{pin_key}",
                    "notes": [
                        "Position is duplicated from the exported Blender Empty.",
                        (
                            f"Internally common with rows "
                            f"{'A-E' if row <= 'E' else 'F-J'} at column {column}."
                        ),
                    ],
                }
            )
    for rail_name, y_mm in RAIL_Y_MM.items():
        role = "power" if rail_name.endswith("POS") else "ground"
        for segment in range(1, 6):
            group_alias = (
                f"rail-{rail_name.lower().replace('_', '-')}-segment-{segment}"
            )
            for hole in range(1, 6):
                x_mm = (
                    RAIL_X_START_MM
                    + (segment - 1) * RAIL_SEGMENT_PITCH_MM
                    + (hole - 1) * RAIL_HOLE_PITCH_MM
                )
                pin_key = f"RAIL_{rail_name}_S{segment}_{hole}"
                records.append(
                    {
                        "pinKey": pin_key,
                        "label": pin_key,
                        "nodeName": f"pin_{pin_key}",
                        "position": [
                            round(x_mm / 1000, 9),
                            0,
                            round(-y_mm / 1000, 9),
                        ],
                        "outwardDirection": [0, 1, 0],
                        "connector": {
                            "gender": "female",
                            "form": "hole",
                            "pitchMillimeter": RAIL_HOLE_PITCH_MM,
                            "diameterMillimeter": SOCKET_OPENING_MM,
                        },
                        "electrical": {
                            "role": role,
                            "aliases": [group_alias],
                        },
                        "mounting": {
                            "breadboardCompatible": True,
                            "insertionDepthMillimeter": SOCKET_INSERTION_DEPTH_MM,
                        },
                        "confidence": 0.95,
                        "sourceObject": f"pin_{pin_key}",
                        "notes": [
                            "Position is duplicated from the exported Blender Empty.",
                            (
                                f"Internally common with the other holes in "
                                f"{group_alias} only."
                            ),
                        ],
                    }
                )
    return records


def update_pin_coordinates() -> None:
    data = read_json(PIN_PATH)
    representative_keys = {
        "RAIL_TOP_POS",
        "RAIL_TOP_NEG",
        "RAIL_BOTTOM_POS",
        "RAIL_BOTTOM_NEG",
        "A1",
        "E1",
        "F1",
        "J1",
    }
    representative_pins = [
        pin
        for pin in data["pins"]
        if pin["pin_key"] in representative_keys
    ]
    representative_pins.sort(
        key=lambda pin: [
            "RAIL_TOP_POS",
            "RAIL_TOP_NEG",
            "RAIL_BOTTOM_POS",
            "RAIL_BOTTOM_NEG",
            "A1",
            "E1",
            "F1",
            "J1",
        ].index(pin["pin_key"])
    )
    for pin in representative_pins:
        pin_key = pin["pin_key"]
        if pin_key.startswith("RAIL_"):
            pin.pop("runtime", None)
            continue
        row = pin_key[0]
        column = int(pin_key[1:])
        x_mm = X_START_MM + (column - 1) * PITCH_MM
        y_mm = ROW_Y_MM[row]
        pin["runtime"] = {
            "node_name": f"pin_{pin_key}",
            "position_meter": [
                round(x_mm / 1000, 9),
                0,
                round(-y_mm / 1000, 9),
            ],
            "outward_direction": [0, 1, 0],
        }
    data["description"] = (
        "Representative Half Breadboard anchors plus a procedural runtime rule. "
        "The 300 GLB Empty nodes remain the coordinate source of truth."
    )
    data["runtime_procedural"] = {
        "space": "gltf-model-local",
        "unit": "meter",
        "columns": {
            "count": 30,
            "x_start_meter": X_START_MM / 1000,
            "x_pitch_meter": PITCH_MM / 1000,
            "formula": "x = x_start_meter + (column - 1) * x_pitch_meter",
        },
        "rows_z_meter": {
            row: round(-y_mm / 1000, 9)
            for row, y_mm in ROW_Y_MM.items()
        },
        "surface_y_meter": 0,
        "outward_direction": [0, 1, 0],
        "node_name_formula": "pin_{ROW}{COLUMN}",
    }
    data["rail_runtime"] = {
        "space": "gltf-model-local",
        "unit": "meter",
        "rows_z_meter": {
            rail_name: round(-y_mm / 1000, 9)
            for rail_name, y_mm in RAIL_Y_MM.items()
        },
        "segments_per_row": 5,
        "holes_per_segment": 5,
        "x_start_meter": RAIL_X_START_MM / 1000,
        "hole_pitch_meter": RAIL_HOLE_PITCH_MM / 1000,
        "segment_pitch_meter": RAIL_SEGMENT_PITCH_MM / 1000,
        "formula": (
            "x = x_start_meter + (segment - 1) * segment_pitch_meter "
            "+ (hole - 1) * hole_pitch_meter"
        ),
        "surface_y_meter": 0,
        "outward_direction": [0, 1, 0],
        "node_name_formula": "pin_RAIL_{RAIL_NAME}_S{SEGMENT}_{HOLE}",
    }
    representative_rail_map = {
        "RAIL_TOP_POS": "TOP_POS",
        "RAIL_TOP_NEG": "TOP_NEG",
        "RAIL_BOTTOM_POS": "BOTTOM_POS",
        "RAIL_BOTTOM_NEG": "BOTTOM_NEG",
    }
    for pin in representative_pins:
        rail_name = representative_rail_map.get(pin["pin_key"])
        if rail_name is None:
            continue
        pin["runtime"] = {
            "node_name": f"pin_RAIL_{rail_name}_S1_1",
            "position_meter": [
                RAIL_X_START_MM / 1000,
                0,
                round(-RAIL_Y_MM[rail_name] / 1000, 9),
            ],
            "outward_direction": [0, 1, 0],
        }
    data["pins"] = representative_pins
    data["notes"] = [
        "GLB Empty nodes are the source of truth; runtime JSON values are distribution copies.",
        "Terminal pitch is 2.54 mm. E-F is separated by the center trench.",
        "Do not materialize A1-J30 as ordinary catalog rows; use runtime_procedural.",
        "Rail entries are representative; rail_runtime generates all 100 rail socket nodes.",
    ]
    write_json(PIN_PATH, data)


def update_catalog(pin_coordinate_data: dict) -> None:
    catalog = read_json(CATALOG_PATH)
    catalog["breadboard-half"] = pin_coordinate_data
    write_json(CATALOG_PATH, catalog)


def update_layout() -> None:
    data = read_json(LAYOUT_PATH)
    data["hole_coordinate_system"] = "runtime-meter-procedural"
    data["terminal_runtime"] = {
        "space": "gltf-model-local",
        "unit": "meter",
        "up_axis": "+Y",
        "front_axis": "+Z",
        "columns": {
            "count": 30,
            "x_start_meter": X_START_MM / 1000,
            "x_pitch_meter": PITCH_MM / 1000,
            "formula": "x = x_start_meter + (column - 1) * x_pitch_meter",
        },
        "rows_z_meter": {
            row: round(-y_mm / 1000, 9)
            for row, y_mm in ROW_Y_MM.items()
        },
        "surface_y_meter": 0,
        "outward_direction": [0, 1, 0],
    }
    data["electrical_connectivity"] = {
        "terminal_groups": [
            {
                "group_id": f"terminal-ae-{column}",
                "holes": [f"{row}{column}" for row in "ABCDE"],
            }
            for column in range(1, 31)
        ]
        + [
            {
                "group_id": f"terminal-fj-{column}",
                "holes": [f"{row}{column}" for row in "FGHIJ"],
            }
            for column in range(1, 31)
        ],
        "rail_groups": [
            {
                "group_id": (
                    f"rail-{rail_name.lower().replace('_', '-')}"
                    f"-segment-{segment}"
                ),
                "rail": rail_name,
                "segment_index": segment,
                "holes": [
                    f"RAIL_{rail_name}_S{segment}_{hole}"
                    for hole in range(1, 6)
                ],
            }
            for rail_name in RAIL_Y_MM
            for segment in range(1, 6)
        ],
        "rail_split_policy": (
            "Each five-hole segment is internally connected. "
            "Different segments and different +/- rows are electrically isolated."
        ),
    }
    data["notes"] = [
        "A1, E1, F1, and J1 were measured on the normalized GLB.",
        "A2 verified the 2.54 mm X pitch; D17, H23, and J30 were visually checked against actual hole centers.",
        "Each power-rail row contains five isolated segments of five holes, measured on the normalized GLB.",
    ]
    write_json(LAYOUT_PATH, data)


def write_metadata(pins: list[dict], sha256: str) -> None:
    metadata = {
        "schemaVersion": "1.0.0",
        "componentSlug": "breadboard-half",
        "asset": {
            "path": "assets_db/3d_models/glb/breadboard-half.glb",
            "sha256": sha256,
            "format": "glb",
            "scaleStatus": "real-world",
            "thumbnailPath": "assets_db/2d_svgs/raster_sources/breadboard-half-top.png",
        },
        "physicalDimensions": {
            "unit": "millimeter",
            "width": 83.01,
            "depth": 56.08,
            "height": 9.51,
            "measurementScope": "overall-including-pins",
            "source": "measured",
            "confidence": 0.95,
        },
        "coordinateSystems": {
            "authoring": {
                "space": "blender-object-local",
                "handedness": "right",
                "upAxis": "+Z",
                "frontAxis": "-Y",
                "unit": "millimeter",
            },
            "runtime": {
                "space": "gltf-model-local",
                "handedness": "right",
                "upAxis": "+Y",
                "frontAxis": "+Z",
                "unit": "meter",
                "modelUnitsPerMillimeter": 0.001,
            },
            "anchorsStoredIn": "runtime",
        },
        "origin": {
            "targetReference": "mounting-surface-center",
            "referencePoint": [0, 0, 0],
            "normalized": True,
            "description": (
                "Origin is the center of the top insertion surface. The board "
                "body extends toward runtime -Y."
            ),
        },
        "orientation": {
            "defaultRotationQuaternion": [0, 0, 0, 1],
            "normalized": True,
            "markers": [
                {
                    "key": "a1-left",
                    "pinKey": "A1",
                    "direction": "-X",
                    "description": "A1 is at the left end of the upper terminal bank.",
                },
                {
                    "key": "j1-front-left",
                    "pinKey": "J1",
                    "direction": "+Z",
                    "description": "J1 marks the front-left terminal hole.",
                },
            ],
        },
        "pins": pins,
        "placement": {
            "mountingType": "fixed",
            "mountingPlaneNormal": [0, 1, 0],
            "rotationPolicy": "snap-yaw",
            "allowedYawDegrees": [0, 90, 180, 270],
            "keepOutMarginMillimeter": 0,
        },
        "provenance": {
            "authorGithub": "quality1435",
            "branch": "feat/asset-breadboard-jumper",
            "method": "blender-empty",
            "sourceTool": (
                "GrabCAD Half Breadboard STEP; converted through Bambu Studio; "
                "normalized in Blender 5.2 LTS"
            ),
            "createdAt": "2026-07-24",
            "status": "candidate",
            "reviewerGithub": None,
            "approvedAt": None,
        },
        "notes": [
            "Candidate GLB contains 400 Empty nodes: 300 terminal holes and 100 rail holes.",
            "Local +Y of every Empty exports as runtime +Y, away from the insertion surface.",
            (
                "Socket opening is a measured square "
                f"{SOCKET_OPENING_MM:.6f} x {SOCKET_OPENING_MM:.6f} mm; "
                "diameterMillimeter stores one side for schema compatibility."
            ),
            (
                "Usable modeled socket depth measured from the insertion surface is "
                f"{SOCKET_INSERTION_DEPTH_MM:.5f} mm."
            ),
            (
                "Upstream model: https://grabcad.com/library/half-breadboard-1"
            ),
            (
                "License status: GrabCAD states Library models are free for "
                "personal use, but this model page exposes no explicit "
                "redistribution or commercial license; approval requires review."
            ),
            "Power rails use five isolated five-hole segments per row.",
        ],
    }
    write_json(METADATA_PATH, metadata)


def write_jumper_fit_spec() -> None:
    clearance = SOCKET_OPENING_MM - JUMPER_MALE_PIN_MM
    spec = {
        "schema_version": "1.0.0",
        "component_slug": "breadboard-half",
        "status": "candidate",
        "coordinate_system": {
            "handedness": "right",
            "up_axis": "+Y",
            "front_axis": "+Z",
            "unit": "millimeter",
        },
        "breadboard_socket": {
            "gender": "female",
            "shape": "square",
            "opening_width_mm": SOCKET_OPENING_MM,
            "opening_height_mm": SOCKET_OPENING_MM,
            "usable_depth_mm": SOCKET_INSERTION_DEPTH_MM,
            "pitch_mm": PITCH_MM,
            "outward_axis_runtime": [0, 1, 0],
            "insertion_axis_runtime": [0, -1, 0],
            "measurement_source": "normalized GLB geometry measured in Blender 5.2 LTS",
        },
        "jumper_male": {
            "gender": "male",
            "shape": "square",
            "pin_width_mm": JUMPER_MALE_PIN_MM,
            "pin_height_mm": JUMPER_MALE_PIN_MM,
            "mating_axis_local": [0, -1, 0],
            "maximum_modeled_insertion_mm": SOCKET_INSERTION_DEPTH_MM,
            "dimension_basis": (
                "Molex PS-10-07-001 and Amphenol BergStik official "
                "documentation for 2.54 mm pitch, 0.64 mm square pins"
            ),
            "dimension_source_url": (
                "https://www.molex.com/content/dam/molex/molex-dot-com/"
                "products/automated/en-us/productspecificationpdf/100/1007/"
                "PS-10-07-001.pdf"
            ),
        },
        "jumper_female": {
            "gender": "female",
            "accepted_mating_pin_shape": "square",
            "accepted_mating_pin_width_mm": JUMPER_MALE_PIN_MM,
            "pitch_mm": PITCH_MM,
            "breadboard_direct_fit": False,
            "reason": (
                "The breadboard socket and a female jumper end are both female; "
                "a male pin is required between them."
            ),
            "dimension_basis": (
                "Harwin M20-1160042 official product data: straight female "
                "receptacle for 0.64 mm square mating pins at 2.54 mm pitch"
            ),
            "dimension_source_url": (
                "https://www.harwin.com/products/M20-1160042"
            ),
        },
        "fit_check": {
            "profile_clearance_total_mm": round(clearance, 6),
            "profile_clearance_each_side_mm": round(clearance / 2, 6),
            "male_profile_fits_opening": clearance > 0,
            "depth_condition": (
                "The exposed male pin length inserted into the asset must not "
                f"exceed {SOCKET_INSERTION_DEPTH_MM:.5f} mm."
            ),
            "result": "pass",
            "limitations": [
                "This is a geometry fit check, not a spring-contact force test.",
                "The source STEP mesh does not model metal spring contacts.",
                "Physical fit still requires comparison with the selected real jumper part.",
            ],
        },
    }
    write_json(JUMPER_SPEC_PATH, spec)


def write_legacy_anchor_exports(pins: list[dict]) -> None:
    bounds = {
        "min": [
            -0.04150497540831566,
            -0.009509995579719543,
            -0.028040006756782532,
        ],
        "max": [
            0.04150497540831566,
            0,
            0.028039991855621338,
        ],
        "size": [
            0.08300995081663132,
            0.009509995579719543,
            0.05607999861240387,
        ],
    }
    representative_pin_keys = {"A1", "E1", "F1", "J1"}
    anchor_pins = [
        {
            "pin_key": pin["pinKey"],
            "label": pin["label"],
            "x_3d": pin["position"][0],
            "y_3d": pin["position"][1],
            "z_3d": pin["position"][2],
            "model_anchor_name": pin["nodeName"],
            "source": "blender-empty",
        }
        for pin in pins
        if pin["pinKey"] in representative_pin_keys
    ]
    representative_rail_keys = {
        "RAIL_TOP_POS": "RAIL_TOP_POS_S1_1",
        "RAIL_TOP_NEG": "RAIL_TOP_NEG_S1_1",
        "RAIL_BOTTOM_POS": "RAIL_BOTTOM_POS_S1_1",
        "RAIL_BOTTOM_NEG": "RAIL_BOTTOM_NEG_S1_1",
    }
    metadata_by_key = {pin["pinKey"]: pin for pin in pins}
    for representative_key, metadata_key in representative_rail_keys.items():
        pin = metadata_by_key[metadata_key]
        anchor_pins.append(
            {
                "pin_key": representative_key,
                "label": representative_key,
                "x_3d": pin["position"][0],
                "y_3d": pin["position"][1],
                "z_3d": pin["position"][2],
                "model_anchor_name": pin["nodeName"],
                "source": "blender-empty",
            }
        )
    component_export = {
        "component_slug": "breadboard-half",
        "display_name": "Half-size Breadboard",
        "model_storage_path": "3d_models/glb/breadboard-half.glb",
        "model_bounds": bounds,
        "method": "blender-empty",
        "coordinate_space": "glb_model_local",
        "axis_mapping": {
            "right_axis": "+X",
            "up_axis": "+Y",
            "front_axis": "+Z",
            "unit": "meter",
            "calibration_quality": "measured_candidate",
        },
        "pins": anchor_pins,
        "notes": [
            "Compatibility export of eight measured calibration anchors.",
            "Generate A1-J30 from the breadboard layout rule or read the GLB Empty nodes.",
            "The component metadata candidate is the versioned review record.",
        ],
    }
    write_json(ANCHOR_PATH, component_export)

    aggregate = read_json(ALL_ANCHORS_PATH)
    aggregate["summary"] = [
        summary
        for summary in aggregate["summary"]
        if summary["component_slug"] != "breadboard-half"
    ]
    aggregate["summary"].append(
        {
            "component_slug": "breadboard-half",
            "pin_count": len(anchor_pins),
            "method": "blender-empty",
            "coordinate_space": "glb_model_local",
            "calibration_quality": "measured_candidate",
        }
    )
    aggregate["summary"].sort(key=lambda item: item["component_slug"])
    aggregate["anchors"] = [
        anchor
        for anchor in aggregate["anchors"]
        if anchor["slug"] != "breadboard-half"
    ]
    aggregate["anchors"].extend(
        {
            "slug": "breadboard-half",
            "pin_key": pin["pin_key"],
            "x_3d": pin["x_3d"],
            "y_3d": pin["y_3d"],
            "z_3d": pin["z_3d"],
            "model_anchor_name": pin["model_anchor_name"],
        }
        for pin in anchor_pins
    )
    write_json(ALL_ANCHORS_PATH, aggregate)


def update_manifest(sha256: str) -> None:
    manifest = read_json(MANIFEST_PATH)
    entry = next(
        item
        for item in manifest
        if item["component_slug"] == "breadboard-half"
    )
    entry.update(
        {
            "source": "breadboard-half-working.blend",
            "upstream_url": "https://grabcad.com/library/half-breadboard-1",
            "upstream_license": (
                "GrabCAD Community personal-use permission; redistribution and "
                "commercial-use permission not explicitly established"
            ),
            "audit_status": "candidate",
            "model_kind": "candidate_3d",
            "notes": (
                "Real-world Half Breadboard exported from Blender with a "
                "mounting-surface origin, 300 terminal-hole Empty nodes, and "
                "100 power-rail Empty nodes."
            ),
            "bytes": GLB_PATH.stat().st_size,
            "sha256": sha256,
            "nodes": 402,
            "meshes": 1,
            "materials": 0,
            "textures": 0,
            "images": 0,
            "extensions_used": [],
            "bounds": {
                "min": [
                    -0.04150497540831566,
                    -0.009509995579719543,
                    -0.028040006756782532,
                ],
                "max": [
                    0.04150497540831566,
                    0,
                    0.028039991855621338,
                ],
                "size": [
                    0.08300995081663132,
                    0.009509995579719543,
                    0.05607999861240387,
                ],
            },
            "unit": "meter",
        }
    )
    write_json(MANIFEST_PATH, manifest)


def main() -> None:
    sha256 = hashlib.sha256(GLB_PATH.read_bytes()).hexdigest()
    metadata_records = metadata_pin_records()

    update_pin_coordinates()
    pin_coordinate_data = read_json(PIN_PATH)
    update_catalog(pin_coordinate_data)
    update_layout()
    write_metadata(metadata_records, sha256)
    write_jumper_fit_spec()
    write_legacy_anchor_exports(metadata_records)
    update_manifest(sha256)

    print(
        "Generated Half Breadboard candidate data: "
        "procedural A1-J30 coordinates, "
        f"{len(metadata_records)} metadata pins."
    )


if __name__ == "__main__":
    main()
