from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = REPO_ROOT / "assets_db/3d_models/glb/breadboard-half.glb"
METADATA_PATH = (
    REPO_ROOT
    / "assets_db/3d_models/component_metadata/candidates/breadboard-half"
    / "quality1435-blender-empty.json"
)
LAYOUT_PATH = (
    REPO_ROOT
    / "assets_db/db_scripts/breadboard_layouts/breadboard-half-layout.json"
)
JUMPER_SPEC_PATH = (
    REPO_ROOT
    / "assets_db/db_scripts/jumper_connectors/breadboard-half-jumper-fit.json"
)

POSITION_TOLERANCE_METER = 2e-7
SOCKET_OPENING_MM = 0.723666
SOCKET_INSERTION_DEPTH_MM = 7.09568
JUMPER_MALE_PIN_MM = 0.64
EXPECTED_PIN_NAMES = {
    f"pin_{row}{column}"
    for row in "ABCDEFGHIJ"
    for column in range(1, 31)
}
EXPECTED_RAIL_PIN_NAMES = {
    f"pin_RAIL_{rail_name}_S{segment}_{hole}"
    for rail_name in ("TOP_POS", "TOP_NEG", "BOTTOM_POS", "BOTTOM_NEG")
    for segment in range(1, 6)
    for hole in range(1, 6)
}
EXPECTED_PIN_NAMES |= EXPECTED_RAIL_PIN_NAMES


def load_glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError("invalid GLB 2.0 header or declared length")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("first GLB chunk is not JSON")
    return json.loads(raw[20 : 20 + json_length])


def close_vector(left: list[float], right: list[float]) -> bool:
    return all(
        math.isclose(a, b, rel_tol=0, abs_tol=POSITION_TOLERANCE_METER)
        for a, b in zip(left, right, strict=True)
    )


def main() -> int:
    errors: list[str] = []
    gltf = load_glb_json(GLB_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    jumper_spec = json.loads(JUMPER_SPEC_PATH.read_text(encoding="utf-8"))

    nodes_by_name = {
        node["name"]: node
        for node in gltf.get("nodes", [])
        if isinstance(node.get("name"), str)
    }
    glb_pin_names = {
        name for name in nodes_by_name if name.startswith("pin_")
    }
    metadata_by_node = {
        pin["nodeName"]: pin for pin in metadata.get("pins", [])
    }

    if glb_pin_names != EXPECTED_PIN_NAMES:
        errors.append(
            "GLB pin node set differs from the expected 400 terminal/rail nodes"
        )
    if set(metadata_by_node) != EXPECTED_PIN_NAMES:
        errors.append(
            "metadata pin node set differs from the expected 400 terminal/rail nodes"
        )

    for node_name in sorted(EXPECTED_PIN_NAMES):
        glb_node = nodes_by_name.get(node_name)
        metadata_pin = metadata_by_node.get(node_name)
        if glb_node is None or metadata_pin is None:
            continue
        translation = glb_node.get("translation", [0, 0, 0])
        if not close_vector(translation, metadata_pin["position"]):
            errors.append(
                f"{node_name} metadata position does not match GLB translation"
            )
        if metadata_pin["outwardDirection"] != [0, 1, 0]:
            errors.append(f"{node_name} outwardDirection must be runtime +Y")
        if metadata_pin["connector"]["diameterMillimeter"] != SOCKET_OPENING_MM:
            errors.append(f"{node_name} socket opening measurement is missing")
        if (
            metadata_pin["mounting"]["insertionDepthMillimeter"]
            != SOCKET_INSERTION_DEPTH_MM
        ):
            errors.append(f"{node_name} insertion-depth measurement is missing")

    runtime = layout["terminal_runtime"]
    if runtime["columns"]["x_pitch_meter"] != 0.00254:
        errors.append("terminal X pitch is not 2.54 mm")
    if len(layout["electrical_connectivity"]["terminal_groups"]) != 60:
        errors.append("expected 60 terminal connectivity groups")
    terminal_groups = layout["electrical_connectivity"]["terminal_groups"]
    if any(len(group["holes"]) != 5 for group in terminal_groups):
        errors.append("every terminal connectivity group must contain 5 holes")
    if len(layout["electrical_connectivity"]["rail_groups"]) != 20:
        errors.append("expected 20 isolated rail segments")
    rail_groups = layout["electrical_connectivity"]["rail_groups"]
    if any(len(group["holes"]) != 5 for group in rail_groups):
        errors.append("every rail connectivity group must contain 5 holes")

    expected_hash = metadata["asset"]["sha256"]
    actual_hash = hashlib.sha256(GLB_PATH.read_bytes()).hexdigest()
    if expected_hash != actual_hash:
        errors.append("metadata SHA-256 does not match breadboard-half.glb")

    mesh_accessor = gltf["accessors"][
        gltf["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    ]
    size = [
        maximum - minimum
        for minimum, maximum in zip(
            mesh_accessor["min"], mesh_accessor["max"], strict=True
        )
    ]
    expected_size = [0.08300995081663132, 0.009509995579719543, 0.05607999861240387]
    if not close_vector(size, expected_size):
        errors.append("GLB mesh bounds differ from the recorded measured bounds")

    socket = jumper_spec["breadboard_socket"]
    male = jumper_spec["jumper_male"]
    fit = jumper_spec["fit_check"]
    if socket["insertion_axis_runtime"] != [0, -1, 0]:
        errors.append("jumper insertion axis must point into the board at runtime -Y")
    if socket["opening_width_mm"] != SOCKET_OPENING_MM:
        errors.append("jumper spec socket width differs from Blender measurement")
    if socket["usable_depth_mm"] != SOCKET_INSERTION_DEPTH_MM:
        errors.append("jumper spec socket depth differs from Blender measurement")
    if male["pin_width_mm"] != JUMPER_MALE_PIN_MM:
        errors.append("jumper male profile must be 0.64 mm square")
    if not fit["male_profile_fits_opening"]:
        errors.append("0.64 mm male jumper profile does not fit measured opening")

    if errors:
        print("FAIL breadboard-half candidate")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS breadboard-half candidate")
    print("  - GLB nodes: 402 total, 400 pin Empty nodes")
    print("  - Metadata pins: 400, exact node/position match")
    print("  - Terminal groups: 60 groups of 5 holes")
    print("  - Rail split groups: 20 groups of 5 holes")
    print("  - Socket opening/depth: 0.723666 mm square / 7.09568 mm")
    print("  - Jumper fit: 0.64 mm square male pin, runtime insertion axis -Y")
    print("  - Bounds: 83.01 x 9.51 x 56.08 mm in runtime X/Y/Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
