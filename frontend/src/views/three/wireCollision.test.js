import test from "node:test";
import assert from "node:assert/strict";
import {
  obstacleClearanceHeight,
  segmentCrossesObstacle,
} from "./wireCollision.js";

const sensor = {
  id: "sensor",
  minX: 2,
  maxX: 4,
  minZ: 1,
  maxZ: 3,
  maxY: 2.2,
};

test("detects a wire segment crossing a component footprint", () => {
  assert.equal(
    segmentCrossesObstacle({ x: 0, z: 2 }, { x: 6, z: 2 }, sensor),
    true,
  );
  assert.equal(
    segmentCrossesObstacle({ x: 0, z: 5 }, { x: 6, z: 5 }, sensor),
    false,
  );
});

test("raises a crossing wire above the tallest obstacle", () => {
  assert.equal(
    obstacleClearanceHeight(
      { x: 0, z: 2 },
      { x: 6, z: 2 },
      [sensor, { ...sensor, id: "button", maxY: 3.1 }],
    ),
    3.4,
  );
});

test("ignores source and target components when checking collisions", () => {
  assert.equal(
    obstacleClearanceHeight(
      { x: 0, z: 2 },
      { x: 6, z: 2 },
      [sensor],
      new Set(["sensor"]),
    ),
    null,
  );
});
