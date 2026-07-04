# 2D Assets

This folder stores the visual assets used by frontend circuit nodes.

## Subfolders

- `raster_sources/`
  Transparent PNG source images for each component.
- `react_flow_nodes/`
  SVG wrappers for React Flow style nodes. These files preserve the component
  dimensions and expose visual pin markers.
- `pin_map_previews/`
  QA preview images with numbered pin labels overlaid on top of each asset.

## Coordinate System

Every pin coordinate is measured against the matching transparent PNG in
`raster_sources/`. The origin is the top-left pixel of the image:

```text
x: left to right
y: top to bottom
```

Frontend code can use the normalized coordinates in `db_scripts` if it needs to
scale an asset to a different display size.

## Storage Paths

When uploading to the Supabase Storage bucket `circuit-assets`, keep these
bucket-relative paths:

- `raster_sources/<component-slug>-top.png`
- `react_flow_nodes/<component-slug>.svg`
