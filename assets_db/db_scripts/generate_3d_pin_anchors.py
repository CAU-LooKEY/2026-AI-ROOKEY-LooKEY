import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_SOURCE = ROOT / "db_scripts" / "all_component_pin_coordinates.json"
MODEL_MANIFEST = ROOT / "3d_models" / "glb_model_manifest.json"
OUT_DIR = ROOT / "3d_models" / "pin_anchors"
SQL_OUT = ROOT / "db_scripts" / "006_seed_3d_pin_anchors.sql"

AXIS_CONFIG = {
    "arduino-uno-r3": {
        "image_x_axis": "x",
        "image_y_axis": "y",
        "surface_axis": "z",
        "image_y_direction": "negative",
        "calibration_quality": "draft_projected",
    },
    "arduino-nano": {
        "image_x_axis": "x",
        "image_y_axis": "z",
        "surface_axis": "y",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "breadboard-half": {
        "image_x_axis": "x",
        "image_y_axis": "y",
        "surface_axis": "z",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "breadboard-full": {
        "image_x_axis": "x",
        "image_y_axis": "z",
        "surface_axis": "y",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "hc-sr04": {
        "image_x_axis": "x",
        "image_y_axis": "y",
        "surface_axis": "z",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "led-5mm-blue": {
        "image_x_axis": "x",
        "image_y_axis": "y",
        "surface_axis": "z",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "pushbutton-6x6": {
        "image_x_axis": "x",
        "image_y_axis": "z",
        "surface_axis": "y",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "resistor-220-ohm": {
        "image_x_axis": "y",
        "image_y_axis": "x",
        "surface_axis": "z",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
    "servo-sg90": {
        "image_x_axis": "x",
        "image_y_axis": "z",
        "surface_axis": "y",
        "image_y_direction": "positive",
        "calibration_quality": "draft_projected",
    },
}


def axis_value(bounds, axis, normalized):
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    return bounds["min"][axis_index] + normalized * bounds["size"][axis_index]


def surface_value(bounds, axis):
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    return bounds["max"][axis_index]


def project_pin(pin, component, model, config):
    x_norm = pin["x_px"] / component["pixel_width"]
    y_norm = pin["y_px"] / component["pixel_height"]
    if config["image_y_direction"] == "negative":
        y_norm = 1 - y_norm

    bounds = model["bounds"]
    coords = {
        "x": None,
        "y": None,
        "z": None,
    }
    coords[config["image_x_axis"]] = axis_value(bounds, config["image_x_axis"], x_norm)
    coords[config["image_y_axis"]] = axis_value(bounds, config["image_y_axis"], y_norm)
    coords[config["surface_axis"]] = surface_value(bounds, config["surface_axis"])

    return {
        "pin_key": pin["pin_key"],
        "label": pin["label"],
        "x_3d": round(coords["x"], 8),
        "y_3d": round(coords["y"], 8),
        "z_3d": round(coords["z"], 8),
        "model_anchor_name": f"pin_{pin['pin_key'].lower().replace('/', '_').replace('+', 'pos').replace('-', 'neg')}",
        "source_x_px": pin["x_px"],
        "source_y_px": pin["y_px"],
    }


def main():
    components = json.loads(PIN_SOURCE.read_text(encoding="utf-8"))
    models = {
        model["component_slug"]: model
        for model in json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    summary = []
    for slug, component in sorted(components.items()):
        if slug not in models or slug not in AXIS_CONFIG:
            continue

        model = models[slug]
        config = AXIS_CONFIG[slug]
        anchors = [project_pin(pin, component, model, config) for pin in component["pins"]]
        calibration = {
            "component_slug": slug,
            "display_name": component["display_name"],
            "model_storage_path": model["storage_path"],
            "model_bounds": model["bounds"],
            "method": "projected_from_2d_pin_map_to_glb_bounds",
            "coordinate_space": "glb_model_local",
            "axis_mapping": config,
            "pixel_source": {
                "width_px": component["pixel_width"],
                "height_px": component["pixel_height"],
                "origin": "top-left",
            },
            "pins": anchors,
            "notes": [
                "These are draft GLB-local anchors projected from existing 2D pin coordinates.",
                "Review in Blender or a Three.js calibration view before using for final production wire snapping.",
            ],
        }
        (OUT_DIR / f"{slug}-3d-pin-anchors.json").write_text(
            json.dumps(calibration, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary.append(
            {
                "component_slug": slug,
                "pin_count": len(anchors),
                "method": calibration["method"],
                "coordinate_space": calibration["coordinate_space"],
                "calibration_quality": config["calibration_quality"],
            }
        )
        for anchor in anchors:
            all_rows.append(
                {
                    "slug": slug,
                    "pin_key": anchor["pin_key"],
                    "x_3d": anchor["x_3d"],
                    "y_3d": anchor["y_3d"],
                    "z_3d": anchor["z_3d"],
                    "model_anchor_name": anchor["model_anchor_name"],
                }
            )

    (OUT_DIR / "all_3d_pin_anchors.json").write_text(
        json.dumps({"summary": summary, "anchors": all_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sql_rows = json.dumps(all_rows, ensure_ascii=False, indent=2)
    SQL_OUT.write_text(
        f"""-- Seed draft GLB-local 3D pin anchors.
-- These values are projected from the existing 2D pin maps onto each selected GLB model bounds.
-- They are good enough for prototype 3D wire snapping, but should be reviewed in a visual
-- calibration tool before production.

with anchor_rows as (
  select * from jsonb_to_recordset($anchors${sql_rows}$anchors$::jsonb) as x(
    slug text,
    pin_key text,
    x_3d numeric,
    y_3d numeric,
    z_3d numeric,
    model_anchor_name text
  )
)
update public.circuit_component_pins pins
set x_3d = anchor_rows.x_3d,
    y_3d = anchor_rows.y_3d,
    z_3d = anchor_rows.z_3d,
    model_anchor_name = anchor_rows.model_anchor_name,
    notes = trim(both ' ' from concat_ws(
      ' ',
      pins.notes,
      '[3D anchor: draft projected from 2D pin map to GLB bounds.]'
    )),
    updated_at = now()
from anchor_rows
join public.circuit_component_assets assets on assets.slug = anchor_rows.slug
where pins.component_id = assets.id
  and pins.pin_key = anchor_rows.pin_key;
""",
        encoding="utf-8",
    )

    print(f"Wrote {len(all_rows)} 3D pin anchors for {len(summary)} components.")


if __name__ == "__main__":
    main()
