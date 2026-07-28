import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import * as THREE from "../../frontend/node_modules/three/build/three.module.js";
import { GLTFExporter } from "../../frontend/node_modules/three/examples/jsm/exporters/GLTFExporter.js";

globalThis.FileReader ??= class FileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((value) => {
      this.result = value;
      this.onloadend?.();
    }).catch((error) => this.onerror?.(error));
  }

  readAsDataURL(blob) {
    blob.arrayBuffer().then((value) => {
      this.result = `data:${blob.type};base64,${Buffer.from(value).toString("base64")}`;
      this.onloadend?.();
    }).catch((error) => this.onerror?.(error));
  }
};

const repoRoot = path.resolve(import.meta.dirname, "../..");
const glbDir = path.join(repoRoot, "assets_db/3d_models/glb");
const metadataDir = path.join(repoRoot, "assets_db/3d_models/component_metadata/candidates");
const catalogPaths = [
  path.join(repoRoot, "assets_db/db_scripts/all_component_pin_coordinates.json"),
  path.join(repoRoot, "frontend/src/assets/all_component_pin_coordinates.json"),
];
const meter = 0.001;

const material = (name, color, options = {}) => new THREE.MeshStandardMaterial({
  name,
  color,
  metalness: options.metalness ?? 0.05,
  roughness: options.roughness ?? 0.48,
  transparent: options.transparent ?? false,
  opacity: options.opacity ?? 1,
});

function mesh(name, geometry, mat, position) {
  const value = new THREE.Mesh(geometry, mat);
  value.name = name;
  value.position.set(...position);
  value.castShadow = true;
  value.receiveShadow = true;
  return value;
}

function addAnchor(root, pin) {
  const anchor = new THREE.Object3D();
  anchor.name = pin.nodeName;
  anchor.position.set(...pin.position);
  anchor.userData = {
    pinKey: pin.pinKey,
    connectorGender: "male",
    connectorForm: "lead",
    insertionDepthMillimeter: pin.insertionDepthMillimeter,
    runtimeOutwardAxis: "-Y",
  };
  root.add(anchor);
}

function addLead(root, name, x, z = 0, top = 3 * meter, depth = 6 * meter) {
  root.add(mesh(
    name,
    new THREE.CylinderGeometry(0.25 * meter, 0.25 * meter, top + depth, 10),
    material("tin_plated_lead", 0xb8bec5, { metalness: 0.82, roughness: 0.25 }),
    [x, (top - depth) / 2, z],
  ));
}

function createLed(slug, color) {
  const root = new THREE.Group();
  root.name = slug;
  root.userData = { componentSlug: slug, schemaVersion: "1.0.0", assetStatus: "candidate" };
  root.add(mesh(
    "led_body",
    new THREE.CylinderGeometry(2.5 * meter, 2.5 * meter, 8.6 * meter, 32),
    material(`${slug}_lens`, color, { transparent: true, opacity: 0.72, roughness: 0.22 }),
    [0, 7.3 * meter, 0],
  ));
  root.add(mesh(
    "led_flange",
    new THREE.CylinderGeometry(2.9 * meter, 2.9 * meter, 1 * meter, 32),
    material(`${slug}_flange`, color, { transparent: true, opacity: 0.78, roughness: 0.3 }),
    [0, 2.5 * meter, 0],
  ));
  addLead(root, "anode_lead", 1.27 * meter, 0, 3 * meter, 8 * meter);
  addLead(root, "cathode_lead", -1.27 * meter, 0, 3 * meter, 6 * meter);
  return {
    root,
    dimensions: [5.8, 5.8, 19.6],
    pins: [
      pin("ANODE", "Anode +", 1.27, 0, ["A", "+", "long-leg"], "passive"),
      pin("CATHODE", "Cathode -", -1.27, 0, ["K", "-", "short-leg"], "passive"),
    ],
    marker: { key: "anode-right", pinKey: "ANODE", direction: "+X", description: "The longer anode lead is on runtime +X." },
    occupancy: { columns: 2, rows: 1, pitchMillimeter: 2.54 },
  };
}

