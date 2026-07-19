# Circuit Asset Pipeline

Use `asset-import/{component-slug}.zip` and run:

```bash
pnpm upload:assets
```

Supported upload formats:

- `image/png`
- `image/jpeg`

Recommended ZIP files:

- `arduino-uno-r3.zip`
- `arduino-nano.zip`
- `breadboard-half.zip`
- `hc-sr04.zip`
- `led-5mm-red.zip`
- `pushbutton-6x6.zip`
- `servo-sg90.zip`

Use transparent PNG for the primary `isometric_2d` asset. Use JPEG only for opaque 3D-looking preview renders.

Pin coordinates use final image pixels from the cropped asset's top-left corner.
