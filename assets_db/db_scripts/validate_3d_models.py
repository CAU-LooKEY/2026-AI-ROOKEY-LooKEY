import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest_path = root / "3d_models" / "glb_model_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

for model in manifest:
    glb_path = root / model["storage_path"]
    if not glb_path.exists():
        raise SystemExit(f"Missing GLB file: {glb_path}")

    data = glb_path.read_bytes()
    if len(data) < 20:
        raise SystemExit(f"GLB too small: {glb_path}")

    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise SystemExit(f"Invalid GLB header: {glb_path}")
    if declared_length != len(data):
        raise SystemExit(f"GLB length mismatch: {glb_path}")

    size = model.get("bounds", {}).get("size", [])
    if len(size) != 3 or any(value <= 0 for value in size):
        raise SystemExit(f"Missing positive bounds.size metadata: {glb_path}")

    if model["audit_status"] == "ready" and model["bytes"] > 10 * 1024 * 1024:
        raise SystemExit(f"Ready model is over 10 MB: {glb_path}")

print(f"Validated {len(manifest)} GLB model files.")
