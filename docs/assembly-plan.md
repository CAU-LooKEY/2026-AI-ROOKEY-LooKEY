# Assembly Plan 1.0

> The production implementation now uses the merged real 3D asset metadata.
> See `docs/physical-assembly-engine.md` for physical placement, split rails,
> electrical grouping, and placement-failure behavior.

`AssemblyPlan` is the server-owned physical layout returned as
`assemblyPlan` by `POST /api/v1/circuit/generate`. K-EXAONE continues to
produce the logical circuit; the backend converts that circuit into the same
physical plan every time.

## Top-level contract

- `schemaVersion`: currently `1.0`
- `components`: unique `instanceId`, asset database `assetSlug`, and label
- `placements`: one transform per component (`position`, `rotation`, `scale`)
- `connections`: typed endpoints, stable electrical-node ID, and wire color
- `warnings`: machine-readable code, severity, Korean message, and references

The Pydantic source of truth is
`backend/app/schemas/assembly_plan.py`. Unknown fields and broken component
references are rejected.

## Physical addresses

- `A1` through `J30`: breadboard holes. `A-E` and `F-J` are separate contact
  groups for each numbered column.
- `L+1`, `L-1`, `R+1`, `R-1` through column 30: left/right power rails.
- Arduino pins such as `GND_P1` and `5V` are board pins.
- Ambiguous Arduino analog/digital names can be explicit: `BOARD:A1` or
  `BOARD:D3`. Without the prefix, `A1` through `J30` mean breadboard holes.

## Placement rules

Canvas coordinates are snapped to a stable 3D grid. Colliding component
footprints are moved along the Z axis until their minimum spacing is met.
Breadboard candidate generation currently knows the physical pitch of 5 mm
LEDs, 220 ohm resistors, and HC-SR04 headers.

## Warning codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `PIN_DUPLICATE` | WARNING | More than one wire terminates directly on one pin |
| `POWER_GROUND_SHORT` | ERROR | Power and ground belong to the same electrical node |
| `LED_REVERSED` | ERROR | LED anode/cathode polarity is reversed |
| `LED_RESISTOR_MISSING` | ERROR | No current-limiting resistor is adjacent to an LED |
| `SENSOR_PIN_ROLE` | ERROR | A sensor power or signal pin has the wrong role |
| `ASSEMBLY_VALID` | INFO | No fatal assembly error was found |

Invalid addresses and impossible leg-pitch candidates are rejected before a
plan is returned. A future asset with unknown pitch returns no candidates so
the caller can show a placement failure without inventing physical geometry.
