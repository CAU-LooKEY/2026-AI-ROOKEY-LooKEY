from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLACEMENT_PATH = (
    REPO_ROOT
    / "assets_db/db_scripts/breadboard_layouts/arduino-nano-breadboard-placement.json"
)
BREADBOARD_LAYOUT_PATH = (
    REPO_ROOT / "assets_db/db_scripts/breadboard_layouts/breadboard-half-layout.json"
)
NANO_METADATA_PATH = (
    REPO_ROOT / "assets_db/3d_models/component_metadata/approved/arduino-nano.json"
)

EXPECTED_PIN_COUNT = 30
BOARD_COLUMN_MIN = 1
BOARD_COLUMN_MAX = 30


def main() -> int:
    errors: list[str] = []

    placement = json.loads(PLACEMENT_PATH.read_text(encoding="utf-8"))
    layout = json.loads(BREADBOARD_LAYOUT_PATH.read_text(encoding="utf-8"))
    nano_metadata = json.loads(NANO_METADATA_PATH.read_text(encoding="utf-8"))

    placements = placement["pin_placements"]
    valid_hole_addresses = {
        hole
        for group in layout["electrical_connectivity"]["terminal_groups"]
        for hole in group["holes"]
    }
    group_holes_by_id = {
        group["group_id"]: set(group["holes"])
        for group in layout["electrical_connectivity"]["terminal_groups"]
    }
    breadboard_compatible_pin_keys = {
        pin["pinKey"]
        for pin in nano_metadata["pins"]
        if pin["mounting"]["breadboardCompatible"]
    }

    # Criterion 1: every Nano pin lands on a valid, distinct hole.
    if len(placements) != EXPECTED_PIN_COUNT:
        errors.append(
            f"Expected {EXPECTED_PIN_COUNT} pin placements, found {len(placements)}"
        )

    placed_pin_keys = {p["pinKey"] for p in placements}
    if placed_pin_keys != breadboard_compatible_pin_keys:
        missing = breadboard_compatible_pin_keys - placed_pin_keys
        extra = placed_pin_keys - breadboard_compatible_pin_keys
        if missing:
            errors.append(f"Missing placements for breadboard-compatible pins: {missing}")
        if extra:
            errors.append(f"Placements exist for non breadboard-compatible pins: {extra}")

    hole_addresses = [p["holeAddress"] for p in placements]
    if len(hole_addresses) != len(set(hole_addresses)):
        duplicates = {h for h in hole_addresses if hole_addresses.count(h) > 1}
        errors.append(f"Duplicate hole addresses: {duplicates}")

    invalid_holes = [h for h in hole_addresses if h not in valid_hole_addresses]
    if invalid_holes:
        errors.append(f"Hole addresses that don't exist on the board: {invalid_holes}")

    # Criterion 2 & 3: each 5-hole terminal group is claimed by at most one
    # pin, and the A-E side never shares a group with the F-J side.
    group_ids = [p["terminalGroupId"] for p in placements]
    if len(group_ids) != len(set(group_ids)):
        duplicates = {g for g in group_ids if group_ids.count(g) > 1}
        errors.append(f"More than one pin resolves to the same terminal group: {duplicates}")

    for p in placements:
        expected_group_holes = group_holes_by_id.get(p["terminalGroupId"])
        if expected_group_holes is None:
            errors.append(f"Unknown terminal group id: {p['terminalGroupId']}")
        elif p["holeAddress"] not in expected_group_holes:
            errors.append(
                f"{p['pinKey']} hole {p['holeAddress']} is not a member of "
                f"terminal group {p['terminalGroupId']}"
            )

    ae_groups = {p["terminalGroupId"] for p in placements if p["boardRow"] == "E"}
    fj_groups = {p["terminalGroupId"] for p in placements if p["boardRow"] == "F"}
    if ae_groups & fj_groups:
        errors.append(
            f"Row E and row F share terminal groups (center groove bridged): {ae_groups & fj_groups}"
        )

    # Criterion 4: no pin falls off the edge of the 30-column board.
    out_of_bounds = [
        p["pinKey"]
        for p in placements
        if not (BOARD_COLUMN_MIN <= p["boardColumn"] <= BOARD_COLUMN_MAX)
    ]
    if out_of_bounds:
        errors.append(f"Pins placed outside the board's 30 columns: {out_of_bounds}")

    if errors:
        print("FAIL arduino-nano breadboard placement")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS arduino-nano breadboard placement")
    print(f"  - {len(placements)} pins placed, all on distinct holes")
    print(f"  - Board rows used: {sorted({p['boardRow'] for p in placements})}")
    print(
        "  - Column span: "
        f"{min(p['boardColumn'] for p in placements)}-"
        f"{max(p['boardColumn'] for p in placements)} of 30"
    )
    print(f"  - Terminal groups claimed: {len(group_ids)}, all distinct, A-E/F-J isolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
