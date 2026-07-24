# Half Breadboard 3D Asset Candidate

## Result

- Component: Half-size Breadboard
- Component slug: `breadboard-half`
- Branch: `feat/asset-breadboard-jumper`
- Status: `candidate`
- Authoring tool: Blender 5.2 LTS
- Source workflow: STEP imported through Bambu Studio and normalized in Blender

## Source and license

- Upstream model: [Half Breadboard — GrabCAD Community Library](https://grabcad.com/library/half-breadboard-1)
- Upstream ownership: third-party user submission
- Recorded permission: GrabCAD Community guidance describes Library models as
  free for personal use.
- License review status: `pending`

The model page does not expose an explicit open-source, redistribution, or
commercial-use license in the accessible page content. The normalized GLB
therefore remains a candidate and must not be promoted to `approved` until the
team confirms that repository redistribution is permitted or replaces it with
an asset carrying a suitable license.

## Normalized asset

- Runtime coordinate system: right-handed
- Runtime up axis: `+Y`
- Runtime front axis: `+Z`
- Runtime unit: meter
- Measured runtime bounds: `83.01 x 9.51 x 56.08 mm` in `X/Y/Z`
- Origin: center of the top insertion surface
- Body direction from origin: runtime `-Y`
- GLB SHA-256: `09574a9d7b95d22dec389cef3048615289c18bcd4ed12287323bd4e223b1de76`

## Terminal-hole calibration

- Empty naming: `pin_A1` through `pin_J30`
- Terminal Empty count: 300
- Power-rail Empty count: 100
- Total Empty count: 400
- Empty source of truth: GLB node transforms
- Runtime outward direction: `[0, 1, 0]`
- Column start: `X = -37.495 mm`
- Column pitch: `2.54 mm`
- Column formula: `X(column) = -37.495 + (column - 1) * 2.54 mm`
- A1 to A30 distance: `73.66 mm`

Measured authoring row positions:

| Row | Y (mm) |
| --- | ---: |
| A | 14.725 |
| B | 12.185 |
| C | 9.645 |
| D | 7.105 |
| E | 4.565 |
| F | -3.235 |
| G | -5.775 |
| H | -8.315 |
| I | -10.855 |
| J | -13.395 |

The runtime conversion is `[authoring X, authoring Z, -authoring Y]`.

## Electrical connectivity

- Each column has one internally common `A-E` group.
- Each column has one internally common `F-J` group.
- Total terminal groups: 60.
- Every terminal group contains five holes.
- The four power-rail rows each contain five isolated segments of five holes.
- Total recorded power-rail segments: 20.
- Different rail segments and different positive/negative rows are electrically isolated.

## Socket and jumper fit

- Measured square socket opening: `0.723666 x 0.723666 mm`
- Measured modeled insertion depth: `7.09568 mm`
- Runtime outward axis: `+Y`
- Runtime insertion axis: `-Y`
- Reference male jumper profile: `0.64 x 0.64 mm`
- Total profile clearance: `0.083666 mm`
- Clearance per side when centered: `0.041833 mm`
- Geometry fit result: `PASS`
- Machine-readable specification:
  `assets_db/db_scripts/jumper_connectors/breadboard-half-jumper-fit.json`

The `0.64 mm` square male profile and `2.54 mm` pitch are supported by
Molex product specification `PS-10-07-001` and the Amphenol BergStik
documentation. Harwin M20 female crimp contacts also specify a `0.64 mm`
square mating pin at `2.54 mm` pitch. The fit result validates geometry only:
the source mesh does not model the breadboard's internal metal spring contacts,
so insertion/withdrawal force is outside this validation.

## Visual checks

- A1, E1, F1, and J1 were placed from selected GLB hole geometry.
- A2 verified the `2.54 mm` pitch.
- D17, H23, and J30 were checked against actual GLB hole centers.
- Asset Lab loaded the final candidate with 300 terminal-hole and 100 power-rail Empty nodes.
- Red GLB `pin_*` markers and teal metadata markers overlap at the modeled hole centers.
- Full-screen evidence: `evidence/asset-lab-full.png`
- Terminal and power-rail close-up evidence: `evidence/asset-lab-pin-closeup.png`

## Validation commands

```powershell
python assets_db/db_scripts/validate_breadboard_half_candidate.py
python assets_db/db_scripts/validate_component_3d_metadata.py
python assets_db/db_scripts/validate_3d_pin_anchors.py
python assets_db/db_scripts/validate_pin_coordinates.py
python assets_db/db_scripts/validate_3d_models.py
pnpm --dir frontend run build
```

All listed data validators and the frontend production build pass.

## Remaining review items

- Measure the physical socket opening and usable insertion depth; candidate metadata keeps these values `null`.
- Confirm redistribution permission for the GrabCAD-derived mesh or replace it
  with a suitably licensed source before approval.
- Select the exact physical jumper product if insertion/withdrawal-force
  validation is required.
