import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_DIR = ROOT / "3d_models" / "pin_anchors"
MODEL_MANIFEST = ROOT / "3d_models" / "glb_model_manifest.json"

models = {
    model["component_slug"]: model
    for model in json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
}

files = sorted(ANCHOR_DIR.glob("*-3d-pin-anchors.json"))
if not files:
    raise SystemExit("No 3D pin anchor files found. Run generate_3d_pin_anchors.py first.")

count = 0
for path in files:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data["component_slug"]
    if slug not in models:
        raise SystemExit(f"No GLB manifest row for {slug}")
    bounds = models[slug]["bounds"]
    mins = bounds["min"]
    maxs = bounds["max"]

    for pin in data["pins"]:
        coords = [pin["x_3d"], pin["y_3d"], pin["z_3d"]]
        for index, value in enumerate(coords):
            if value < mins[index] - 1e-6 or value > maxs[index] + 1e-6:
                raise SystemExit(f"{slug}/{pin['pin_key']} 3D coordinate is outside model bounds")
        count += 1

print(f"Validated {count} 3D pin anchors across {len(files)} components.")
