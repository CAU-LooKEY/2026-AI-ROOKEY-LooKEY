# Physical Assembly Engine

The production assembly path combines `feat/assembly-plan-engine` with the
asset data merged from `integration/3d-assets`. The source integration branch
is not modified; its metadata is consumed from this branch.

## Runtime data sources

- `breadboard-half-pin-coordinates.json`: 30-column, 2.54 mm procedural hole
  coordinates in GLTF model-local meters
- `breadboard-half-layout.json`: A-E/F-J terminal groups and the real split
  power-rail groups
- component metadata: physical dimensions, pin anchors, pin pitch,
  breadboard compatibility, insertion depth, and keep-out margins

The loader is `backend/app/services/asset_metadata.py`. The placement and
electrical graph implementation is
`backend/app/services/physical_assembly.py`.

## Placement

The engine adds one `breadboard-half` assembly instance, leaves the Arduino
beside the breadboard, and places breadboard-compatible parts in stable ID
order. Candidate positions must satisfy all of the following:

1. every lead lands on a real A1-J30 hole at the metadata pitch;
2. no hole is already occupied;
3. physical dimensions plus the metadata keep-out margin do not overlap;
4. the full keep-out rectangle remains inside the real breadboard bounds.

Successful placements contain pin-to-hole `addresses` and a transform derived
from the real hole coordinates. The same input therefore produces the same
serialized plan.

## Electrical graph

The union-find graph joins:

- a component pin to its allocated physical hole;
- each hole to its actual A-E/F-J terminal group;
- rail holes only to their five-hole asset segment;
- the two endpoints of each jumper connection.

Resistor leads, LED leads, and sensor pins are deliberately not joined through
the component body. This preserves resistance, polarity, and independent
sensor-pin semantics while still allowing short-circuit and series-component
checks over the physical graph.

Rail aliases use `T+1` to `T+25`, `T-1` to `T-25`, `B+1` to `B+25`, and
`B-1` to `B-25`. The full asset names such as
`RAIL_TOP_POS_S1_1` are also accepted. Each set of five holes is common;
adjacent five-hole segments are isolated, matching the asset metadata.

## Placement failure policy

The API returns a partial plan instead of discarding the logical circuit.
A failed `Placement` has `status: "failed"`, a `failureCode`, empty addresses,
and a matching structured warning containing a Korean message, suggestion,
component IDs, and diagnostic details.

| Code | Meaning |
| --- | --- |
| `BREADBOARD_METADATA_MISSING` | Breadboard coordinates cannot be loaded |
| `ASSET_METADATA_MISSING` | A component has no usable physical pin metadata |
| `NO_PLACEMENT_CANDIDATE` | No in-bounds, pitch-correct, collision-free holes remain |
| `ASSET_SCALE_UNCALIBRATED` | Placement used nominal pitch for an unapproved asset |
| `HOLE_OCCUPIED` | Multiple leads occupy the same physical hole |
| `PIN_DUPLICATE` | Multiple jumper wires terminate directly at one pin |
| `POWER_GROUND_SHORT` | Power and ground resolve to one electrical node |
| `LED_REVERSED` | LED polarity is reversed |
| `LED_RESISTOR_MISSING` | No resistor shares either LED terminal node |
| `SENSOR_PIN_ROLE` | A sensor terminal resolves to the wrong board-pin role |

## Verification

`backend/tests/test_physical_assembly.py` verifies the merged real metadata,
2.54 mm pitch, split rail semantics, five representative circuits, endpoint
addresses, deterministic output, board bounds, and structured placement
failure results.
