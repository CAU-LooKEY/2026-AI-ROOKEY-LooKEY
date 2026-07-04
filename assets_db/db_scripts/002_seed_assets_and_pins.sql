-- Seed circuit component assets, transparent top-view images, SVG wrappers, and image-space pin coordinates.
-- Upload files in assets_db/2d_svgs/raster_sources and assets_db/2d_svgs/react_flow_nodes
-- to the Supabase Storage bucket `circuit-assets` with the same storage_path values used below.

with asset_rows as (
  select * from jsonb_to_recordset($assets$[
  {
    "slug": "arduino-uno-r3",
    "display_name": "Arduino Uno R3",
    "category": "controller",
    "board_family": "arduino",
    "description": "Uno-compatible board using the previously calibrated transparent top-view image.",
    "grid_width": 12,
    "grid_height": 8,
    "pixel_width": 580,
    "pixel_height": 417,
    "license_status": "needs_review",
    "trademark_notes": "Source image includes Arduino-compatible board markings; replace with clean self-generated artwork before public production use.",
    "status": "ready"
  },
  {
    "slug": "arduino-nano",
    "display_name": "Arduino Nano",
    "category": "controller",
    "board_family": "arduino",
    "description": "Nano-compatible board calibrated from the uploaded top-view image.",
    "grid_width": 10,
    "grid_height": 4,
    "pixel_width": 498,
    "pixel_height": 220,
    "license_status": "needs_review",
    "trademark_notes": "Source image includes Arduino/Nano markings; replace with clean self-generated artwork before public production use.",
    "status": "ready"
  },
  {
    "slug": "led-5mm-blue",
    "display_name": "Blue LED 5mm",
    "category": "output",
    "board_family": null,
    "description": "Two-lead blue LED calibrated from the uploaded angled image. A true top-view LED asset is still recommended.",
    "grid_width": 2,
    "grid_height": 4,
    "pixel_width": 310,
    "pixel_height": 381,
    "license_status": "needs_review",
    "trademark_notes": null,
    "status": "ready"
  },
  {
    "slug": "pushbutton-6x6",
    "display_name": "6x6 Tactile Pushbutton",
    "category": "input",
    "board_family": null,
    "description": "Four-leg tactile switch calibrated from the uploaded top-view image.",
    "grid_width": 2,
    "grid_height": 2,
    "pixel_width": 183,
    "pixel_height": 235,
    "license_status": "approved",
    "trademark_notes": null,
    "status": "ready"
  },
  {
    "slug": "servo-sg90",
    "display_name": "SG90 Micro Servo",
    "category": "actuator",
    "board_family": null,
    "description": "SG90 micro servo calibrated from the uploaded front/top image; connector pin order follows brown/red/orange wire order.",
    "grid_width": 3,
    "grid_height": 5,
    "pixel_width": 167,
    "pixel_height": 249,
    "license_status": "needs_review",
    "trademark_notes": null,
    "status": "ready"
  },
  {
    "slug": "hc-sr04",
    "display_name": "HC-SR04 Ultrasonic",
    "category": "sensor",
    "board_family": null,
    "description": "HC-SR04 ultrasonic distance sensor calibrated from the uploaded top-view image.",
    "grid_width": 6,
    "grid_height": 3,
    "pixel_width": 502,
    "pixel_height": 292,
    "license_status": "approved",
    "trademark_notes": null,
    "status": "ready"
  }
]$assets$::jsonb) as x(
    slug text,
    display_name text,
    category text,
    board_family text,
    description text,
    grid_width integer,
    grid_height integer,
    pixel_width integer,
    pixel_height integer,
    license_status text,
    trademark_notes text,
    status text
  )
)
insert into public.circuit_component_assets (
  slug, display_name, category, board_family, description,
  grid_width, grid_height, pixel_width, pixel_height,
  license_status, trademark_notes, status
)
select slug, display_name, category, board_family, description,
  grid_width, grid_height, pixel_width, pixel_height,
  license_status, trademark_notes, status
from asset_rows
on conflict (slug) do update
set display_name = excluded.display_name,
    category = excluded.category,
    board_family = excluded.board_family,
    description = excluded.description,
    grid_width = excluded.grid_width,
    grid_height = excluded.grid_height,
    pixel_width = excluded.pixel_width,
    pixel_height = excluded.pixel_height,
    license_status = excluded.license_status,
    trademark_notes = excluded.trademark_notes,
    status = excluded.status,
    updated_at = now();

