import assert from "node:assert/strict";
import test from "node:test";

import {
  REAL_WORLD_SCENE_UNITS_PER_METER,
  resolveModelScale,
} from "./modelScale.js";

test("keeps calibrated meter assets on the shared scene scale", () => {
  const metadata = {
    asset: { scaleStatus: "real-world" },
    coordinateSystems: { runtime: { unit: "meter" } },
  };

  assert.equal(
    resolveModelScale(metadata, { x: 0.04, y: 0.02, z: 0.03 }, 3),
    REAL_WORLD_SCENE_UNITS_PER_METER,
  );
});

test("uses the declared physical envelope for uncalibrated candidate assets", () => {
  const metadata = {
    asset: { scaleStatus: "uncalibrated" },
    coordinateSystems: { runtime: { unit: "model-unit" } },
    physicalDimensions: {
      unit: "millimeter",
      width: 43,
      depth: 43,
      height: 27,
    },
  };

  const scale = resolveModelScale(metadata, { x: 1, y: 0.5, z: 1 }, 3);
  assert.equal(scale, 0.043 * REAL_WORLD_SCENE_UNITS_PER_METER);
});

test("falls back to the visual profile when physical dimensions are unavailable", () => {
  assert.equal(
    resolveModelScale(null, { x: 2, y: 1, z: 1 }, 4),
    2,
  );
});
