import { useEffect, useRef, useState } from "react";
import { Box, Grid3X3 } from "lucide-react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import pinCatalog from "../../assets/all_component_pin_coordinates.json";
import all3dPinAnchors from "../../../../assets_db/3d_models/pin_anchors/all_3d_pin_anchors.json";
import breadboardHalfCoordinates from "../../../../assets_db/db_scripts/pin_coordinates/breadboard-half-pin-coordinates.json";
import { modelRegistry } from "./modelRegistry.js";

const assetBySlug = new Map(modelRegistry.map((asset) => [asset.slug, asset]));
const REAL_WORLD_SCENE_UNITS_PER_METER = 80;
const all3dAnchorsBySlug = new Map();

(all3dPinAnchors.anchors ?? []).forEach((anchor) => {
  if (!all3dAnchorsBySlug.has(anchor.slug)) {
    all3dAnchorsBySlug.set(anchor.slug, new Map());
  }
  all3dAnchorsBySlug.get(anchor.slug).set(
    anchor.pin_key,
    new THREE.Vector3(anchor.x_3d, anchor.y_3d, anchor.z_3d),
  );
});

const modelProfiles = {
  "arduino-uno-r3": {
    longestSide: 5.6,
    rotation: [-Math.PI / 2, 0, 0],
    pinLayout: "board",
  },
  "breadboard-full": {
    longestSide: 18,
    rotation: [0, 0, 0],
    pinLayout: "breadboard",
  },
  "breadboard-half": {
    longestSide: 6.4,
    rotation: [0, 0, 0],
    pinLayout: "breadboard",
  },
  "hc-sr04": {
    longestSide: 3.6,
    rotation: [0, 0, 0],
    pinLayout: "sensor",
  },
  "led-5mm-blue": {
    longestSide: 2.2,
    rotation: [0, 0, 0],
    pinLayout: "led",
  },
  "led-5mm-red": {
    longestSide: 2.2,
    rotation: [0, 0, 0],
    pinLayout: "led",
  },
  "resistor-220-ohm": {
    longestSide: 2.8,
    rotation: [0, 0, 0],
    pinLayout: "resistor",
  },
  "pushbutton-6x6": {
    longestSide: 1.8,
    rotation: [0, 0, 0],
    pinLayout: "switch",
  },
};

const SCENE_UNITS_PER_METER = REAL_WORLD_SCENE_UNITS_PER_METER;
const assemblyCalibration = {
  arduinoUno: {
    fixedX: -10.2,
    digitalJumperSocketOffset: new THREE.Vector3(0, -0.3, -0.22),
    powerJumperSocketOffset: new THREE.Vector3(0, -0.3, 0.18),
  },
  led: {
    anchorPin: "ANODE",
    breadboardPitchOffset: -0.5,
  },
  pushbutton: {
    yPitchOffset: 0,
    zPitchOffset: -3,
  },
};
const arduinoPowerHeaderPins = new Set([
  "IOREF",
  "RESET",
  "3V3",
  "5V",
  "GND_P1",
  "GND_P2",
  "VIN",
]);
const breadboardInsertYOffset = {
  "hc-sr04": 0,
  "led-5mm-blue": -0.8,
  "led-5mm-red": -0.8,
  "pushbutton-6x6": -0.08,
  "resistor-220-ohm": -0.05,
};
const breadboardRuntime = breadboardHalfCoordinates.runtime_procedural;
const breadboardRailRuntime = breadboardHalfCoordinates.rail_runtime;

function assemblyCoordinate(value = 0) {
  const numeric = Number(value ?? 0);
  return Math.abs(numeric) <= 1 ? numeric * SCENE_UNITS_PER_METER : numeric;
}

function assemblyVectorToScene(vector = {}) {
  return new THREE.Vector3(
    assemblyCoordinate(vector.x),
    assemblyCoordinate(vector.y),
    assemblyCoordinate(vector.z),
  );
}

