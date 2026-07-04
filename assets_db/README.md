# Circuit Asset Database

This folder contains the asset database package for the hardware circuit
visualization workstream. It is scoped to component metadata, image assets, and
pin coordinates only.

## Components Included

The current seed set contains 6 components and 82 pins:

- Arduino Uno R3
- Arduino Nano
- HC-SR04 ultrasonic sensor
- 5 mm blue LED
- 6x6 pushbutton
- SG90-style servo motor

Pin coordinates are stored in source-image pixel coordinates with `(0, 0)` at
the top-left of the transparent PNG.

## Folder Map

- `2d_svgs/`
  Transparent PNG source assets, React Flow SVG wrappers, and pin-map preview
  images.
- `db_scripts/`
  Supabase schema, seed SQL, and JSON pin coordinate exports.
- `3d_models/`
  Reserved for real 3D source assets. This package currently does not include
  production `.glb`, `.fbx`, `.blend`, or VARCO model files.

## Production Notes

- The SVG files are lightweight node wrappers around the transparent PNG
  images. Upload the PNG and SVG files to Supabase Storage before running the
  seed SQL.
- The LED source image is angled rather than a strict top-down image, so its
  two lead coordinates are usable for a prototype but should be replaced with a
  cleaner calibrated top-view asset before production.
- Trademarked markings and logos on source images should be reviewed before
  public release.