function createRgbLed() {
  const slug = "led-rgb-5mm";
  const root = new THREE.Group();
  root.name = slug;
  root.userData = { componentSlug: slug, schemaVersion: "1.0.0", assetStatus: "candidate" };
  root.add(mesh(
    "rgb_led_body",
    new THREE.CylinderGeometry(2.5 * meter, 2.5 * meter, 8.6 * meter, 32),
    material("rgb_diffused_lens", 0xe7edf4, { transparent: true, opacity: 0.68, roughness: 0.25 }),
    [0, 7.3 * meter, 0],
  ));
  root.add(mesh(
    "rgb_led_flange",
    new THREE.CylinderGeometry(2.9 * meter, 2.9 * meter, 1 * meter, 32),
    material("rgb_led_flange", 0xd9e2ec, { transparent: true, opacity: 0.75 }),
    [0, 2.5 * meter, 0],
  ));
  const definitions = [
    ["RED", "Red channel", -3.81, ["R"], "signal"],
    ["COMMON_CATHODE", "Common cathode", -1.27, ["COM", "K", "-"], "ground"],
    ["GREEN", "Green channel", 1.27, ["G"], "signal"],
    ["BLUE", "Blue channel", 3.81, ["B"], "signal"],
  ];
  definitions.forEach(([key], index) => addLead(
    root,
    `${key.toLowerCase()}_lead`,
    [-3.81, -1.27, 1.27, 3.81][index] * meter,
    0,
    3 * meter,
    key === "COMMON_CATHODE" ? 6 * meter : 7 * meter,
  ));
  return {
    root,
    dimensions: [8.12, 5.8, 19.6],
    pins: definitions.map(([key, label, x, aliases, role]) => pin(key, label, x, 0, aliases, role)),
    marker: { key: "red-left", pinKey: "RED", direction: "-X", description: "The red channel lead is on runtime -X." },
    occupancy: { columns: 4, rows: 1, pitchMillimeter: 2.54 },
  };
}

function createPotentiometer() {
  const slug = "potentiometer-10k";
  const root = new THREE.Group();
  root.name = slug;
  root.userData = { componentSlug: slug, schemaVersion: "1.0.0", assetStatus: "candidate" };
  root.add(mesh("pot_body", new THREE.BoxGeometry(9.5 * meter, 6.2 * meter, 9.5 * meter), material("pot_blue", 0x2563a8), [0, 5.8 * meter, 0]));
  root.add(mesh("pot_knob", new THREE.CylinderGeometry(2.4 * meter, 2.4 * meter, 3 * meter, 24), material("pot_knob", 0xd8dde3), [0, 10.4 * meter, 0]));
  root.add(mesh("pot_slot", new THREE.BoxGeometry(0.7 * meter, 0.3 * meter, 3.2 * meter), material("pot_slot", 0x60666d), [0, 11.95 * meter, 0]));
  [-2.54, 0, 2.54].forEach((x, index) => addLead(root, `pot_lead_${index + 1}`, x * meter));
  return {
    root,
    dimensions: [9.5, 9.5, 13.45],
    pins: [
      pin("CCW", "Counter-clockwise terminal", -2.54, 0, ["A", "1"], "passive"),
      pin("WIPER", "Wiper", 0, 0, ["W", "2", "SIG"], "signal"),
      pin("CW", "Clockwise terminal", 2.54, 0, ["B", "3"], "passive"),
    ],
    marker: { key: "wiper-center", pinKey: "WIPER", direction: "+Z", description: "The wiper is the center lead." },
    occupancy: { columns: 3, rows: 4, pitchMillimeter: 2.54 },
  };
}

