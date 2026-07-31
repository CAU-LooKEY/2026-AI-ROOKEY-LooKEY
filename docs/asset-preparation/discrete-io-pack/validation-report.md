# Discrete LED and Input Asset Pack Validation

Validated on 2026-07-29 for branch `feat/assets-discrete-io-pack`.

## Scope

| Component | Asset | Pin / contact contract | Breadboard footprint | Asset Lab evidence |
| --- | --- | --- | --- | --- |
| Blue 5 mm LED | `led-5mm-blue.glb` | `ANODE`, `CATHODE`; polarity and 2.54 mm pitch encoded | 2 columns x 1 row | [PNG](evidence/led-5mm-blue-asset-lab.png) |
| Red 5 mm LED | `led-5mm-red.glb` | `ANODE`, `CATHODE`; pin anchors verified | 2 columns x 1 row | [PNG](evidence/led-5mm-red-asset-lab.png) |
| RGB 5 mm LED | `led-rgb-5mm.glb` | `RED`, `COMMON_CATHODE`, `GREEN`, `BLUE` | 4 columns x 1 row | [PNG](evidence/led-rgb-5mm-asset-lab.png) |
| 220 ohm resistor | `resistor-220-ohm.glb` | interchangeable `LEAD_A`, `LEAD_B` | metadata-encoded lead anchors | [PNG](evidence/resistor-220-ohm-asset-lab.png) |
| 6x6 push button | `pushbutton-6x6.glb` | four pins; A pair and B pair internal contacts encoded | contact pairs verified | [PNG](evidence/pushbutton-6x6-asset-lab.png) |
| 10 kohm potentiometer | `potentiometer-10k.glb` | `CCW`, `WIPER`, `CW` | 3 columns x 4 rows | [PNG](evidence/potentiometer-10k-asset-lab.png) |
| SPDT slide switch | `slide-switch-spdt.glb` | `THROW_A`, `COMMON`, `THROW_B` | 3 columns x 3 rows | [PNG](evidence/slide-switch-spdt-asset-lab.png) |

## Blue LED reference

The procedural blue LED is based on Kingbright `WP7113QBC/D`, specification
`DSAG3481 Rev V.18B` dated 2025-03-26. The candidate metadata records a
5.9 mm package diameter, 8.6 mm body height, 2.54 mm lead spacing, and
the datasheet's general +/-0.25 mm tolerance.

Official source:
https://www.kingbrightusa.com/images/catalog/spec/wp7113qbc-d.pdf

## Automated checks

The following checks pass:

```text
python assets_db/db_scripts/validate_discrete_io_pack.py
  PASS: 8 components; GLB anchors, polarity, contacts, and occupancy

python assets_db/db_scripts/validate_3d_models.py
  PASS: 10 registered GLB model files

python assets_db/db_scripts/validate_component_3d_metadata.py
  PASS: all 9 candidate metadata files

npm run build  (from frontend/)
  PASS: production bundle generated
```

Asset Lab was also exercised interactively for all seven components listed
above. Each model loaded and rendered, and the browser console reported no
errors during the final run.

## Review state

All metadata remains `candidate` intentionally. Schema validation, named GLB
pin anchors, component electrical roles, placement rules, and Asset Lab
rendering are ready for review. Changing a record to `approved` requires an
independent reviewer identity and approval date; those fields must not be
self-certified by the asset author.

The existing red LED, resistor, and push-button source assets retain their
original provenance notes. A reviewer should confirm their redistribution
license before approval. The new RGB LED, potentiometer, and slide switch are
nominal procedural assets; projects requiring a particular vendor part should
bind each one to that part's datasheet before treating package dimensions as a
manufacturing reference.
