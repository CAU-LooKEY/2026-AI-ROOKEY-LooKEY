import { demoAssets } from "../data/demoAssets";
import { demoCircuits } from "../data/demoCircuits";

const assetMap = new Map(demoAssets.map((asset) => [asset.slug, asset]));
const errors: string[] = [];

for (const scene of demoCircuits) {
  const placementMap = new Map(scene.placements.map((placement) => [placement.id, placement]));

  for (const placement of scene.placements) {
    if (!assetMap.has(placement.componentSlug)) {
      errors.push(`${scene.id}: placement ${placement.id} references missing asset ${placement.componentSlug}`);
    }
  }

  for (const connection of scene.connections) {
    for (const endpoint of [connection.from, connection.to]) {
      const placement = placementMap.get(endpoint.placementId);
      const asset = placement ? assetMap.get(placement.componentSlug) : null;
      const hasPin = asset?.pins.some((pin) => pin.pinKey === endpoint.pinKey);

      if (!placement) {
        errors.push(`${scene.id}: connection ${connection.id} references missing placement ${endpoint.placementId}`);
      } else if (!hasPin) {
        errors.push(
          `${scene.id}: connection ${connection.id} references missing pin ${placement.componentSlug}.${endpoint.pinKey}`,
        );
      }
    }
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`Validated ${demoAssets.length} assets and ${demoCircuits.length} demo circuits.`);