function avoidBreadboardOverlap(position, part, placement) {
  if (placement?.mode !== "free" || part.componentKey !== "arduino-uno-r3") {
    return position;
  }
  const adjusted = position.clone();
  adjusted.x = Math.min(adjusted.x, assemblyCalibration.arduinoUno.fixedX);
  return adjusted;
}

function makeFallbackPart(component, index) {
  return {
    id: component.instanceId,
    label: component.label,
    componentKey: component.assetSlug,
    position: { x: index * 160, y: 120 },
    width: 120,
  };
}

function getAssemblyItems(circuit) {
  const plan = circuit?.assemblyPlan;
  if (!plan?.components?.length) {
    return (circuit?.parts ?? []).map((part) => ({ part, placement: null }));
  }

  const placementsById = new Map(
    (plan.placements ?? []).map((placement) => [placement.componentId, placement]),
  );
  return plan.components.map((component, index) => ({
    part: makeFallbackPart(component, index),
    placement: placementsById.get(component.instanceId) ?? null,
  }));
}

function breadboardHoleLocalPosition(address) {
  if (!address) return null;
  const normalized = String(address).trim().toUpperCase();
  const terminal = normalized.match(/^([A-J])([1-9]|[12][0-9]|30)$/);
  if (terminal) {
    const [, row, columnText] = terminal;
    const column = Number(columnText);
    return new THREE.Vector3(
      (breadboardRuntime.columns.x_start_meter + (column - 1) * breadboardRuntime.columns.x_pitch_meter) * SCENE_UNITS_PER_METER,
      breadboardRuntime.surface_y_meter * SCENE_UNITS_PER_METER + 0.08,
      breadboardRuntime.rows_z_meter[row] * SCENE_UNITS_PER_METER,
    );
  }

  const shortRail = normalized.match(/^([TB])([+-])([1-9]|1[0-9]|2[0-5])$/);
  if (shortRail) {
    const [, side, polarity, indexText] = shortRail;
    const index = Number(indexText);
    const segment = Math.floor((index - 1) / 5) + 1;
    const hole = ((index - 1) % 5) + 1;
    const railName = `${side === "T" ? "TOP" : "BOTTOM"}_${polarity === "+" ? "POS" : "NEG"}`;
    return railHoleLocalPosition(railName, segment, hole);
  }

  const rail = normalized.match(/^RAIL_(TOP|BOTTOM)_(POS|NEG)_S([1-5])_([1-5])$/);
  if (rail) {
    const [, side, polarity, segmentText, holeText] = rail;
    return railHoleLocalPosition(`${side}_${polarity}`, Number(segmentText), Number(holeText));
  }

  return null;
}

function averageBreadboardAddressPosition(addresses = {}) {
  const positions = Object.values(addresses)
    .map((address) => breadboardHoleLocalPosition(address))
    .filter(Boolean);
  if (!positions.length) return null;
  return positions
    .reduce((sum, position) => sum.add(position), new THREE.Vector3())
    .multiplyScalar(1 / positions.length);
}

function firstBreadboardAddressPosition(addresses = {}) {
  const firstAddress = addresses[assemblyCalibration.led.anchorPin] ?? Object.values(addresses)[0];
  return breadboardHoleLocalPosition(firstAddress);
}

function railHoleLocalPosition(railName, segment, hole) {
  const z = breadboardRailRuntime.rows_z_meter[railName];
  if (typeof z !== "number") return null;
  return new THREE.Vector3(
    (breadboardRailRuntime.x_start_meter
      + (segment - 1) * breadboardRailRuntime.segment_pitch_meter
      + (hole - 1) * breadboardRailRuntime.hole_pitch_meter) * SCENE_UNITS_PER_METER,
    breadboardRailRuntime.surface_y_meter * SCENE_UNITS_PER_METER + 0.08,
    z * SCENE_UNITS_PER_METER,
  );
}