with image_rows as (
  select * from jsonb_to_recordset($images$[
  {
    "slug": "arduino-uno-r3",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/arduino-uno-r3-top.png",
    "mime_type": "image/png",
    "width_px": 580,
    "height_px": 417
  },
  {
    "slug": "arduino-uno-r3",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/arduino-uno-r3.svg",
    "mime_type": "image/svg+xml",
    "width_px": 580,
    "height_px": 417
  },
  {
    "slug": "arduino-nano",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/arduino-nano-top.png",
    "mime_type": "image/png",
    "width_px": 498,
    "height_px": 220
  },
  {
    "slug": "arduino-nano",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/arduino-nano.svg",
    "mime_type": "image/svg+xml",
    "width_px": 498,
    "height_px": 220
  },
  {
    "slug": "led-5mm-blue",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/led-5mm-blue-top.png",
    "mime_type": "image/png",
    "width_px": 310,
    "height_px": 381
  },
  {
    "slug": "led-5mm-blue",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/led-5mm-blue.svg",
    "mime_type": "image/svg+xml",
    "width_px": 310,
    "height_px": 381
  },
  {
    "slug": "pushbutton-6x6",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/pushbutton-6x6-top.png",
    "mime_type": "image/png",
    "width_px": 183,
    "height_px": 235
  },
  {
    "slug": "pushbutton-6x6",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/pushbutton-6x6.svg",
    "mime_type": "image/svg+xml",
    "width_px": 183,
    "height_px": 235
  },
  {
    "slug": "servo-sg90",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/servo-sg90-top.png",
    "mime_type": "image/png",
    "width_px": 167,
    "height_px": 249
  },
  {
    "slug": "servo-sg90",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/servo-sg90.svg",
    "mime_type": "image/svg+xml",
    "width_px": 167,
    "height_px": 249
  },
  {
    "slug": "hc-sr04",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/hc-sr04-top.png",
    "mime_type": "image/png",
    "width_px": 502,
    "height_px": 292
  },
  {
    "slug": "hc-sr04",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/hc-sr04.svg",
    "mime_type": "image/svg+xml",
    "width_px": 502,
    "height_px": 292
  }
]$images$::jsonb) as x(
    slug text,
    image_kind text,
    storage_path text,
    mime_type text,
    width_px integer,
    height_px integer
  )
)
insert into public.circuit_component_asset_images (component_id, image_kind, storage_path, mime_type, width_px, height_px)
select assets.id, image_rows.image_kind, image_rows.storage_path, image_rows.mime_type, image_rows.width_px, image_rows.height_px
from image_rows
join public.circuit_component_assets assets on assets.slug = image_rows.slug
on conflict (component_id, image_kind) do update
set storage_path = excluded.storage_path,
    mime_type = excluded.mime_type,
    width_px = excluded.width_px,
    height_px = excluded.height_px,
    updated_at = now();

