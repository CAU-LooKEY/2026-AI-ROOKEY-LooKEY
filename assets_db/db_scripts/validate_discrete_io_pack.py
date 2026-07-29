"""Validate the LED, resistor, and input-component 3D asset pack."""

from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GLB_DIR = ROOT / "assets_db" / "3d_models" / "glb"
METADATA_DIR = ROOT / "assets_db" / "3d_models" / "component_metadata" / "candidates"
RULES_PATH = ROOT / "assets_db" / "3d_models" / "placement_rules" / "discrete-io-pack.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def glb_nodes(path: Path) -> set[str]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise AssertionError(f"{path.name}: invalid GLB magic")
    _, version, total_length = struct.unpack_from("<4sII", data, 0)
    if version != 2 or total_length != len(data):
        raise AssertionError(f"{path.name}: invalid GLB header")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A:
        raise AssertionError(f"{path.name}: first chunk is not JSON")
    document = json.loads(data[20 : 20 + chunk_length].decode("utf-8").rstrip(" \0"))
    return {node.get("name") for node in document.get("nodes", []) if node.get("name")}


def metadata(slug: str) -> dict:
    return load_json(METADATA_DIR / slug / "metadata.json")


def pin_map(data: dict) -> dict[str, dict]:
    return {pin["pinKey"]: pin for pin in data["pins"]}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_component(slug: str, expected_pins: set[str]) -> None:
    data = metadata(slug)
    pins = pin_map(data)
    require(set(pins) == expected_pins, f"{slug}: unexpected pin set")
    nodes = glb_nodes(GLB_DIR / f"{slug}.glb")
    missing_nodes = {pin["nodeName"] for pin in pins.values()} - nodes
    require(not missing_nodes, f"{slug}: missing GLB pin nodes {sorted(missing_nodes)}")
    for pin in pins.values():
        require(pin["mounting"]["breadboardCompatible"], f"{slug}:{pin['pinKey']} is not breadboard compatible")
        require(pin["connector"]["diameterMillimeter"] <= 0.64, f"{slug}:{pin['pinKey']} is wider than 0.64 mm")
        require(pin["outwardDirection"] == [0, -1, 0], f"{slug}:{pin['pinKey']} has the wrong insertion direction")


def main() -> None:
    validate_component("led-5mm-blue", {"ANODE", "CATHODE"})
    validate_component("led-rgb-5mm", {"RED", "COMMON_CATHODE", "GREEN", "BLUE"})
    validate_component("potentiometer-10k", {"CCW", "WIPER", "CW"})
    validate_component("slide-switch-spdt", {"THROW_A", "COMMON", "THROW_B"})

    red = pin_map(metadata("led-5mm-red"))
    require(set(red) == {"ANODE", "CATHODE"}, "red LED pin set is invalid")
    require(red["ANODE"]["position"][0] > red["CATHODE"]["position"][0], "red LED polarity anchors are reversed")
    require("long-leg" in red["ANODE"]["electrical"]["aliases"], "red LED anode is not identified as the long lead")

    resistor = metadata("resistor-220-ohm")
    resistor_pins = pin_map(resistor)
    span_mm = abs(resistor_pins["LEAD_B"]["position"][0] - resistor_pins["LEAD_A"]["position"][0]) * 1000
    require(abs(span_mm - 10.16) < 0.01, "220 ohm resistor must span four 2.54 mm grid intervals")
    require(any("non-polarized" in note.lower() for note in resistor["notes"]), "resistor polarity note is missing")

    button = metadata("pushbutton-6x6")
    button_pins = pin_map(button)
    require("A2" in button_pins["A1"]["notes"][0], "pushbutton A-side common contact is missing")
    require("B2" in button_pins["B1"]["notes"][0], "pushbutton B-side common contact is missing")
    require(any("pressing" in note.lower() for note in button["notes"]), "pushbutton pressed-state contact rule is missing")

    rules = load_json(RULES_PATH)
    expected_rules = {"led-5mm-blue", "led-rgb-5mm", "potentiometer-10k", "slide-switch-spdt"}
    require(set(rules["components"]) == expected_rules, "placement rule component set is incomplete")
    for slug, rule in rules["components"].items():
        require(rule["pitchMillimeter"] == 2.54, f"{slug}: grid pitch must be 2.54 mm")
        require(rule["occupiedColumns"] > 0 and rule["occupiedRows"] > 0, f"{slug}: occupancy is invalid")

    print("Discrete I/O pack validation passed (8 components, GLB anchors, polarity, contacts, and occupancy).")


if __name__ == "__main__":
    main()