function disposeObject(root) {
  root.traverse((object) => {
    object.geometry?.dispose?.();
    const materials = Array.isArray(object.material)
      ? object.material
      : [object.material];
    materials.forEach((material) => {
      if (!material) return;
      Object.values(material).forEach((value) => value?.isTexture && value.dispose());
      material.dispose?.();
    });
  });
}

function normalizedPartPosition(part, bounds) {
  const centerX = Number(part.position?.x ?? 0) + Number(part.width ?? 120) / 2;
  const centerY = Number(part.position?.y ?? 0) + 55;
  return new THREE.Vector3(
    (centerX - bounds.centerX) * bounds.scale,
    0,
    (centerY - bounds.centerY) * bounds.scale,
  );
}

function getLayoutBounds(parts) {
  const centers = parts.map((part, index) => ({
    x: Number(part.position?.x ?? index * 220) + Number(part.width ?? 120) / 2,
    y: Number(part.position?.y ?? (index % 2) * 180) + 55,
  }));
  const xs = centers.map((point) => point.x);
  const ys = centers.map((point) => point.y);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const largestSpan = Math.max(maxX - minX, maxY - minY, 400);

  return {
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
    scale: Math.min(0.017, 10.5 / largestSpan),
  };
}

function prepareModel(gltf, part, asset, layoutBounds, placement = null) {
  const profile = modelProfiles[part.componentKey] ?? {
    longestSide: 3,
    rotation: [0, 0, 0],
    pinLayout: "generic",
  };
  const group = new THREE.Group();
  group.name = part.id;

  const model = gltf.scene;
  model.rotation.set(...profile.rotation);
  model.updateMatrixWorld(true);

  const pinAnchors = new Map();
  const pinModelPositions = new Map(all3dAnchorsBySlug.get(part.componentKey) ?? []);
  (asset.metadata?.pins ?? []).forEach((pin) => {
    if (!pin.pinKey || !Array.isArray(pin.position)) return;
    pinModelPositions.set(
      pin.pinKey,
      new THREE.Vector3(pin.position[0], pin.position[1], pin.position[2]),
    );
  });
  const pinKeyByNodeName = new Map(
    (asset.metadata?.pins ?? [])
      .filter((pin) => pin.nodeName && pin.pinKey)
      .map((pin) => [pin.nodeName, pin.pinKey]),
  );
  model.traverse((object) => {
    const pinKey = object.userData?.pinKey ?? pinKeyByNodeName.get(object.name);
    if (pinKey) pinAnchors.set(pinKey, object);
  });
  const isRealWorldAsset = asset.metadata?.asset?.scaleStatus === "real-world"
    && asset.metadata?.coordinateSystems?.runtime?.unit === "meter";
  const hasNormalizedOrigin = Boolean(asset.metadata?.origin?.normalized);

  let modelBounds = new THREE.Box3().setFromObject(model);
  let size = modelBounds.getSize(new THREE.Vector3());
  if (isRealWorldAsset) {
    model.scale.setScalar(REAL_WORLD_SCENE_UNITS_PER_METER);
  } else {
    const longestSide = Math.max(size.x, size.y, size.z, 0.0001);
    model.scale.setScalar(profile.longestSide / longestSide);
  }
  model.updateMatrixWorld(true);

  modelBounds = new THREE.Box3().setFromObject(model);
  if (!hasNormalizedOrigin) {
    const center = modelBounds.getCenter(new THREE.Vector3());
    model.position.x -= center.x;
    model.position.y -= modelBounds.min.y;
    model.position.z -= center.z;
  }
  model.updateMatrixWorld(true);

  model.traverse((object) => {
    if (!object.isMesh) return;
    object.castShadow = false;
    object.receiveShadow = false;
  });
  group.add(model);

  modelBounds = new THREE.Box3().setFromObject(model);
  size = modelBounds.getSize(new THREE.Vector3());
  const addressPosition = placement?.mode === "breadboard"
    ? (part.componentKey.startsWith("led-")
      ? firstBreadboardAddressPosition(placement.addresses)
      : averageBreadboardAddressPosition(placement.addresses))
    : null;

  if (addressPosition) {
    group.position.copy(addressPosition);
    if (part.componentKey.startsWith("led-")) {
      const holePitch = breadboardRuntime.columns.x_pitch_meter * SCENE_UNITS_PER_METER;
      group.position.x += holePitch * assemblyCalibration.led.breadboardPitchOffset;
    }
    if (part.componentKey === "pushbutton-6x6") {
      const holePitch = breadboardRuntime.columns.x_pitch_meter * SCENE_UNITS_PER_METER;
      group.position.y += holePitch * assemblyCalibration.pushbutton.yPitchOffset;
      group.position.z += holePitch * assemblyCalibration.pushbutton.zPitchOffset;
    }
    group.position.y += breadboardInsertYOffset[part.componentKey] ?? 0;
  } else if (placement?.transform?.position) {
    group.position.copy(
      avoidBreadboardOverlap(
        assemblyVectorToScene(placement.transform.position),
        part,
        placement,
      ),
    );
  } else {
    group.position.copy(normalizedPartPosition(part, layoutBounds));
  }

  if (placement?.transform) {
    const rotation = placement.transform.rotation ?? {};
    group.rotation.set(
      Number(rotation.x ?? 0),
      Number(rotation.y ?? 0),
      Number(rotation.z ?? 0),
    );
    const scale = placement.transform.scale ?? {};
    group.scale.set(
      Number(scale.x ?? 1),
      Number(scale.y ?? 1),
      Number(scale.z ?? 1),
    );
  }

  return {
    asset,
    group,
    part,
    placement,
    pinAnchors,
    pinModelPositions,
    pinLayout: profile.pinLayout,
    model,
    size,
  };
}

