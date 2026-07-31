from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = REPO_ROOT / "assets_db"
NANO_METADATA_PATH = (
    ASSETS_ROOT
    / "3d_models"
    / "component_metadata"
    / "approved"
    / "arduino-nano.json"
)
BREADBOARD_LAYOUT_PATH = (
    ASSETS_ROOT / "db_scripts" / "breadboard_layouts" / "breadboard-half-layout.json"
)
OUTPUT_PATH = (
    ASSETS_ROOT
    / "db_scripts"
    / "breadboard_layouts"
    / "arduino-nano-breadboard-placement.json"
)

BOARD_SLUG = "breadboard-half"
COMPONENT_SLUG = "arduino-nano"

# Nano's two 15-pin header rows are separated 15.24 mm apart along local X.
# The board's own A-J span (measured, see breadboard-half-layout.json
# terminal_runtime.rows_z_meter) doesn't contain a row pair exactly 15.24 mm
# apart; the closest literal "straddle the center groove" placement is the
# pair of rows immediately adjacent to the trough, E and F.
ROW_X_TO_BOARD_ROW = {
    -0.00762: "E",
    0.00762: "F",
}
START_COLUMN = 8
PIN_COLUMN_SPAN = 15


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def breadboard_compatible_pins(nano_metadata: dict) -> list[dict]:
    return [
        pin
        for pin in nano_metadata["pins"]
        if pin["mounting"]["breadboardCompatible"]
    ]


def group_pins_by_header_row(pins: list[dict]) -> dict[float, list[dict]]:
    groups: dict[float, list[dict]] = {x: [] for x in ROW_X_TO_BOARD_ROW}
    for pin in pins:
        x = round(pin["position"][0], 5)
        if x not in groups:
            raise ValueError(
                f"Pin {pin['pinKey']} has unexpected header-row x={x}; "
                f"expected one of {list(ROW_X_TO_BOARD_ROW)}."
            )
        groups[x].append(pin)
    return groups


def find_terminal_group_id(terminal_groups: list[dict], hole_address: str) -> str:
    for group in terminal_groups:
        if hole_address in group["holes"]:
            return group["group_id"]
    raise ValueError(f"No terminal group contains hole {hole_address}.")


def compute_board_position(terminal_runtime: dict, column: int, row_letter: str):
    columns = terminal_runtime["columns"]
    x = columns["x_start_meter"] + (column - 1) * columns["x_pitch_meter"]
    z = terminal_runtime["rows_z_meter"][row_letter]
    y = terminal_runtime["surface_y_meter"]
    return [x, y, z]


def build_pin_placements(
    nano_metadata: dict, breadboard_layout: dict
) -> list[dict]:
    pins = breadboard_compatible_pins(nano_metadata)
    grouped = group_pins_by_header_row(pins)
    terminal_groups = breadboard_layout["electrical_connectivity"]["terminal_groups"]
    terminal_runtime = breadboard_layout["terminal_runtime"]

    placements: list[dict] = []
    for x, row_letter in ROW_X_TO_BOARD_ROW.items():
        row_pins = sorted(grouped[x], key=lambda pin: pin["position"][2])
        if len(row_pins) != PIN_COLUMN_SPAN:
            raise ValueError(
                f"Expected {PIN_COLUMN_SPAN} breadboard-compatible pins on the "
                f"row at x={x}, found {len(row_pins)}."
            )

        for offset, pin in enumerate(row_pins):
            column = START_COLUMN + offset
            hole_address = f"{row_letter}{column}"
            placements.append(
                {
                    "pinKey": pin["pinKey"],
                    "nodeName": pin["nodeName"],
                    "holeAddress": hole_address,
                    "terminalGroupId": find_terminal_group_id(
                        terminal_groups, hole_address
                    ),
                    "boardRow": row_letter,
                    "boardColumn": column,
                    "boardPosition": compute_board_position(
                        terminal_runtime, column, row_letter
                    ),
                }
            )
    return placements


def validate_placements(placements: list[dict]) -> None:
    hole_addresses = [placement["holeAddress"] for placement in placements]
    if len(hole_addresses) != len(set(hole_addresses)):
        duplicates = {
            hole for hole in hole_addresses if hole_addresses.count(hole) > 1
        }
        raise AssertionError(f"Duplicate hole addresses assigned: {duplicates}")

    out_of_bounds = [
        placement
        for placement in placements
        if not (1 <= placement["boardColumn"] <= 30)
    ]
    if out_of_bounds:
        raise AssertionError(
            "Pins placed outside the 30-column board: "
            f"{[p['pinKey'] for p in out_of_bounds]}"
        )

    group_ids = [placement["terminalGroupId"] for placement in placements]
    if len(group_ids) != len(set(group_ids)):
        duplicates = {gid for gid in group_ids if group_ids.count(gid) > 1}
        raise AssertionError(
            f"More than one pin shares the same 5-hole terminal group: {duplicates}"
        )

    ae_groups = {
        placement["terminalGroupId"]
        for placement in placements
        if placement["boardRow"] == "E"
    }
    fj_groups = {
        placement["terminalGroupId"]
        for placement in placements
        if placement["boardRow"] == "F"
    }
    if ae_groups & fj_groups:
        raise AssertionError(
            "Row E and row F pins resolved to the same terminal group "
            f"(center groove bridged): {ae_groups & fj_groups}"
        )
    if not all(gid.startswith("terminal-ae-") for gid in ae_groups):
        raise AssertionError("Row E pins must resolve to terminal-ae-* groups.")
    if not all(gid.startswith("terminal-fj-") for gid in fj_groups):
        raise AssertionError("Row F pins must resolve to terminal-fj-* groups.")


def main() -> None:
    nano_metadata = read_json(NANO_METADATA_PATH)
    breadboard_layout = read_json(BREADBOARD_LAYOUT_PATH)

    placements = build_pin_placements(nano_metadata, breadboard_layout)
    validate_placements(placements)

    output = {
        "component_slug": COMPONENT_SLUG,
        "board_slug": BOARD_SLUG,
        "mounting": {
            "mounting_type": nano_metadata["placement"]["mountingType"],
            "rotation_policy": nano_metadata["placement"]["rotationPolicy"],
            "straddles_center_gap": True,
            "board_rows": sorted(set(ROW_X_TO_BOARD_ROW.values())),
            "board_columns": [START_COLUMN, START_COLUMN + PIN_COLUMN_SPAN - 1],
            "notes": [
                "Nano header row spacing is 15.24 mm; the board's row E-row F "
                "gap measures 7.8 mm, so this placement straddles the center "
                "groove literally (rows E/F) rather than matching the header "
                "spacing to the millimeter.",
            ],
        },
        "pin_placements": placements,
    }
    write_json(OUTPUT_PATH, output)
    print(f"Wrote {len(placements)} pin placements to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