function createSlideSwitch() {
  const slug = "slide-switch-spdt";
  const root = new THREE.Group();
  root.name = slug;
  root.userData = { componentSlug: slug, schemaVersion: "1.0.0", assetStatus: "candidate" };
  root.add(mesh("switch_body", new THREE.BoxGeometry(12 * meter, 5 * meter, 6 * meter), material("switch_black", 0x20252b), [0, 5.5 * meter, 0]));
  root.add(mesh("switch_plate", new THREE.BoxGeometry(13 * meter, 0.8 * meter, 7 * meter), material("switch_metal", 0xa7afb8, { metalness: 0.72, roughness: 0.3 }), [0, 8.2 * meter, 0]));
  root.add(mesh("switch_slider", new THREE.BoxGeometry(4 * meter, 3 * meter, 3 * meter), material("switch_slider", 0x374151), [-2.5 * meter, 10.1 * meter, 0]));
  [-2.54, 0, 2.54].forEach((x, index) => addLead(root, `switch_lead_${index + 1}`, x * meter));
  return {
    root,
    dimensions: [13, 7, 13.1],
    pins: [
      pin("THROW_A", "Throw A", -2.54, 0, ["A", "1"], "signal"),
      pin("COMMON", "Common", 0, 0, ["COM", "2"], "signal"),
      pin("THROW_B", "Throw B", 2.54, 0, ["B", "3"], "signal"),
    ],
    marker: { key: "throw-a-left", pinKey: "THROW_A", direction: "-X", description: "Throw A is the runtime -X lead." },
    occupancy: { columns: 3, rows: 3, pitchMillimeter: 2.54 },
  };
}

function pin(pinKey, label, xMillimeter, zMillimeter, aliases, role) {
  return {
    pinKey,
    label,
    nodeName: `pin_${pinKey.toLowerCase()}`,
    position: [xMillimeter * meter, 0, zMillimeter * meter],
    outwardDirection: [0, -1, 0],
    connector: { gender: "male", form: "lead", pitchMillimeter: 2.54, diameterMillimeter: 0.5 },
    electrical: { role, aliases },
    mounting: { breadboardCompatible: true, insertionDepthMillimeter: 6 },
    insertionDepthMillimeter: 6,
    confidence: 0.95,
    sourceObject: `pin_${pinKey.toLowerCase()}`,
    notes: ["Procedural anchor at the measured 2.54 mm breadboard grid position."],
  };
}

function metadataFor(slug, definition, sha256) {
  const [width, depth, height] = definition.dimensions;
  return {
    schemaVersion: "1.0.0",
    componentSlug: slug,
    asset: {
      path: `assets_db/3d_models/glb/${slug}.glb`,
      sha256,
      format: "glb",
      scaleStatus: "real-world",
      thumbnailPath: null,
    },
    physicalDimensions: {
      unit: "millimeter",
      width,
      depth,
      height,
      measurementScope: "overall-including-pins",
      source: "nominal",
      confidence: 0.9,
    },
    coordinateSystems: {
      authoring: { space: "threejs-object-local", handedness: "right", upAxis: "+Y", frontAxis: "+Z", unit: "meter" },
      runtime: { space: "gltf-model-local", handedness: "right", upAxis: "+Y", frontAxis: "+Z", unit: "meter", modelUnitsPerMillimeter: 0.001 },
      anchorsStoredIn: "runtime",
    },
    origin: {
      targetReference: "mounting-surface-center",
      referencePoint: [0, 0, 0],
      normalized: true,
      description: "Origin is centered on the breadboard insertion plane between the outer leads.",
    },
    orientation: { defaultRotationQuaternion: [0, 0, 0, 1], normalized: true, markers: [definition.marker] },
    pins: definition.pins.map(({ insertionDepthMillimeter, ...value }) => value),
    placement: {
      mountingType: "breadboard-insert",
      mountingPlaneNormal: [0, 1, 0],
      rotationPolicy: "snap-yaw",
      allowedYawDegrees: [0, 90, 180, 270],
      keepOutMarginMillimeter: 0.5,
    },
    provenance: {
      authorGithub: "a3222",
      branch: "feat/assets-discrete-io-pack",
      method: "other",
      sourceTool: "Three.js GLTFExporter",
      createdAt: "2026-07-28",
      status: "candidate",
      reviewerGithub: null,
      approvedAt: null,
    },
    notes: [
      `Nominal real-world procedural model; breadboard occupancy ${definition.occupancy.columns} columns x ${definition.occupancy.rows} rows.`,
      "Pin spacing, polarity, and terminal roles are encoded in named GLB nodes and metadata.",
    ],
  };
}

