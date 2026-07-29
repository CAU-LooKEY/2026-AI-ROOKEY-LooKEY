import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = REPOSITORY_ROOT / "assets_db"
COMPONENT_METADATA_ROOT = ASSET_ROOT / "3d_models/component_metadata"
BREADBOARD_COORDINATES_PATH = (
    ASSET_ROOT / "db_scripts/pin_coordinates/breadboard-half-pin-coordinates.json"
)
BREADBOARD_LAYOUT_PATH = (
    ASSET_ROOT / "db_scripts/breadboard_layouts/breadboard-half-layout.json"
)
BREADBOARD_METADATA_PATH = (
    ASSET_ROOT / "3d_models/component_metadata/candidates/breadboard-half/quality1435-blender-empty.json"
)


class AssetMetadataError(RuntimeError):
    pass


@dataclass(frozen=True)
class ComponentFootprint:
    asset_slug: str
    pins: tuple[str, ...]
    offsets: tuple[int, ...]
    width_meter: float
    depth_meter: float
    keep_out_meter: float
    normalized: bool
    pin_positions_meter: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class BreadboardGeometry:
    columns: int
    x_start_meter: float
    x_pitch_meter: float
    rows_z_meter: dict[str, float]
    surface_y_meter: float
    rail_groups: dict[str, str]
    x_bounds: tuple[float, float]
    z_bounds: tuple[float, float]

    def hole_position(self, address: str) -> tuple[float, float, float]:
        row, column = address[0], int(address[1:])
        if row not in self.rows_z_meter or not 1 <= column <= self.columns:
            raise AssetMetadataError(f"Unknown breadboard hole: {address}")
        return (
            self.x_start_meter + (column - 1) * self.x_pitch_meter,
            self.surface_y_meter,
            self.rows_z_meter[row],
        )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except (OSError, ValueError) as exc:
        raise AssetMetadataError(f"Could not load asset metadata: {path}") from exc


@lru_cache
def load_component_footprint(asset_slug: str) -> ComponentFootprint:
    path = _find_component_metadata_path(asset_slug)
    metadata = _read_json(path)
    pins = metadata.get("pins", [])
    compatible = [pin for pin in pins if pin.get("mounting", {}).get("breadboardCompatible")]
    if not compatible:
        raise AssetMetadataError(f"No breadboard-compatible pins for {asset_slug}")

    pin_positions = tuple(
        (float(pin["position"][0]), float(pin["position"][2]))
        for pin in compatible
    )
    x_positions = [position[0] for position in pin_positions]
    origin = min(x_positions)
    pitch = 0.00254
    normalized = bool(metadata.get("origin", {}).get("normalized"))
    offsets = tuple(
        round((position - origin) / pitch) for position in x_positions
    )
    if not normalized or len(set(offsets)) != len(offsets):
        offsets = tuple(range(len(compatible)))

    dimensions = metadata["physicalDimensions"]
    placement = metadata["placement"]
    return ComponentFootprint(
        asset_slug=asset_slug,
        pins=tuple(pin["pinKey"] for pin in compatible),
        offsets=offsets,
        width_meter=float(dimensions["width"]) / 1000,
        depth_meter=float(dimensions["depth"]) / 1000,
        keep_out_meter=float(placement.get("keepOutMarginMillimeter", 0)) / 1000,
        normalized=normalized,
        pin_positions_meter=pin_positions,
    )


def _find_component_metadata_path(asset_slug: str) -> Path:
    candidates = (
        COMPONENT_METADATA_ROOT / "approved" / asset_slug / "metadata.json",
        COMPONENT_METADATA_ROOT / "candidates" / asset_slug / "metadata.json",
        COMPONENT_METADATA_ROOT / "examples" / f"{asset_slug}.projected-2d.example.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise AssetMetadataError(f"No 3D component metadata for {asset_slug}")


@lru_cache
def load_breadboard_geometry() -> BreadboardGeometry:
    coordinates = _read_json(BREADBOARD_COORDINATES_PATH)
    procedural = coordinates["runtime_procedural"]
    columns = procedural["columns"]
    layout = _read_json(BREADBOARD_LAYOUT_PATH)
    board_metadata = _read_json(BREADBOARD_METADATA_PATH)
    dimensions = board_metadata["physicalDimensions"]
    rail_groups: dict[str, str] = {}
    for group in layout["electrical_connectivity"]["rail_groups"]:
        for hole in group["holes"]:
            rail_groups[hole] = group["group_id"]
    return BreadboardGeometry(
        columns=int(columns["count"]),
        x_start_meter=float(columns["x_start_meter"]),
        x_pitch_meter=float(columns["x_pitch_meter"]),
        rows_z_meter={key: float(value) for key, value in procedural["rows_z_meter"].items()},
        surface_y_meter=float(procedural["surface_y_meter"]),
        rail_groups=rail_groups,
        x_bounds=(-float(dimensions["width"]) / 2000, float(dimensions["width"]) / 2000),
        z_bounds=(-float(dimensions["depth"]) / 2000, float(dimensions["depth"]) / 2000),
    )
