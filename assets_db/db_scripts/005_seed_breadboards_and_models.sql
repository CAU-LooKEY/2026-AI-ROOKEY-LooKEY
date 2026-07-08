-- Seed breadboard assets, procedural breadboard layouts, and selected GLB model metadata.
-- Upload files from assets_db/2d_svgs/raster_sources, assets_db/2d_svgs/react_flow_nodes,
-- and assets_db/3d_models/glb to the Supabase Storage bucket `circuit-assets`
-- using the storage_path values below.

with asset_rows as (
  select * from jsonb_to_recordset($assets$[
  {
    "slug": "breadboard-full",
    "display_name": "Full-size Breadboard",
    "category": "prototyping",
    "board_family": null,
    "description": "Long breadboard layout calibrated from the uploaded top-view image; rails include split segment metadata.",
    "grid_width": 24,
    "grid_height": 8,
    "pixel_width": 1007,
    "pixel_height": 350,
    "license_status": "needs_review",
    "trademark_notes": null,
    "status": "ready"
  },
  {
    "slug": "breadboard-half",
    "display_name": "Half-size Breadboard",
    "category": "prototyping",
    "board_family": null,
    "description": "Procedural breadboard layout calibrated from the uploaded top-view image.",
    "grid_width": 12,
    "grid_height": 8,
    "pixel_width": 367,
    "pixel_height": 247,
    "license_status": "needs_review",
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
    "slug": "breadboard-full",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/breadboard-full-top.png",
    "mime_type": "image/png",
    "width_px": 1007,
    "height_px": 350
  },
  {
    "slug": "breadboard-full",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/breadboard-full.svg",
    "mime_type": "image/svg+xml",
    "width_px": 1007,
    "height_px": 350
  },
  {
    "slug": "breadboard-half",
    "image_kind": "isometric_2d",
    "storage_path": "raster_sources/breadboard-half-top.png",
    "mime_type": "image/png",
    "width_px": 367,
    "height_px": 247
  },
  {
    "slug": "breadboard-half",
    "image_kind": "schematic_2d",
    "storage_path": "react_flow_nodes/breadboard-half.svg",
    "mime_type": "image/svg+xml",
    "width_px": 367,
    "height_px": 247
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

with model_rows as (
  select * from jsonb_to_recordset($models$[
  {
    "slug": "arduino-uno-r3",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/arduino-uno-r3.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "arduino_uno.glb",
    "file_size_bytes": 4491236,
    "sha256": "e5556c7b8c5417121bd6a6d6f80708e86044f965ca9d3865279fe1cca02f4fc9",
    "bounds": {
      "min": [
        -0.6041634910627027,
        -0.37986031128498043,
        0.16593804822606747
      ],
      "max": [
        0.5596647789396831,
        0.4464157889981979,
        0.349629177977125
      ],
      "size": [
        1.1638282700023859,
        0.8262761002831783,
        0.18369112975105753
      ]
    },
    "dimensions": {
      "x": 1.1638282700023859,
      "y": 0.8262761002831783,
      "z": 0.18369112975105753
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected Uno candidate with stable bounds and moderate file size."
  },
  {
    "slug": "arduino-nano",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/arduino-nano.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "arduino_nano (1).glb",
    "file_size_bytes": 2313776,
    "sha256": "1d55ae6423feef21d6854e155ca21da31e0620f0d35debeaafe60861dbc995ec",
    "bounds": {
      "min": [
        -1.4971014102779918,
        2.6058101384642214,
        -0.3714991287306475
      ],
      "max": [
        1.334714153515506,
        5.00892408296022,
        6.912279976355421
      ],
      "size": [
        2.831815563793498,
        2.403113944495999,
        7.283779105086069
      ]
    },
    "dimensions": {
      "x": 2.831815563793498,
      "y": 2.403113944495999,
      "z": 7.283779105086069
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected Nano candidate with plausible board aspect ratio and 2.3 MB size."
  },
  {
    "slug": "breadboard-half",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/breadboard-half.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "breadboard_arduino.glb",
    "file_size_bytes": 1998128,
    "sha256": "a6a53a19dede60c269274886f05b4966ddb5a40dd08f83b1a47c721bca7569a2",
    "bounds": {
      "min": [
        0.21258124709129328,
        -0.29579075426517537,
        0.17433716814463632
      ],
      "max": [
        0.5780577957630157,
        -0.05015984921993204,
        0.19822729666287406
      ],
      "size": [
        0.36547654867172247,
        0.24563090504524332,
        0.02389012851823774
      ]
    },
    "dimensions": {
      "x": 0.36547654867172247,
      "y": 0.24563090504524332,
      "z": 0.02389012851823774
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected regular breadboard candidate with small file size and simple structure."
  },
  {
    "slug": "breadboard-full",
    "model_kind": "candidate_3d",
    "storage_path": "3d_models/glb/breadboard-full.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "breadboard_blender.glb",
    "file_size_bytes": 25283068,
    "sha256": "b9e9ef4e44db22fcf37dcc07714f16a01e1e8e7f4fdb1b217a3d1de4355279c9",
    "bounds": {
      "min": [
        -2.703288565661377,
        0.0008963979780673981,
        -8.25690358842266
      ],
      "max": [
        2.70365066388778,
        0.8048873360144884,
        8.25690358842266
      ],
      "size": [
        5.406939229549157,
        0.803990938036421,
        16.51380717684532
      ]
    },
    "dimensions": {
      "x": 5.406939229549157,
      "y": 0.803990938036421,
      "z": 16.51380717684532
    },
    "unit": "model-unit",
    "audit_status": "needs_optimization",
    "notes": "Valid long breadboard candidate, but about 25 MB; optimize before production web delivery."
  },
  {
    "slug": "hc-sr04",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/hc-sr04.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "hc-sr04.glb",
    "file_size_bytes": 1310040,
    "sha256": "59e486e3173fe311cf685ab61451241b8c1198829c2728d329f04c4f203d8e6b",
    "bounds": {
      "min": [
        -1.2287132735491468,
        -0.07834634256011341,
        -0.3487059473991394
      ],
      "max": [
        1.6345217521429731,
        1.5839607119560242,
        0.7818499892883217
      ],
      "size": [
        2.86323502569212,
        1.6623070545161376,
        1.1305559366874611
      ]
    },
    "dimensions": {
      "x": 2.86323502569212,
      "y": 1.6623070545161376,
      "z": 1.1305559366874611
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected smaller HC-SR04 candidate with valid mesh and texture metadata."
  },
  {
    "slug": "led-5mm-blue",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/led-5mm-blue.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "led_light-emitting_diode.glb",
    "file_size_bytes": 204992,
    "sha256": "22d73261961c68f1dcadda61374bd54728fef02812be26dcdaf8fb99700f6e4e",
    "bounds": {
      "min": [
        -0.7099154650891037,
        -1.2011530950029548,
        -0.23535256324766307
      ],
      "max": [
        0.2403139845835432,
        1.3656709622220875,
        0.23535272745438912
      ],
      "size": [
        0.9502294496726469,
        2.566824057225042,
        0.4707052907020522
      ]
    },
    "dimensions": {
      "x": 0.9502294496726469,
      "y": 2.566824057225042,
      "z": 0.4707052907020522
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected detailed LED candidate."
  },
  {
    "slug": "pushbutton-6x6",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/pushbutton-6x6.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "push_button_6x6x5mm.glb",
    "file_size_bytes": 43928,
    "sha256": "7a925080695029f57df877e8f5d46da6b80d0d92cbb011cd5cfdf35151c67d8b",
    "bounds": {
      "min": [
        -0.003608345054090023,
        -0.005616545211523772,
        -0.004085539840161801
      ],
      "max": [
        0.0036001799162477255,
        0.0037894239649176606,
        0.004076898097991943
      ],
      "size": [
        0.0072085249703377485,
        0.009405969176441433,
        0.008162437938153744
      ]
    },
    "dimensions": {
      "x": 0.0072085249703377485,
      "y": 0.009405969176441433,
      "z": 0.008162437938153744
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected compact 6x6 pushbutton model."
  },
  {
    "slug": "servo-sg90",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/servo-sg90.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "servo_motor_sg_90.glb",
    "file_size_bytes": 376656,
    "sha256": "fc321496fc81d5183b4eda2eca3fc0fe4fec059e2cfe548d028d0152d586ea13",
    "bounds": {
      "min": [
        -0.5124761462211609,
        -0.07357913255691528,
        -1.4787427186965942
      ],
      "max": [
        0.5144802927970886,
        2.589119926095009,
        1.9720511734485626
      ],
      "size": [
        1.0269564390182495,
        2.662699058651924,
        3.450793892145157
      ]
    },
    "dimensions": {
      "x": 1.0269564390182495,
      "y": 2.662699058651924,
      "z": 3.450793892145157
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "Selected SG90 candidate with compact file size."
  },
  {
    "slug": "resistor-220-ohm",
    "model_kind": "production_3d",
    "storage_path": "3d_models/glb/resistor-220-ohm.glb",
    "mime_type": "model/gltf-binary",
    "format": "glb",
    "source_filename": "resistor.glb",
    "file_size_bytes": 167684,
    "sha256": "fd4a5a218cbe116459c61cbb20e4547736e6e13976a2eca6b739f6e293c20d05",
    "bounds": {
      "min": [
        -0.238720898443745,
        0.04055225849151611,
        -0.2580604818399479
      ],
      "max": [
        0.2772341209613387,
        3.1676844358444214,
        0.2578945923955587
      ],
      "size": [
        0.5159550194050837,
        3.1271321773529053,
        0.5159550742355066
      ]
    },
    "dimensions": {
      "x": 0.5159550194050837,
      "y": 3.1271321773529053,
      "z": 0.5159550742355066
    },
    "unit": "model-unit",
    "audit_status": "ready",
    "notes": "User-supplied compact 220 ohm resistor GLB; two non-polarized leads use draft projected anchors."
  }
]$models$::jsonb) as x(
    slug text,
    model_kind text,
    storage_path text,
    mime_type text,
    format text,
    source_filename text,
    file_size_bytes bigint,
    sha256 text,
    bounds jsonb,
    dimensions jsonb,
    unit text,
    audit_status text,
    notes text
  )
)
insert into public.circuit_component_asset_models (
  component_id, model_kind, storage_path, mime_type, format, source_filename,
  file_size_bytes, sha256, bounds, dimensions, unit, audit_status, notes
)
select assets.id, model_rows.model_kind, model_rows.storage_path, model_rows.mime_type, model_rows.format,
  model_rows.source_filename, model_rows.file_size_bytes, model_rows.sha256, model_rows.bounds,
  model_rows.dimensions, model_rows.unit, model_rows.audit_status, model_rows.notes
from model_rows
join public.circuit_component_assets assets on assets.slug = model_rows.slug
on conflict (component_id, model_kind) do update
set storage_path = excluded.storage_path,
    mime_type = excluded.mime_type,
    format = excluded.format,
    source_filename = excluded.source_filename,
    file_size_bytes = excluded.file_size_bytes,
    sha256 = excluded.sha256,
    bounds = excluded.bounds,
    dimensions = excluded.dimensions,
    unit = excluded.unit,
    audit_status = excluded.audit_status,
    notes = excluded.notes,
    updated_at = now();

with layout_rows as (
  select * from jsonb_to_recordset($layouts$[
  {
    "slug": "breadboard-full",
    "layout_kind": "breadboard",
    "hole_coordinate_system": "image-pixel-procedural",
    "column_indexing": "left-to-right",
    "columns": 63,
    "terminal_rows": [
      "A",
      "B",
      "C",
      "D",
      "E",
      "F",
      "G",
      "H",
      "I",
      "J"
    ],
    "terminal": {
      "x_start_px": 43.3,
      "x_pitch_px": 15.0,
      "upper_rows": {
        "labels": [
          "A",
          "B",
          "C",
          "D",
          "E"
        ],
        "y_px": [
          103.6,
          118.7,
          133.8,
          148.9,
          163.9
        ]
      },
      "lower_rows": {
        "labels": [
          "F",
          "G",
          "H",
          "I",
          "J"
        ],
        "y_px": [
          208.7,
          223.7,
          238.8,
          253.9,
          268.9
        ]
      }
    },
    "rails": {
      "top_positive": {
        "label": "+",
        "y_px": 45.9,
        "x_start_px": 65.0,
        "x_pitch_px": 15.0,
        "segments": [
          {
            "start_column": 1,
            "end_column": 29
          },
          {
            "start_column": 31,
            "end_column": 59
          }
        ]
      },
      "top_negative": {
        "label": "-",
        "y_px": 61.2,
        "x_start_px": 65.0,
        "x_pitch_px": 15.0,
        "segments": [
          {
            "start_column": 1,
            "end_column": 29
          },
          {
            "start_column": 31,
            "end_column": 59
          }
        ]
      },
      "bottom_positive": {
        "label": "+",
        "y_px": 311.5,
        "x_start_px": 66.4,
        "x_pitch_px": 15.0,
        "segments": [
          {
            "start_column": 1,
            "end_column": 29
          },
          {
            "start_column": 31,
            "end_column": 59
          }
        ]
      },
      "bottom_negative": {
        "label": "-",
        "y_px": 326.9,
        "x_start_px": 66.4,
        "x_pitch_px": 15.0,
        "segments": [
          {
            "start_column": 1,
            "end_column": 29
          },
          {
            "start_column": 31,
            "end_column": 59
          }
        ]
      }
    },
    "notes": [
      "Procedural layout calibrated from detected hole centers in the uploaded top-view image.",
      "Long breadboard rail split metadata should be used when routing power rails."
    ]
  },
  {
    "slug": "breadboard-half",
    "layout_kind": "breadboard",
    "hole_coordinate_system": "image-pixel-procedural",
    "column_indexing": "left-to-right",
    "columns": 30,
    "terminal_rows": [
      "A",
      "B",
      "C",
      "D",
      "E",
      "F",
      "G",
      "H",
      "I",
      "J"
    ],
    "terminal": {
      "x_start_px": 32.1,
      "x_pitch_px": 10.45,
      "upper_rows": {
        "labels": [
          "A",
          "B",
          "C",
          "D",
          "E"
        ],
        "y_px": [
          69.2,
          79.7,
          90.1,
          100.6,
          110.9
        ]
      },
      "lower_rows": {
        "labels": [
          "F",
          "G",
          "H",
          "I",
          "J"
        ],
        "y_px": [
          142.0,
          152.1,
          162.9,
          173.1,
          183.8
        ]
      }
    },
    "rails": {
      "top_positive": {
        "label": "+",
        "y_px": 28.6,
        "x_groups_px": [
          [
            37.9,
            48.0,
            58.4,
            68.9,
            79.0
          ],
          [
            100.0,
            110.5,
            120.9,
            131.1,
            141.8,
            152.1,
            162.3,
            172.6,
            183.0,
            193.5,
            203.9,
            214.3,
            225.0,
            235.8,
            245.9,
            256.3,
            267.0
          ],
          [
            287.9,
            298.0,
            308.5,
            319.0,
            329.1
          ]
        ]
      },
      "top_negative": {
        "label": "-",
        "y_px": 39.4,
        "x_groups_px": [
          [
            37.9,
            48.0,
            58.4,
            68.9,
            79.0
          ],
          [
            100.0,
            110.5,
            120.9,
            131.1,
            141.8,
            152.1,
            162.3,
            172.6,
            183.0,
            193.5,
            203.9,
            214.3,
            225.0,
            235.8,
            245.9,
            256.3,
            267.0
          ],
          [
            287.9,
            298.0,
            308.5,
            319.0,
            329.1
          ]
        ]
      },
      "bottom_positive": {
        "label": "+",
        "y_px": 214.0,
        "x_groups_px": [
          [
            37.9,
            48.0,
            58.6,
            69.0,
            79.5
          ],
          [
            100.1,
            110.8,
            121.0,
            131.6,
            142.0,
            152.2,
            162.8,
            173.0,
            183.6,
            194.0,
            204.4,
            214.9,
            225.7,
            236.0,
            246.4,
            256.9,
            267.4
          ],
          [
            288.0,
            298.9,
            309.0,
            319.9,
            330.0
          ]
        ]
      },
      "bottom_negative": {
        "label": "-",
        "y_px": 224.5,
        "x_groups_px": [
          [
            37.9,
            48.0,
            58.6,
            69.0,
            79.5
          ],
          [
            100.1,
            110.8,
            121.0,
            131.6,
            142.0,
            152.2,
            162.8,
            173.0,
            183.6,
            194.0,
            204.4,
            214.9,
            225.7,
            236.0,
            246.4,
            256.9,
            267.4
          ],
          [
            288.0,
            298.9,
            309.0,
            319.9,
            330.0
          ]
        ]
      }
    },
    "notes": [
      "Procedural layout calibrated from detected hole centers in the uploaded top-view image.",
      "Do not store every breadboard hole as a DB row; compute holes from x_start, x_pitch, and y row arrays."
    ]
  }
]$layouts$::jsonb) as x(
    slug text,
    layout_kind text,
    hole_coordinate_system text,
    column_indexing text,
    columns integer,
    terminal_rows jsonb,
    terminal jsonb,
    rails jsonb,
    notes jsonb
  )
)
insert into public.circuit_breadboard_layouts (
  component_id, layout_kind, hole_coordinate_system, column_indexing,
  columns, terminal_rows, terminal, rails, notes
)
select assets.id,
  layout_rows.layout_kind,
  layout_rows.hole_coordinate_system,
  layout_rows.column_indexing,
  layout_rows.columns,
  array(select jsonb_array_elements_text(layout_rows.terminal_rows)),
  layout_rows.terminal,
  layout_rows.rails,
  array(select jsonb_array_elements_text(layout_rows.notes))
from layout_rows
join public.circuit_component_assets assets on assets.slug = layout_rows.slug
on conflict (component_id) do update
set layout_kind = excluded.layout_kind,
    hole_coordinate_system = excluded.hole_coordinate_system,
    column_indexing = excluded.column_indexing,
    columns = excluded.columns,
    terminal_rows = excluded.terminal_rows,
    terminal = excluded.terminal,
    rails = excluded.rails,
    notes = excluded.notes,
    updated_at = now();

with pin_rows as (
  select * from jsonb_to_recordset($pins$[
  {
    "slug": "breadboard-full",
    "pin_key": "RAIL_TOP_POS",
    "label": "+ top",
    "signal_type": "power",
    "side": "top",
    "x_px": 65.0,
    "y_px": 45.9,
    "aliases": [
      "+"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 0
  },
  {
    "slug": "breadboard-full",
    "pin_key": "RAIL_TOP_NEG",
    "label": "- top",
    "signal_type": "ground",
    "side": "top",
    "x_px": 65.0,
    "y_px": 61.2,
    "aliases": [
      "-"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 1
  },
  {
    "slug": "breadboard-full",
    "pin_key": "RAIL_BOTTOM_POS",
    "label": "+ bottom",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 66.4,
    "y_px": 311.5,
    "aliases": [
      "+"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 2
  },
  {
    "slug": "breadboard-full",
    "pin_key": "RAIL_BOTTOM_NEG",
    "label": "- bottom",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 66.4,
    "y_px": 326.9,
    "aliases": [
      "-"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 3
  },
  {
    "slug": "breadboard-full",
    "pin_key": "A1",
    "label": "A1",
    "signal_type": "component",
    "side": "center",
    "x_px": 43.3,
    "y_px": 103.6,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 4
  },
  {
    "slug": "breadboard-full",
    "pin_key": "E1",
    "label": "E1",
    "signal_type": "component",
    "side": "center",
    "x_px": 43.3,
    "y_px": 163.9,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 5
  },
  {
    "slug": "breadboard-full",
    "pin_key": "F1",
    "label": "F1",
    "signal_type": "component",
    "side": "center",
    "x_px": 43.3,
    "y_px": 208.7,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 6
  },
  {
    "slug": "breadboard-full",
    "pin_key": "J1",
    "label": "J1",
    "signal_type": "component",
    "side": "center",
    "x_px": 43.3,
    "y_px": 268.9,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 7
  },
  {
    "slug": "breadboard-half",
    "pin_key": "RAIL_TOP_POS",
    "label": "+ top",
    "signal_type": "power",
    "side": "top",
    "x_px": 37.9,
    "y_px": 28.6,
    "aliases": [
      "+"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 0
  },
  {
    "slug": "breadboard-half",
    "pin_key": "RAIL_TOP_NEG",
    "label": "- top",
    "signal_type": "ground",
    "side": "top",
    "x_px": 37.9,
    "y_px": 39.4,
    "aliases": [
      "-"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 1
  },
  {
    "slug": "breadboard-half",
    "pin_key": "RAIL_BOTTOM_POS",
    "label": "+ bottom",
    "signal_type": "power",
    "side": "bottom",
    "x_px": 37.9,
    "y_px": 214.0,
    "aliases": [
      "+"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 2
  },
  {
    "slug": "breadboard-half",
    "pin_key": "RAIL_BOTTOM_NEG",
    "label": "- bottom",
    "signal_type": "ground",
    "side": "bottom",
    "x_px": 37.9,
    "y_px": 224.5,
    "aliases": [
      "-"
    ],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 3
  },
  {
    "slug": "breadboard-half",
    "pin_key": "A1",
    "label": "A1",
    "signal_type": "component",
    "side": "center",
    "x_px": 32.1,
    "y_px": 69.2,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 4
  },
  {
    "slug": "breadboard-half",
    "pin_key": "E1",
    "label": "E1",
    "signal_type": "component",
    "side": "center",
    "x_px": 32.1,
    "y_px": 110.9,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 5
  },
  {
    "slug": "breadboard-half",
    "pin_key": "F1",
    "label": "F1",
    "signal_type": "component",
    "side": "center",
    "x_px": 32.1,
    "y_px": 142.0,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 6
  },
  {
    "slug": "breadboard-half",
    "pin_key": "J1",
    "label": "J1",
    "signal_type": "component",
    "side": "center",
    "x_px": 32.1,
    "y_px": 183.8,
    "aliases": [],
    "notes": "Representative breadboard anchor; compute full hole coordinates from circuit_breadboard_layouts.",
    "sort_order": 7
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
