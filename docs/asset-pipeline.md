# Circuit Asset Pipeline

## Supabase model

Store files in the public `circuit-assets` bucket and store render metadata in:

- `circuit_component_assets`: one row per component.
- `circuit_component_asset_images`: one row per image variant.
- `circuit_component_pins`: one row per connectable pin.

The frontend reads only `ready` assets through RLS policies. Uploads should use the server-only `SUPABASE_SERVICE_ROLE_KEY` through `npm run upload:assets`.

## ZIP import shape

Place ZIP files in `asset-import/`. The ZIP file name must match the component slug:

```txt
asset-import/
  arduino-uno-r3.zip
  arduino-nano.zip
  breadboard-half.zip
  hc-sr04.zip
  led-5mm-red.zip
  pushbutton-6x6.zip
  servo-sg90.zip
```

Inside each ZIP:

```txt
isometric.png
preview-3d.jpg
schematic.png
```

File names containing `3d` or `preview` become `preview_3d`; names containing `schematic` or `symbol` become `schematic_2d`; all other supported images become `isometric_2d`.

## Image formats

This project accepts only PNG and JPEG for ZIP imports.

- Use transparent PNG for the main 2.5D diagram asset whenever possible.
- Use JPEG only for opaque 3D-looking preview renders.
- Do not put STL, GLB, GLTF, WebP, SVG, or PDF files in the ZIP for this DB flow.

The phrase "3D image" means a PNG/JPEG rendered from a fixed 3D camera angle, not a 3D model file.

## Pin coordinates

All pin positions are image-pixel coordinates relative to the final cropped asset image. If the PNG crop, padding, or export size changes, recalibrate `x_px` and `y_px`.

Uploading a ZIP does not automatically discover exact pin centers from an arbitrary image. The upload script can store files automatically, but pin coordinates must come from one of these sources:

1. A predefined template for that component slug, such as `arduino-uno-r3`.
2. A manual calibration pass where each pin center is clicked once.
3. A computer-vision helper, followed by human review.

For education circuits, exact pin coordinates should be treated as authored metadata.

Recommended workflow:

1. Export every component to a fixed pixel size.
2. Keep a transparent margin convention.
3. Record each pin center in image pixels.
4. Store aliases such as `13`, `GPIO17`, `SDA`, or `GND` for prompt parsing.

## Initial asset set

The current first batch is:

- `arduino-uno-r3`
- `arduino-nano`
- `breadboard-half`
- `hc-sr04`
- `led-5mm-red`
- `pushbutton-6x6`
- `servo-sg90`

LEDs and pushbuttons should usually be placed through a breadboard in generated circuits. The breadboard image also needs calibrated hole coordinates or at least representative anchor holes for early prototypes.