function findPinDefinition(record, pinKey) {
  const componentPins = pinCatalog[record.part.componentKey]?.pins ?? [];
  return componentPins.find((pin) => pin.pin_key === pinKey) ?? null;
}

function pinLocalPosition(record, pinKey) {
  const { part, pinLayout, size } = record;
  const definition = findPinDefinition(record, pinKey);
  const component = pinCatalog[part.componentKey];
  const xRatio = definition && component?.pixel_width
    ? definition.x_px / component.pixel_width - 0.5
    : 0;
  const yRatio = definition && component?.pixel_height
    ? definition.y_px / component.pixel_height - 0.5
    : 0;

  if (pinLayout === "board") {
    return new THREE.Vector3(xRatio * size.x, size.y + 0.08, yRatio * size.z);
  }
  if (pinLayout === "sensor") {
    return new THREE.Vector3(xRatio * size.x, 0.12, size.z * 0.42);
  }
  if (pinLayout === "led") {
    const direction = pinKey === "ANODE" ? 1 : -1;
    return new THREE.Vector3(direction * size.x * 0.22, 0.1, 0);
  }
  if (pinLayout === "resistor") {
    const direction = pinKey === "LEAD_A" ? -1 : 1;
    return new THREE.Vector3(direction * size.x * 0.5, size.y * 0.5, 0);
  }

  return new THREE.Vector3(xRatio * size.x, size.y + 0.08, yRatio * size.z);
}

function pinWorldPosition(record, pinKey) {
  const embeddedAnchor = record.pinAnchors?.get(pinKey);
  if (embeddedAnchor) {
    record.group.updateMatrixWorld(true);
    return embeddedAnchor.getWorldPosition(new THREE.Vector3());
  }

  const modelPosition = record.pinModelPositions?.get(pinKey);
  if (modelPosition) {
    record.model.updateMatrixWorld(true);
    return record.model.localToWorld(modelPosition.clone());
  }

  const position = pinLocalPosition(record, pinKey);
  record.group.updateMatrixWorld(true);
  return record.group.localToWorld(position);
}

