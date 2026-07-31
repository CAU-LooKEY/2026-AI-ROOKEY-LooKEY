import test from "node:test";
import assert from "node:assert/strict";
import {
  breadboardHoleRatios,
  nearestEmptyHole,
  parseBreadboardAddress,
  resolveBreadboardWires,
} from "./breadboardWiring.js";

test("parses terminal groups and produces distinct hole coordinates", () => {
  assert.equal(parseBreadboardAddress("A12").electricalGroup, "ABCDE:12");
  assert.equal(parseBreadboardAddress("J12").electricalGroup, "FGHIJ:12");
  assert.notDeepEqual(breadboardHoleRatios("A12"), breadboardHoleRatios("J12"));
});

test("selects an unoccupied hole in the same five-hole strip", () => {
  assert.equal(nearestEmptyHole("A4", new Set(["A4", "B4"])), "C4");
});

test("omits a jumper when mounted legs already share a breadboard strip", () => {
  const wires = resolveBreadboardWires({
    connections: [{ id: "w1", source: "led", sourcePin: "ANODE", target: "r1", targetPin: "A" }],
    assemblyPlan: {
      components: [
        { instanceId: "breadboard", assetSlug: "breadboard-half" },
        { instanceId: "led", assetSlug: "led-5mm-red" },
        { instanceId: "r1", assetSlug: "resistor-220-ohm" },
      ],
      placements: [
        { componentId: "led", addresses: { ANODE: "A4" } },
        { componentId: "r1", addresses: { A: "E4" } },
      ],
      connections: [{
        id: "w1",
        source: { componentId: "led", pin: "ANODE", address: "A4" },
        target: { componentId: "r1", pin: "A", address: "E4" },
        electricalNode: "node:ABCDE:4",
        color: "#2563eb",
      }],
    },
  });
  assert.deepEqual(wires, []);
});

test("routes an external wire to an empty breadboard hole center", () => {
  const [wire] = resolveBreadboardWires({
    connections: [{
      id: "w1",
      source: "uno",
      sourcePin: "D9",
      sourceConnector: "female",
      target: "led",
      targetPin: "ANODE",
      targetConnector: "female",
      wireType: "female-female",
    }],
    assemblyPlan: {
      components: [
        { instanceId: "breadboard", assetSlug: "breadboard-half" },
        { instanceId: "uno", assetSlug: "arduino-uno-r3" },
        { instanceId: "led", assetSlug: "led-5mm-red" },
      ],
      placements: [{ componentId: "led", addresses: { ANODE: "A4" } }],
      connections: [{
        id: "w1",
        source: { componentId: "uno", pin: "D9", address: "BOARD:D9" },
        target: { componentId: "led", pin: "ANODE", address: "A4" },
        electricalNode: "node:signal",
        color: "#2563eb",
      }],
    },
  });
  assert.equal(wire.source, "uno");
  assert.equal(wire.target, "breadboard");
  assert.equal(wire.targetPin, "B4");
  assert.equal(wire.sourceConnector, "female");
  assert.equal(wire.targetConnector, undefined);
  assert.equal(wire.wireType, undefined);
});