with pin_rows as (
  select * from jsonb_to_recordset($pins$[
  {
    "slug": "arduino-uno-r3",
    "pin_key": "SCL",
    "label": "SCL",
    "signal_type": "i2c",
    "side": "top",
    "x_px": 194,
    "y_px": 46,
    "aliases": [
      "A5"
    ],
    "sort_order": 0
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "SDA",
    "label": "SDA",
    "signal_type": "i2c",
    "side": "top",
    "x_px": 214,
    "y_px": 46,
    "aliases": [
      "A4"
    ],
    "sort_order": 1
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AREF",
    "label": "AREF",
    "signal_type": "analog",
    "side": "top",
    "x_px": 233,
    "y_px": 46,
    "aliases": [],
    "sort_order": 2
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "GND_D",
    "label": "GND",
    "signal_type": "ground",
    "side": "top",
    "x_px": 253,
    "y_px": 46,
    "aliases": [
      "GND"
    ],
    "sort_order": 3
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D13",
    "label": "D13/SCK",
    "signal_type": "spi",
    "side": "top",
    "x_px": 272,
    "y_px": 46,
    "aliases": [
      "13",
      "SCK"
    ],
    "sort_order": 4
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D12",
    "label": "D12/MISO",
    "signal_type": "spi",
    "side": "top",
    "x_px": 291,
    "y_px": 46,
    "aliases": [
      "12",
      "MISO"
    ],
    "sort_order": 5
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D11",
    "label": "D11 PWM/MOSI",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 311,
    "y_px": 46,
    "aliases": [
      "11",
      "MOSI"
    ],
    "sort_order": 6
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D10",
    "label": "D10 PWM/SS",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 331,
    "y_px": 46,
    "aliases": [
      "10",
      "SS"
    ],
    "sort_order": 7
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D9",
    "label": "D9 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 349,
    "y_px": 46,
    "aliases": [
      "9"
    ],
    "sort_order": 8
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D8",
    "label": "D8",
    "signal_type": "digital",
    "side": "top",
    "x_px": 370,
    "y_px": 46,
    "aliases": [
      "8"
    ],
    "sort_order": 9
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D7",
    "label": "D7",
    "signal_type": "digital",
    "side": "top",
    "x_px": 401,
    "y_px": 46,
    "aliases": [
      "7"
    ],
    "sort_order": 10
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D6",
    "label": "D6 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 420,
    "y_px": 46,
    "aliases": [
      "6"
    ],
    "sort_order": 11
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D5",
    "label": "D5 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 439,
    "y_px": 46,
    "aliases": [
      "5"
    ],
    "sort_order": 12
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D4",
    "label": "D4",
    "signal_type": "digital",
    "side": "top",
    "x_px": 459,
    "y_px": 46,
    "aliases": [
      "4"
    ],
    "sort_order": 13
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D3",
    "label": "D3 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 479,
    "y_px": 46,
    "aliases": [
      "3"
    ],
    "sort_order": 14
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D2",
    "label": "D2",
    "signal_type": "digital",
    "side": "top",
    "x_px": 498,
    "y_px": 46,
    "aliases": [
      "2"
    ],
    "sort_order": 15
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D1",
    "label": "D1/TX",
    "signal_type": "uart",
    "side": "top",
    "x_px": 518,
    "y_px": 46,
    "aliases": [
      "1",
      "TX"
    ],
    "sort_order": 16
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "D0",
    "label": "D0/RX",
    "signal_type": "uart",
    "side": "top",
    "x_px": 537,
    "y_px": 46,
    "aliases": [
      "0",
      "RX"
    ],
    "sort_order": 17
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "IOREF",
    "label": "IOREF",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 262,
    "y_px": 370,
    "aliases": [],
    "sort_order": 100
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "RESET",
    "label": "RESET",
    "signal_type": "digital",
    "side": "bottom",
    "x_px": 282,
    "y_px": 370,
    "aliases": [
      "RST"
    ],
    "sort_order": 101
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "3V3",
    "label": "3.3V",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 302,
    "y_px": 370,
    "aliases": [],
    "sort_order": 102
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "5V",
    "label": "5V",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 321,
    "y_px": 371,
    "aliases": [],
    "sort_order": 103
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "GND_P1",
    "label": "GND",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 342,
    "y_px": 371,
    "aliases": [
      "GND"
    ],
    "sort_order": 104
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "GND_P2",
    "label": "GND",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 359,
    "y_px": 371,
    "aliases": [
      "GND"
    ],
    "sort_order": 105
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "VIN",
    "label": "VIN",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 379,
    "y_px": 372,
    "aliases": [],
    "sort_order": 106
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A0",
    "label": "A0",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 438,
    "y_px": 371,
    "aliases": [],
    "sort_order": 200
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A1",
    "label": "A1",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 457,
    "y_px": 372,
    "aliases": [],
    "sort_order": 201
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A2",
    "label": "A2",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 478,
    "y_px": 372,
    "aliases": [],
    "sort_order": 202
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A3",
    "label": "A3",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 497,
    "y_px": 372,
    "aliases": [],
    "sort_order": 203
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A4",
    "label": "A4/SDA",
    "signal_type": "i2c",
    "side": "bottom",
    "x_px": 518,
    "y_px": 372,
    "aliases": [
      "SDA"
    ],
    "sort_order": 204
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "A5",
    "label": "A5/SCL",
    "signal_type": "i2c",
    "side": "bottom",
    "x_px": 537,
    "y_px": 372,
    "aliases": [
      "SCL"
    ],
    "sort_order": 205
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_RX",
    "label": "RX",
    "signal_type": "uart",
    "side": "right",
    "x_px": 503,
    "y_px": 275,
    "aliases": [
      "D0",
      "RX"
    ],
    "sort_order": 300
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_TX",
    "label": "TX",
    "signal_type": "uart",
    "side": "right",
    "x_px": 520,
    "y_px": 275,
    "aliases": [
      "D1",
      "TX"
    ],
    "sort_order": 301
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_5V",
    "label": "5V",
    "signal_type": "power",
    "side": "right",
    "x_px": 541,
    "y_px": 275,
    "aliases": [
      "5V"
    ],
    "sort_order": 302
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_GND_1",
    "label": "GND",
    "signal_type": "ground",
    "side": "right",
    "x_px": 560,
    "y_px": 275,
    "aliases": [
      "GND"
    ],
    "sort_order": 303
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_SDA",
    "label": "SDA",
    "signal_type": "i2c",
    "side": "right",
    "x_px": 503,
    "y_px": 295,
    "aliases": [
      "A4",
      "SDA"
    ],
    "sort_order": 304
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_SCL",
    "label": "SCL",
    "signal_type": "i2c",
    "side": "right",
    "x_px": 521,
    "y_px": 295,
    "aliases": [
      "A5",
      "SCL"
    ],
    "sort_order": 305
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_3V3",
    "label": "3.3V",
    "signal_type": "power",
    "side": "right",
    "x_px": 540,
    "y_px": 295,
    "aliases": [
      "3V3"
    ],
    "sort_order": 306
  },
  {
    "slug": "arduino-uno-r3",
    "pin_key": "AUX_GND_2",
    "label": "GND",
    "signal_type": "ground",
    "side": "right",
    "x_px": 560,
    "y_px": 295,
    "aliases": [
      "GND"
    ],
    "sort_order": 307
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D12",
    "label": "D12/MISO",
    "signal_type": "spi",
    "side": "top",
    "x_px": 67,
    "y_px": 22,
    "aliases": [
      "12",
      "MISO"
    ],
    "sort_order": 0
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D11",
    "label": "D11 PWM/MOSI",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 93,
    "y_px": 22,
    "aliases": [
      "11",
      "MOSI"
    ],
    "sort_order": 1
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D10",
    "label": "D10 PWM/SS",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 120,
    "y_px": 22,
    "aliases": [
      "10",
      "SS"
    ],
    "sort_order": 2
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D9",
    "label": "D9 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 147,
    "y_px": 22,
    "aliases": [
      "9"
    ],
    "sort_order": 3
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D8",
    "label": "D8",
    "signal_type": "digital",
    "side": "top",
    "x_px": 175,
    "y_px": 22,
    "aliases": [
      "8"
    ],
    "sort_order": 4
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D7",
    "label": "D7",
    "signal_type": "digital",
    "side": "top",
    "x_px": 201,
    "y_px": 22,
    "aliases": [
      "7"
    ],
    "sort_order": 5
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D6",
    "label": "D6 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 228,
    "y_px": 22,
    "aliases": [
      "6"
    ],
    "sort_order": 6
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D5",
    "label": "D5 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 254,
    "y_px": 22,
    "aliases": [
      "5"
    ],
    "sort_order": 7
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D4",
    "label": "D4",
    "signal_type": "digital",
    "side": "top",
    "x_px": 282,
    "y_px": 22,
    "aliases": [
      "4"
    ],
    "sort_order": 8
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D3",
    "label": "D3 PWM",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 310,
    "y_px": 22,
    "aliases": [
      "3"
    ],
    "sort_order": 9
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D2",
    "label": "D2",
    "signal_type": "digital",
    "side": "top",
    "x_px": 336,
    "y_px": 22,
    "aliases": [
      "2"
    ],
    "sort_order": 10
  },
  {
    "slug": "arduino-nano",
    "pin_key": "GND_2",
    "label": "GND",
    "signal_type": "ground",
    "side": "top",
    "x_px": 364,
    "y_px": 22,
    "aliases": [
      "GND"
    ],
    "sort_order": 11
  },
  {
    "slug": "arduino-nano",
    "pin_key": "RESET_2",
    "label": "RESET",
    "signal_type": "digital",
    "side": "top",
    "x_px": 389,
    "y_px": 22,
    "aliases": [
      "RST",
      "RESET"
    ],
    "sort_order": 12
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D0",
    "label": "D0/RX",
    "signal_type": "uart",
    "side": "top",
    "x_px": 418,
    "y_px": 22,
    "aliases": [
      "0",
      "RX"
    ],
    "sort_order": 13
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D1",
    "label": "D1/TX",
    "signal_type": "uart",
    "side": "top",
    "x_px": 443,
    "y_px": 22,
    "aliases": [
      "1",
      "TX"
    ],
    "sort_order": 14
  },
  {
    "slug": "arduino-nano",
    "pin_key": "D13",
    "label": "D13/SCK",
    "signal_type": "spi",
    "side": "bottom",
    "x_px": 67,
    "y_px": 184,
    "aliases": [
      "13",
      "SCK"
    ],
    "sort_order": 100
  },
  {
    "slug": "arduino-nano",
    "pin_key": "3V3",
    "label": "3.3V",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 93,
    "y_px": 184,
    "aliases": [],
    "sort_order": 101
  },
  {
    "slug": "arduino-nano",
    "pin_key": "AREF",
    "label": "AREF",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 120,
    "y_px": 184,
    "aliases": [],
    "sort_order": 102
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A0",
    "label": "A0",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 147,
    "y_px": 184,
    "aliases": [],
    "sort_order": 103
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A1",
    "label": "A1",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 175,
    "y_px": 184,
    "aliases": [],
    "sort_order": 104
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A2",
    "label": "A2",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 201,
    "y_px": 184,
    "aliases": [],
    "sort_order": 105
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A3",
    "label": "A3",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 228,
    "y_px": 184,
    "aliases": [],
    "sort_order": 106
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A4",
    "label": "A4/SDA",
    "signal_type": "i2c",
    "side": "bottom",
    "x_px": 254,
    "y_px": 184,
    "aliases": [
      "SDA"
    ],
    "sort_order": 107
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A5",
    "label": "A5/SCL",
    "signal_type": "i2c",
    "side": "bottom",
    "x_px": 282,
    "y_px": 184,
    "aliases": [
      "SCL"
    ],
    "sort_order": 108
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A6",
    "label": "A6",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 310,
    "y_px": 184,
    "aliases": [],
    "sort_order": 109
  },
  {
    "slug": "arduino-nano",
    "pin_key": "A7",
    "label": "A7",
    "signal_type": "analog",
    "side": "bottom",
    "x_px": 336,
    "y_px": 184,
    "aliases": [],
    "sort_order": 110
  },
  {
    "slug": "arduino-nano",
    "pin_key": "5V",
    "label": "5V",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 364,
    "y_px": 184,
    "aliases": [],
    "sort_order": 111
  },
  {
    "slug": "arduino-nano",
    "pin_key": "RESET_1",
    "label": "RESET",
    "signal_type": "digital",
    "side": "bottom",
    "x_px": 389,
    "y_px": 184,
    "aliases": [
      "RST",
      "RESET"
    ],
    "sort_order": 112
  },
  {
    "slug": "arduino-nano",
    "pin_key": "GND_1",
    "label": "GND",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 418,
    "y_px": 184,
    "aliases": [
      "GND"
    ],
    "sort_order": 113
  },
  {
    "slug": "arduino-nano",
    "pin_key": "VIN",
    "label": "VIN",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 443,
    "y_px": 184,
    "aliases": [],
    "sort_order": 114
  },
  {
    "slug": "led-5mm-blue",
    "pin_key": "ANODE",
    "label": "Anode +",
    "signal_type": "component",
    "side": "bottom",
    "x_px": 31,
    "y_px": 372,
    "aliases": [
      "A",
      "+",
      "long-leg"
    ],
    "sort_order": 0,
    "notes": "Longer visible lead; inferred as anode."
  },
  {
    "slug": "led-5mm-blue",
    "pin_key": "CATHODE",
    "label": "Cathode -",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 9,
    "y_px": 319,
    "aliases": [
      "K",
      "-",
      "short-leg"
    ],
    "sort_order": 1,
    "notes": "Shorter visible lead; inferred as cathode."
  },
  {
    "slug": "pushbutton-6x6",
    "pin_key": "A1",
    "label": "A1",
    "signal_type": "component",
    "side": "left",
    "x_px": 22,
    "y_px": 15,
    "aliases": [
      "left-top"
    ],
    "sort_order": 0,
    "notes": "Internally common with A2."
  },
  {
    "slug": "pushbutton-6x6",
    "pin_key": "A2",
    "label": "A2",
    "signal_type": "component",
    "side": "left",
    "x_px": 22,
    "y_px": 220,
    "aliases": [
      "left-bottom"
    ],
    "sort_order": 1,
    "notes": "Internally common with A1."
  },
  {
    "slug": "pushbutton-6x6",
    "pin_key": "B1",
    "label": "B1",
    "signal_type": "component",
    "side": "right",
    "x_px": 161,
    "y_px": 15,
    "aliases": [
      "right-top"
    ],
    "sort_order": 2,
    "notes": "Internally common with B2."
  },
  {
    "slug": "pushbutton-6x6",
    "pin_key": "B2",
    "label": "B2",
    "signal_type": "component",
    "side": "right",
    "x_px": 161,
    "y_px": 220,
    "aliases": [
      "right-bottom"
    ],
    "sort_order": 3,
    "notes": "Internally common with B1."
  },
  {
    "slug": "servo-sg90",
    "pin_key": "GND",
    "label": "GND",
    "signal_type": "ground",
    "side": "top",
    "x_px": 71,
    "y_px": 17,
    "aliases": [
      "brown",
      "black",
      "-"
    ],
    "sort_order": 0,
    "notes": "Left connector socket in the uploaded image."
  },
  {
    "slug": "servo-sg90",
    "pin_key": "VCC",
    "label": "VCC",
    "signal_type": "power",
    "side": "top",
    "x_px": 86,
    "y_px": 17,
    "aliases": [
      "5V",
      "red"
    ],
    "sort_order": 1,
    "notes": "Middle connector socket in the uploaded image."
  },
  {
    "slug": "servo-sg90",
    "pin_key": "SIGNAL",
    "label": "Signal",
    "signal_type": "pwm",
    "side": "top",
    "x_px": 101,
    "y_px": 17,
    "aliases": [
      "SIG",
      "PWM",
      "orange",
      "yellow"
    ],
    "sort_order": 2,
    "notes": "Right connector socket in the uploaded image."
  },
  {
    "slug": "hc-sr04",
    "pin_key": "VCC",
    "label": "VCC",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 207,
    "y_px": 238,
    "aliases": [
      "5V"
    ],
    "sort_order": 0
  },
  {
    "slug": "hc-sr04",
    "pin_key": "TRIG",
    "label": "TRIG",
    "signal_type": "digital",
    "side": "bottom",
    "x_px": 237,
    "y_px": 238,
    "aliases": [
      "trigger"
    ],
    "sort_order": 1
  },
  {
    "slug": "hc-sr04",
    "pin_key": "ECHO",
    "label": "ECHO",
    "signal_type": "digital",
    "side": "bottom",
    "x_px": 267,
    "y_px": 238,
    "aliases": [
      "echo"
    ],
    "sort_order": 2
  },
  {
    "slug": "hc-sr04",
    "pin_key": "GND",
    "label": "GND",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 297,
    "y_px": 238,
    "aliases": [
      "GND"
    ],
    "sort_order": 3
  }
]$pins$::jsonb) as x(
    slug text,
    pin_key text,
    label text,
    signal_type text,
    side text,
    x_px numeric,
    y_px numeric,
    aliases jsonb,
    sort_order integer,
    notes text
  )
)
insert into public.circuit_component_pins (component_id, pin_key, label, signal_type, side, x_px, y_px, aliases, notes, sort_order)
select assets.id,
  pin_rows.pin_key,
  pin_rows.label,
  pin_rows.signal_type,
  pin_rows.side,
  pin_rows.x_px,
  pin_rows.y_px,
  array(select jsonb_array_elements_text(coalesce(pin_rows.aliases, '[]'::jsonb))),
  pin_rows.notes,
  pin_rows.sort_order
from pin_rows
join public.circuit_component_assets assets on assets.slug = pin_rows.slug
on conflict (component_id, pin_key) do update
set label = excluded.label,
    signal_type = excluded.signal_type,
    side = excluded.side,
    x_px = excluded.x_px,
    y_px = excluded.y_px,
    aliases = excluded.aliases,
    notes = excluded.notes,
    sort_order = excluded.sort_order,
    updated_at = now();
