import assert from "node:assert/strict";
import test from "node:test";

import { resolveAssemblyParts } from "./assemblyCircuit.js";

test("adds the generated breadboard and assembly transforms to 3D parts", () => {
  const circuit = {
    parts: [{
      id: "led-1",
      label: "LED",
      componentKey: "led-5mm-blue",
      position: { x: 20, y: 30 },
      width: 80,
    }],
    assemblyPlan: {
      components: [
        { instanceId: "breadboard-1", assetSlug: "breadboard-half", label: "Breadboard" },
        { instanceId: "led-1", assetSlug: "led-5mm-blue", label: "LED" },
      ],
      placements: [
        {
          componentId: "breadboard-1",
          mode: "board",
          status: "placed",
          transform: { position: { x: 0, y: 0, z: 0 } },
        },
        {
          componentId: "led-1",
          mode: "breadboard",
          status: "placed",
          transform: { position: { x: 0.01, y: 0.002, z: -0.01 } },
        },
      ],
    },
  };

  const parts = resolveAssemblyParts(circuit);

  assert.equal(parts.length, 2);
  assert.equal(parts[0].componentKey, "breadboard-half");
  assert.deepEqual(parts[1].assemblyTransform.position, { x: 0.01, y: 0.002, z: -0.01 });
});

test("keeps the legacy circuit parts when no assembly plan exists", () => {
  const parts = [{ id: "legacy-part" }];
  assert.equal(resolveAssemblyParts({ parts }), parts);
});

test("omits components whose physical placement failed", () => {
  const parts = resolveAssemblyParts({
    parts: [],
    assemblyPlan: {
      components: [{ instanceId: "missing", assetSlug: "led-5mm-blue", label: "Missing" }],
      placements: [{
        componentId: "missing",
        status: "failed",
        transform: { position: { x: 0, y: 0, z: 0 } },
      }],
    },
  });

  assert.deepEqual(parts, []);
});
