# Arduino UNO R3 3D asset validation report

## Status

**Candidate — not approved**

This report records the state of `assets_db/3d_models/glb/arduino-uno-r3.glb`
after the Blender Empty placement work. It deliberately separates verified GLB
facts from items that still require mesh or catalog correction.

## Verified

- Runtime root: `ARDUINO_UNO_R3_ROOT`
- Root transform: identity location, rotation, and scale
- Runtime coordinate system: right-handed glTF local space, `+Y` up
- GLB `pin_*` nodes: 42
- Metadata pins: 42
- Maximum GLB-to-metadata coordinate error: `0.000000466 mm`
- Overall mesh bounds including connectors:
  - width: `75.337738 mm`
  - depth: `53.544750 mm`
  - height: `10.032145 mm`
- Pin metadata includes digital, analog, PWM, I2C, SPI, UART, power, ground,
  reset, and reference classifications.
- Standard header sockets are described as female sockets with `+Y` insertion
  direction, nominal `2.54 mm` pitch, and `6 mm` insertion depth.
- ICSP markers are described separately as male pins with `+Y` outward
  direction and nominal `0.64 mm` pin width.

The Blender-based GLB/metadata validator passes:

```text
pinNodeCount: 42
metadataPinCount: 42
maximumPinPositionErrorMillimeter: 4.6566128730773926e-07
rootNode: ARDUINO_UNO_R3_ROOT
result: PASS
```

## Approval blockers

1. The component pin catalog and the GLB do not currently describe the same
   electrical interface.
   - Catalog entries missing from the GLB include the canonical `SCL`, `SDA`,
     and auxiliary header pins.
   - The GLB contains `pin_NC` and twelve spatial ICSP markers that do not yet
     have approved catalog keys or electrical aliases.
2. The first digital socket mesh visually contains ten holes where the UNO
   header segment is expected to contain eight. The Empty positions must be
   rechecked after that mesh is corrected.
3. The manually placed `D0`–`D7` marker spacing is approximately `2.1 mm`, not
   the standard `2.54 mm` UNO header pitch.
4. At least one marker interval in the `D8`–`D13` section is approximately
   `2.441 mm`; the full row must be remeasured against socket centers.
5. The two ICSP groups currently measure approximately `1.9–2.06 mm` and
   `1.99–2.00 mm` between markers. Their real socket-center pitch and exact
   electrical mapping must be confirmed.
6. `scaleStatus` remains `uncalibrated`. The mesh bounds include protruding
   connectors and therefore do not by themselves prove the UNO PCB's nominal
   board dimensions.
7. Model source, license, and redistribution rights still need confirmation.

Because of these blockers, the repository-wide metadata validator correctly
rejects promotion to `approved`, even though the GLB node-to-JSON coordinate
validation passes.

## Files and repeatable checks

- Candidate metadata:
  `assets_db/3d_models/component_metadata/candidates/arduino-uno-r3/yoohyeon93-blender-empty.json`
- Metadata generator:
  `assets_db/db_scripts/generate_arduino_uno_r3_candidate.py`
- GLB inspection helper:
  `assets_db/db_scripts/inspect_glb_component_state.py`
- Schema/catalog check:
  `python assets_db/db_scripts/validate_component_3d_metadata.py`
- GLB coordinate check:
  `blender --background --python assets_db/db_scripts/validate_glb_pin_metadata.py -- assets_db/3d_models/component_metadata/candidates/arduino-uno-r3/yoohyeon93-blender-empty.json`

## Promotion checklist

- [ ] Correct the ten-hole digital header mesh or replace the affected mesh.
- [ ] Recenter and re-export `D0`–`D13` markers at verified socket centers.
- [ ] Resolve `SCL`, `SDA`, auxiliary, `NC`, and ICSP catalog mappings.
- [ ] Confirm physical PCB dimensions and set `scaleStatus` to `real-world`.
- [ ] Record model source, license, and redistribution rights.
- [ ] Re-run both validators with no errors.
- [ ] Move metadata from `candidates` to `approved`.