function breadboardHoleWorldPosition(recordsById, address) {
  const boardRecord = [...recordsById.values()].find(
    (record) => record.part.componentKey === "breadboard-half",
  );
  const localPosition = breadboardHoleLocalPosition(address);
  if (!boardRecord || !localPosition) return null;
  boardRecord.group.updateMatrixWorld(true);
  return boardRecord.group.localToWorld(localPosition);
}

function endpointWorldPosition(endpoint, recordsById) {
  const addressPosition = breadboardHoleWorldPosition(recordsById, endpoint.address);
  if (addressPosition) return addressPosition;

  const record = recordsById.get(endpoint.componentId);
  if (!record) return null;
  const position = pinWorldPosition(record, endpoint.pin);
  if (record.part.componentKey === "arduino-uno-r3") {
    position.add(
      arduinoPowerHeaderPins.has(endpoint.pin)
        ? assemblyCalibration.arduinoUno.powerJumperSocketOffset
        : assemblyCalibration.arduinoUno.digitalJumperSocketOffset,
    );
  }
  return position;
}

function normalizeAssemblyConnection(connection) {
  const sourceConnector = "male";
  const targetConnector = "male";
  return {
    id: connection.id,
    source: connection.source?.componentId,
    sourcePin: connection.source?.pin,
    sourceAddress: connection.source?.address,
    target: connection.target?.componentId,
    targetPin: connection.target?.pin,
    targetAddress: connection.target?.address,
    label: `${connection.source?.pin ?? "?"} -> ${connection.target?.pin ?? "?"}`,
    color: connection.color,
    sourceConnector,
    targetConnector,
    wireType: `${sourceConnector}-${targetConnector}`,
  };
}

function makeConnector(position, color, connectorType) {
  const group = new THREE.Group();
  const shell = new THREE.Mesh(
    new THREE.CylinderGeometry(0.075, 0.075, 0.24, 12),
    new THREE.MeshStandardMaterial({
      color: connectorType === "female" ? 0x111827 : color,
      metalness: 0.18,
      roughness: 0.55,
    }),
  );
  shell.position.y = 0.12;
  group.add(shell);

  if (connectorType === "male") {
    const pin = new THREE.Mesh(
      new THREE.CylinderGeometry(0.025, 0.025, 0.46, 10),
      new THREE.MeshStandardMaterial({ color: 0xc8a951, metalness: 0.8, roughness: 0.25 }),
    );
    pin.position.y = -0.25;
    group.add(pin);
  }

  group.position.copy(position);
  return group;
}

function makeWire(connection, source, target, index) {
  const distance = source.distanceTo(target);
  const lift = Math.min(2.4, Math.max(0.65, distance * 0.18)) + (index % 3) * 0.08;
  const sourceRise = source.clone().add(new THREE.Vector3(0, 0.34, 0));
  const targetRise = target.clone().add(new THREE.Vector3(0, 0.34, 0));
  const midpoint = source.clone().lerp(target, 0.5);
  midpoint.y = Math.max(source.y, target.y) + lift;
  const curve = new THREE.CatmullRomCurve3(
    [source, sourceRise, midpoint, targetRise, target],
    false,
    "centripetal",
  );
  const color = new THREE.Color(connection.color || "#2563eb");
  const wire = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 48, 0.035, 8, false),
    new THREE.MeshStandardMaterial({ color, roughness: 0.58, metalness: 0.05 }),
  );
  wire.castShadow = false;

  const group = new THREE.Group();
  group.name = connection.id;
  group.add(wire);
  group.add(makeConnector(source, color, connection.sourceConnector));
  group.add(makeConnector(target, color, connection.targetConnector));
  return group;
}

function wireTypeLabel(wireType) {
  return wireType
    ?.split("-")
    .map((connector) => (connector === "male" ? "수" : connector === "female" ? "암" : connector))
    .join("-");
}

function getDisplayConnections(circuit) {
  return circuit?.assemblyPlan?.connections?.length
    ? circuit.assemblyPlan.connections.map(normalizeAssemblyConnection)
    : (circuit?.connections ?? []);
}

