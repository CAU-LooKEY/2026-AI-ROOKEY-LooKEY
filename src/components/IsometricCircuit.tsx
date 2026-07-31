import type { ReactElement } from "react";
import type {
  AssetImageKind,
  CircuitComponentAsset,
  CircuitScene,
  ComponentPin,
} from "../types/circuit";
import { isoToScreen, TILE_HEIGHT, TILE_WIDTH, type Point } from "../lib/geometry";

interface IsometricCircuitProps {
  assets: CircuitComponentAsset[];
  scene: CircuitScene;
  imageKind: AssetImageKind;
  showPinLabels: boolean;
}

interface RenderedPlacement {
  placementId: string;
  asset: CircuitComponentAsset;
  left: number;
  top: number;
  width: number;
  height: number;
  zIndex: number;
  imageUrl: string | null;
  pins: Array<ComponentPin & { screen: Point }>;
}

const VIEWBOX_WIDTH = 1120;
const VIEWBOX_HEIGHT = 700;
const COMPONENT_SCALE = 0.42;
const GRID_COLUMNS = 21;
const GRID_ROWS = 15;
const ORIGIN = { x: 530, y: 56 };

export function IsometricCircuit({
  assets,
  scene,
  imageKind,
  showPinLabels,
}: IsometricCircuitProps) {
  const assetMap = new Map(assets.map((asset) => [asset.slug, asset]));
  const renderedPlacements = scene.placements
    .map((placement) => {
      const asset = assetMap.get(placement.componentSlug);
      if (!asset) {
        return null;
      }

      const foot = isoToScreen(
        placement.gridX + asset.gridWidth / 2,
        placement.gridY + asset.gridHeight / 2,
        ORIGIN,
      );
      const width = asset.pixelWidth * COMPONENT_SCALE;
      const height = asset.pixelHeight * COMPONENT_SCALE;
      const left = foot.x - width / 2 + asset.originX * COMPONENT_SCALE;
      const top = foot.y - height + (asset.gridHeight * TILE_HEIGHT) / 2 + asset.originY * COMPONENT_SCALE;
      const imageUrl =
        asset.images.find((image) => image.kind === imageKind)?.url ??
        asset.images.find((image) => image.kind === "isometric_2d")?.url ??
        null;

      const pins = asset.pins.map((assetPin) => ({
        ...assetPin,
        screen: {
          x: left + assetPin.x * COMPONENT_SCALE,
          y: top + assetPin.y * COMPONENT_SCALE,
        },
      }));

      return {
        placementId: placement.id,
        asset,
        left,
        top,
        width,
        height,
        zIndex: Math.round((placement.gridX + placement.gridY) * 10),
        imageUrl,
        pins,
      } satisfies RenderedPlacement;
    })
    .filter((placement): placement is RenderedPlacement => Boolean(placement))
    .sort((a, b) => a.zIndex - b.zIndex);

  const pinLookup = new Map<string, Point>();
  renderedPlacements.forEach((placement) => {
    placement.pins.forEach((pin) => {
      pinLookup.set(`${placement.placementId}:${pin.pinKey}`, pin.screen);
    });
  });

  return (
    <div className="circuit-stage" aria-label={scene.title}>
      <svg className="iso-grid" viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} role="presentation">
        <GridLines />
        <WireLayer scene={scene} pinLookup={pinLookup} />
      </svg>

      {renderedPlacements.map((placement) => (
        <div
          className="component-asset"
          key={placement.placementId}
          style={{
            left: placement.left,
            top: placement.top,
            width: placement.width,
            height: placement.height,
            zIndex: placement.zIndex,
          }}
        >
          {placement.imageUrl ? (
            <img src={placement.imageUrl} alt={placement.asset.displayName} draggable={false} />
          ) : (
            <FallbackAsset asset={placement.asset} />
          )}

          <div className="pin-layer">
            {placement.pins.map((pin) => (
              <span
                className={`pin-dot signal-${pin.signalType}`}
                key={pin.pinKey}
                style={{
                  left: pin.x * COMPONENT_SCALE,
                  top: pin.y * COMPONENT_SCALE,
                }}
                title={`${placement.asset.displayName} ${pin.label}`}
              >
                {showPinLabels && <span className="pin-label">{pin.label}</span>}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function GridLines() {
  const lines: ReactElement[] = [];

  for (let x = 0; x <= GRID_COLUMNS; x += 1) {
    const start = isoToScreen(x, 0, ORIGIN);
    const end = isoToScreen(x, GRID_ROWS, ORIGIN);
    lines.push(<line key={`x-${x}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} />);
  }

  for (let y = 0; y <= GRID_ROWS; y += 1) {
    const start = isoToScreen(0, y, ORIGIN);
    const end = isoToScreen(GRID_COLUMNS, y, ORIGIN);
    lines.push(<line key={`y-${y}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} />);
  }

  return <g className="grid-lines">{lines}</g>;
}

function WireLayer({
  scene,
  pinLookup,
}: {
  scene: CircuitScene;
  pinLookup: Map<string, Point>;
}) {
  return (
    <g className="wire-layer">
      {scene.connections.map((connection) => {
        const start = pinLookup.get(`${connection.from.placementId}:${connection.from.pinKey}`);
        const end = pinLookup.get(`${connection.to.placementId}:${connection.to.pinKey}`);

        if (!start || !end) {
          return null;
        }

        const lift = Math.max(34, Math.min(90, Math.abs(start.x - end.x) * 0.12));
        const midY = Math.min(start.y, end.y) - lift;
        const path = `M ${start.x} ${start.y} C ${start.x} ${midY}, ${end.x} ${midY}, ${end.x} ${end.y}`;
        const labelX = (start.x + end.x) / 2;
        const labelY = midY - 6;

        return (
          <g key={connection.id}>
            <path className="wire-shadow" d={path} />
            <path className="wire" d={path} style={{ stroke: connection.color }} />
            {connection.label && (
              <text className="wire-label" x={labelX} y={labelY}>
                {connection.label}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

function FallbackAsset({ asset }: { asset: CircuitComponentAsset }) {
  return (
    <div className={`fallback-asset fallback-${asset.category}`}>
      <div className="fallback-title">{asset.displayName}</div>
      <div className="fallback-body" />
    </div>
  );
}