async function exportGlb(root) {
  root.traverse((object) => object.updateMatrix());
  return new Promise((resolve, reject) => {
    new GLTFExporter().parse(root, resolve, reject, {
      binary: true,
      onlyVisible: true,
      trs: true,
    });
  });
}

function catalogEntry(slug, definition) {
  return {
    component_slug: slug,
    display_name: slug.split("-").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "),
    category: slug.includes("led") ? "output" : "input",
    description: "Real-world procedural breadboard component.",
    grid_width: definition.occupancy.columns,
    grid_height: definition.occupancy.rows,
    pixel_width: 100,
    pixel_height: 100,
    image: { path: null, mime_type: null, width_px: 100, height_px: 100, coordinate_origin: "top-left", background: "transparent" },
    pins: definition.pins.map((item, index) => ({
      pin_key: item.pinKey,
      label: item.label,
      signal_type: item.electrical.role,
      side: "bottom",
      x_px: ((index + 1) * 100) / (definition.pins.length + 1),
      y_px: 90,
      aliases: item.electrical.aliases,
      sort_order: index,
    })),
    notes: ["Generated with the discrete I/O pack."],
  };
}

async function main() {
  const definitions = new Map([
    ["led-5mm-blue", createLed("led-5mm-blue", 0x1677ff)],
    ["led-rgb-5mm", createRgbLed()],
    ["potentiometer-10k", createPotentiometer()],
    ["slide-switch-spdt", createSlideSwitch()],
  ]);
  await fs.mkdir(glbDir, { recursive: true });

  for (const [slug, definition] of definitions) {
    definition.pins.forEach((item) => addAnchor(definition.root, item));
    const arrayBuffer = await exportGlb(definition.root);
    const bytes = Buffer.from(arrayBuffer);
    const sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
    await fs.writeFile(path.join(glbDir, `${slug}.glb`), bytes);
    const componentDir = path.join(metadataDir, slug);
    await fs.mkdir(componentDir, { recursive: true });
    await fs.writeFile(
      path.join(componentDir, "metadata.json"),
      `${JSON.stringify(metadataFor(slug, definition, sha256), null, 2)}\n`,
    );
  }

  for (const catalogPath of catalogPaths) {
    const catalog = JSON.parse(await fs.readFile(catalogPath, "utf8"));
    for (const [slug, definition] of definitions) catalog[slug] = catalogEntry(slug, definition);
    await fs.writeFile(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
  }

  const occupancy = Object.fromEntries([...definitions].map(([slug, definition]) => [
    slug,
    {
      pinKeys: definition.pins.map((item) => item.pinKey),
      pitchMillimeter: definition.occupancy.pitchMillimeter,
      occupiedColumns: definition.occupancy.columns,
      occupiedRows: definition.occupancy.rows,
      polarity: slug === "led-5mm-blue"
        ? { positive: "ANODE", negative: "CATHODE" }
        : slug === "led-rgb-5mm"
          ? { common: "COMMON_CATHODE", channels: ["RED", "GREEN", "BLUE"] }
          : null,
    },
  ]));
  const rulesDir = path.join(repoRoot, "assets_db/3d_models/placement_rules");
  await fs.mkdir(rulesDir, { recursive: true });
  await fs.writeFile(
    path.join(rulesDir, "discrete-io-pack.json"),
    `${JSON.stringify({ schemaVersion: "1.0.0", gridPitchMillimeter: 2.54, components: occupancy }, null, 2)}\n`,
  );
}

await main();