function frameAssembly(camera, controls, assembly, view = "isometric") {
  const bounds = new THREE.Box3().setFromObject(assembly);
  if (bounds.isEmpty()) return;
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z, 1);
  const directions = {
    isometric: new THREE.Vector3(1.15, 1.05, 1.25),
    top: new THREE.Vector3(0, 1, 0.001),
    front: new THREE.Vector3(0, 0.42, 1.35),
    right: new THREE.Vector3(1.35, 0.42, 0),
  };
  const direction = directions[view] ?? directions.isometric;
  camera.position.copy(center).add(direction.normalize().multiplyScalar(radius * 1.12));
  camera.near = 0.02;
  camera.far = Math.max(150, radius * 30);
  camera.up.set(0, 1, 0);
  if (view === "top") camera.up.set(0, 0, -1);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

export default function Circuit3DView({ circuit }) {
  const containerRef = useRef(null);
  const actionsRef = useRef({});
  const gridRef = useRef(null);
  const [showGrid, setShowGrid] = useState(true);
  const [loadState, setLoadState] = useState({ loaded: 0, status: "loading", total: 0 });

  useEffect(() => {
    if (gridRef.current) gridRef.current.visible = showGrid;
  }, [showGrid]);

  useEffect(() => {
    const container = containerRef.current;
    const parts = circuit?.parts ?? [];
    const assemblyItems = getAssemblyItems(circuit);
    if (!container || assemblyItems.length === 0) return undefined;

    let disposed = false;
    let animationFrame = 0;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f8fc);
    scene.fog = new THREE.Fog(0xf5f8fc, 23, 48);

    const camera = new THREE.PerspectiveCamera(38, 1, 0.02, 200);
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.enablePan = true;
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.PAN,
      RIGHT: THREE.MOUSE.PAN,
    };
    controls.minPolarAngle = 0.02;
    controls.maxPolarAngle = Math.PI - 0.02;
    controls.minDistance = 1.2;
    controls.maxDistance = 90;

    scene.add(new THREE.HemisphereLight(0xffffff, 0xa8b5c5, 2.4));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.6);
    keyLight.position.set(-5, 12, 8);
    keyLight.castShadow = false;
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xc7dcff, 1.4);
    fillLight.position.set(8, 5, -7);
    scene.add(fillLight);

    const assembly = new THREE.Group();
    scene.add(assembly);

    const grid = new THREE.GridHelper(40, 40, 0x9cafc4, 0xd7e0ea);
    grid.material.transparent = true;
    grid.material.opacity = 0.58;
    grid.position.y = -0.01;
    grid.visible = showGrid;
    scene.add(grid);
    gridRef.current = grid;

    const resizeObserver = new ResizeObserver(() => {
      const width = Math.max(container.clientWidth, 1);
      const height = Math.max(container.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    });
    resizeObserver.observe(container);

    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(render);
    };
    render();

    const loader = new GLTFLoader();
    const layoutBounds = getLayoutBounds(parts);
    setLoadState({ loaded: 0, status: "loading", total: assemblyItems.length });

    Promise.all(
      assemblyItems.map(async ({ part, placement }) => {
        const asset = assetBySlug.get(part.componentKey);
        if (!asset) throw new Error(`Missing GLB: ${part.componentKey}`);
        const gltf = await loader.loadAsync(asset.url);
        if (disposed) {
          disposeObject(gltf.scene);
          return null;
        }
        const record = prepareModel(gltf, part, asset, layoutBounds, placement);
        assembly.add(record.group);
        setLoadState((current) => ({ ...current, loaded: current.loaded + 1 }));
        return record;
      }),
    )
      .then((records) => {
        if (disposed) return;
        const recordsById = new Map(records.filter(Boolean).map((record) => [record.part.id, record]));
        const wireGroup = new THREE.Group();
        wireGroup.name = "jumper-wires";
        const sourceConnections = circuit.assemblyPlan?.connections?.length
          ? circuit.assemblyPlan.connections.map(normalizeAssemblyConnection)
          : (circuit.connections ?? []);
        sourceConnections.forEach((connection, index) => {
          const source = endpointWorldPosition(
            {
              componentId: connection.source,
              pin: connection.sourcePin,
              address: connection.sourceAddress,
            },
            recordsById,
          );
          const target = endpointWorldPosition(
            {
              componentId: connection.target,
              pin: connection.targetPin,
              address: connection.targetAddress,
            },
            recordsById,
          );
          if (!source || !target) return;
          wireGroup.add(
            makeWire(
              connection,
              source,
              target,
              index,
            ),
          );
        });
        assembly.add(wireGroup);
        frameAssembly(camera, controls, assembly);
        actionsRef.current = {
          isometric: () => frameAssembly(camera, controls, assembly, "isometric"),
          top: () => frameAssembly(camera, controls, assembly, "top"),
          front: () => frameAssembly(camera, controls, assembly, "front"),
          right: () => frameAssembly(camera, controls, assembly, "right"),
        };
        setLoadState({ loaded: records.length, status: "ready", total: assemblyItems.length });
      })
      .catch((error) => {
        if (disposed) return;
        console.error("3D circuit load failed", error);
        setLoadState((current) => ({ ...current, message: error.message, status: "error" }));
      });

    return () => {
      disposed = true;
      actionsRef.current = {};
      gridRef.current = null;
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [circuit]);

  return (
    <div className="circuit3dWorkspace">
      <div className="circuit3dToolbar">
        <div className="circuit3dTitle">
          <Box size={18} aria-hidden="true" />
          <strong>3D 회로</strong>
          <span>{loadState.loaded}/{loadState.total} 부품</span>
        </div>
        <div className="circuit3dControls">
          <button
            type="button"
            className={showGrid ? "active" : ""}
            title="그리드 표시"
            aria-label="그리드 표시"
            onClick={() => setShowGrid((visible) => !visible)}
          >
            <Grid3X3 size={17} />
          </button>
          <button
            type="button"
            title="위에서 보기"
            aria-label="위에서 보기"
            onClick={() => actionsRef.current.top?.()}
          >
            TOP
          </button>
          <button
            type="button"
            title="아이소메트릭 보기"
            aria-label="아이소메트릭 보기"
            onClick={() => actionsRef.current.isometric?.()}
          >
            ISO
          </button>
          <button
            type="button"
            title="앞에서 보기"
            aria-label="앞에서 보기"
            onClick={() => actionsRef.current.front?.()}
          >
            FRONT
          </button>
          <button
            type="button"
            title="오른쪽에서 보기"
            aria-label="오른쪽에서 보기"
            onClick={() => actionsRef.current.right?.()}
          >
            RIGHT
          </button>
        </div>
      </div>

      <div className="circuit3dCanvas" ref={containerRef}>
        {loadState.status !== "ready" && (
          <div className={`circuit3dState ${loadState.status}`}>
            <strong>{loadState.status === "error" ? "회로도를 그리지 못했습니다" : "3D 회로 조립 중"}</strong>
            <span>{loadState.message ?? `${loadState.loaded}/${loadState.total} 부품 불러오는 중`}</span>
          </div>
        )}
      </div>

      <div className="circuit3dLegend" aria-label="3D 점퍼선 연결 목록">
        {getDisplayConnections(circuit).map((connection) => (
          <div className="circuit3dLegendItem" key={connection.id} title={connection.label}>
            <span style={{ backgroundColor: connection.color }} />
            <b>
              {connection.sourcePin}
              {connection.sourceAddress ? ` @ ${connection.sourceAddress}` : ""}
              {" ↔ "}
              {connection.targetPin}
              {connection.targetAddress ? ` @ ${connection.targetAddress}` : ""}
            </b>
            <small>{wireTypeLabel(connection.wireType)}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
