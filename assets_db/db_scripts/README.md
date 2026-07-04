# Supabase DB Scripts

This folder contains the database side of the circuit asset package.

## Files

- `001_schema.sql`
  Creates the storage bucket, component tables, image tables, pin tables, and
  read policies.
- `002_seed_assets_and_pins.sql`
  Inserts the current component metadata, image paths, and pin coordinates.
- `pin_coordinates/*.json`
  Per-component coordinate exports.
- `all_component_pin_coordinates.json`
  Combined coordinate export for all components.
- `image_processing_manifest.json`
  Source image conversion and output manifest.
- `validate_pin_coordinates.py`
  Local validation helper for image bounds and required fields.

## Apply Order

1. Run `001_schema.sql` in Supabase SQL Editor.
2. Upload files from `../2d_svgs/raster_sources/` to the Storage bucket
   `circuit-assets/raster_sources/`.
3. Upload files from `../2d_svgs/react_flow_nodes/` to the Storage bucket
   `circuit-assets/react_flow_nodes/`.
4. Run `002_seed_assets_and_pins.sql`.
5. Run `python validate_pin_coordinates.py` locally when coordinates or images
   change.

The schema allows `image/png`, `image/jpeg`, and `image/svg+xml` because the
current package uses transparent PNG sources and SVG node wrappers.
