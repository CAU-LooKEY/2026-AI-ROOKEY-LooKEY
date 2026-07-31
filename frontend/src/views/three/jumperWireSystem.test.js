import test from "node:test";
import assert from "node:assert/strict";
import {
  ConnectorGender,
  calculateCurveProfile,
  colorForWireRole,
  inferEndpointGender,
  insertionDepthSceneUnits,
  resolveJumperWire,
  WireColorRole,
} from "./jumperWireSystem.js";

const endpoint = (pinKey, interfaceGender, kind = "component-pin") => ({
  pinKey,
  interfaceGender,
  kind,
  metadata: null,
});

test("female Arduino header to female breadboard selects male-male", () => {
  const result = resolveJumperWire(
    { id: "wire-1" },
    endpoint("D9", ConnectorGender.FEMALE),
    endpoint("A1", ConnectorGender.FEMALE, "breadboard-hole"),
  );
  assert.equal(result.wireType, "male-male");
  assert.equal(result.validation.valid, true);
});

test("female header to male sensor selects male-female", () => {
  const result = resolveJumperWire(
    { id: "wire-2" },
    endpoint("D9", ConnectorGender.FEMALE),
    endpoint("TRIG", ConnectorGender.MALE),
  );
  assert.equal(result.wireType, "male-female");
});

test("male sensor to male sensor selects female-female", () => {
  const result = resolveJumperWire(
    { id: "wire-3" },
    endpoint("ECHO", ConnectorGender.MALE),
    endpoint("SIG", ConnectorGender.MALE),
  );
  assert.equal(result.wireType, "female-female");
});

test("rejects a female connector at a breadboard hole", () => {
  const result = resolveJumperWire(
    { id: "wire-4", targetConnector: "female" },
    endpoint("D9", ConnectorGender.FEMALE),
    endpoint("A1", ConnectorGender.FEMALE, "breadboard-hole"),
  );
  assert.equal(result.validation.valid, false);
  assert.ok(result.validation.issues.some((issue) => issue.code === "BREADBOARD_REQUIRES_MALE_064"));
});

test("rejects a male pin wider than a breadboard hole", () => {
  const breadboard = {
    ...endpoint("A1", ConnectorGender.FEMALE, "breadboard-hole"),
    connector: { diameterMillimeter: 0.5 },
  };
  const result = resolveJumperWire(
    { id: "wire-too-wide" },
    endpoint("D9", ConnectorGender.FEMALE),
    breadboard,
  );
  assert.equal(result.validation.valid, false);
  assert.ok(result.validation.issues.some((issue) => issue.code === "PIN_TOO_WIDE"));
});

test("applies power, ground, and signal colors", () => {
  assert.equal(colorForWireRole(WireColorRole.POWER), "#dc2626");
  assert.equal(colorForWireRole(WireColorRole.GROUND), "#1f2937");
  assert.equal(colorForWireRole(WireColorRole.SIGNAL, 0), "#2563eb");
});

test("curve lift and segments grow with distance", () => {
  const short = calculateCurveProfile(1, 0, 0);
  const long = calculateCurveProfile(8, 1, 2);
  assert.ok(long.lift > short.lift);
  assert.ok(long.tubularSegments > short.tubularSegments);
  assert.notEqual(long.lateralOffset, 0);
});

test("uses metadata gender before component fallback", () => {
  assert.equal(
    inferEndpointGender("arduino-uno-r3", { connector: { gender: "male" } }),
    "male",
  );
  assert.equal(inferEndpointGender("arduino-uno-r3", null), "female");
  assert.equal(inferEndpointGender("arduino-nano", null), "female");
});

test("converts connector insertion depth from millimeters to scene units", () => {
  assert.equal(insertionDepthSceneUnits({ insertionDepthMillimeter: 6 }), 0.48);
  assert.equal(insertionDepthSceneUnits({ insertionDepthMillimeter: 2 }), 0.16);
});
