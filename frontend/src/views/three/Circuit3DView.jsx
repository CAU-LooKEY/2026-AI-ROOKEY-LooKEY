import { useEffect, useMemo, useRef, useState } from "react";
import { Box, Eye, EyeOff, Grid3X3, RotateCcw } from "lucide-react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import pinCatalog from "../../assets/all_component_pin_coordinates.json";
import { modelRegistry } from "./modelRegistry.js";
import {
  calculateCurveProfile,
  createPinEndpoint,
  JUMPER_SPEC,
  resolveJumperWire,
} from "./jumperWireSystem.js";

const assetBySlug = new Map(modelRegistry.map((asset) => [asset.slug, asset]));
const REAL_WORLD_SCENE_UNITS_PER_METER = 80;
const CONNECTOR_SHELL_HEIGHT = 0.24;
const CONNECTOR_SEATING_DEPTH = 0.045;

const modelProfiles = {
  "arduino-uno-r3": {
    longestSide: 5.6,
    rotation: [-Math.PI / 2, 0, 0],
    pinLayout: "board",
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

function prepareModel(gltf, part, asset, layoutBounds) {
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
    object.castShadow = true;
    object.receiveShadow = true;
  });
  group.add(model);

  modelBounds = new THREE.Box3().setFromObject(model);
  size = modelBounds.getSize(new THREE.Vector3());
  group.position.copy(normalizedPartPosition(part, layoutBounds));

  return {
    asset,
    group,
    model,
    part,
    pinAnchors,
    pinLayout: profile.pinLayout,
    size,
  };
}

function findPinMetadata(record, pinKey) {
  return record.asset?.metadata?.pins?.find((pin) => pin.pinKey === pinKey) ?? null;
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

  const metadata = findPinMetadata(record, pinKey);
  if (metadata?.position?.length === 3) {
    record.model.updateMatrixWorld(true);
    return record.model.localToWorld(new THREE.Vector3(...metadata.position));
  }

  const position = pinLocalPosition(record, pinKey);
  record.group.updateMatrixWorld(true);
  return record.group.localToWorld(position);
}

function pinWorldDirection(record, endpoint) {
  // Catalog-only board pins do not have an exported GLB direction. Their
  // positions are already resolved in the assembled scene, so keep the
  // insertion axis in world space instead of rotating the fallback vector
  // with the GLB (Arduino models are laid down with an X-axis rotation).
  if (!endpoint.metadata?.outwardDirection && record.pinLayout === "board") {
    return new THREE.Vector3(0, 1, 0);
  }

  const direction = new THREE.Vector3(...endpoint.outwardDirection);
  if (direction.lengthSq() < 0.0001) direction.set(0, 1, 0);
  direction.normalize();
  record.model.updateMatrixWorld(true);
  direction.transformDirection(record.model.matrixWorld).normalize();
  return direction;
}

function getSelectablePinKeys(record) {
  const metadataKeys = (record.asset?.metadata?.pins ?? []).map((pin) => pin.pinKey);
  if (metadataKeys.length) return metadataKeys;
  return (pinCatalog[record.part.componentKey]?.pins ?? []).map((pin) => pin.pin_key);
}

function makePinTarget(record, pinKey) {
  const endpoint = createPinEndpoint(record, pinKey);
  const direction = pinWorldDirection(record, endpoint);
  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(record.part.componentKey.startsWith("breadboard-") ? 0.035 : 0.055, 10, 8),
    new THREE.MeshBasicMaterial({
      color: 0x0ea5e9,
      depthTest: false,
      transparent: true,
      opacity: 0.82,
    }),
  );
  marker.position.copy(pinWorldPosition(record, pinKey)).addScaledVector(direction, 0.045);
  marker.renderOrder = 30;
  marker.userData.pinRef = {
    endpoint,
    pinKey,
    record,
  };
  return marker;
}

function makeConnector(position, direction, color, connectorType, endpoint) {
  const group = new THREE.Group();
  const normalizedDirection = direction.clone().normalize();
  const insertionLength = Math.min(
    0.52,
    Math.max(0.12, Number(endpoint.insertionDepthMillimeter ?? 2) * 0.08),
  );
  const shellMaterial = new THREE.MeshStandardMaterial({
    color: connectorType === "female" ? 0x111827 : color,
    metalness: 0.18,
    roughness: 0.55,
  });
  const shell = new THREE.Mesh(
    new THREE.BoxGeometry(0.15, CONNECTOR_SHELL_HEIGHT, 0.15),
    shellMaterial,
  );
  shell.position.y = CONNECTOR_SHELL_HEIGHT / 2;
  group.add(shell);

  if (connectorType === "male") {
    const pin = new THREE.Mesh(
      new THREE.BoxGeometry(0.032, insertionLength, 0.032),
      new THREE.MeshStandardMaterial({ color: 0xc8a951, metalness: 0.8, roughness: 0.25 }),
    );
    pin.position.y = -insertionLength / 2;
    group.add(pin);
  }

  // Seat male housings slightly below the mating surface. The metal pin then
  // continues into the socket/hole by the requested insertion depth.
  group.position.copy(position);
  if (connectorType === "male") {
    group.position.addScaledVector(normalizedDirection, -CONNECTOR_SEATING_DEPTH);
  }
  group.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normalizedDirection);
  return group;
}

function connectorCablePosition(position, direction, connectorType) {
  const seatingDepth = connectorType === "male" ? CONNECTOR_SEATING_DEPTH : 0;
  return position.clone().addScaledVector(
    direction,
    CONNECTOR_SHELL_HEIGHT - seatingDepth,
  );
}

function makeWire(
  connection,
  source,
  target,
  sourceDirection,
  targetDirection,
  sourceEndpoint,
  targetEndpoint,
  index,
) {
  const sourceCable = connectorCablePosition(
    source,
    sourceDirection,
    connection.sourceConnector,
  );
  const targetCable = connectorCablePosition(
    target,
    targetDirection,
    connection.targetConnector,
  );
  const distance = sourceCable.distanceTo(targetCable);
  const profile = calculateCurveProfile(distance, Math.abs(source.y - target.y), index);
  const sourceRise = sourceCable.clone().addScaledVector(sourceDirection, 0.34);
  const targetRise = targetCable.clone().addScaledVector(targetDirection, 0.34);
  const midpoint = sourceCable.clone().lerp(targetCable, 0.5);
  midpoint.y = Math.max(sourceCable.y, targetCable.y) + profile.lift;
  const lateral = targetCable.clone().sub(sourceCable).cross(new THREE.Vector3(0, 1, 0));
  if (lateral.lengthSq() > 0.0001) {
    midpoint.addScaledVector(lateral.normalize(), profile.lateralOffset);
  }
  const curve = new THREE.CatmullRomCurve3(
    [sourceCable, sourceRise, midpoint, targetRise, targetCable],
    false,
    "centripetal",
  );
  const color = new THREE.Color(connection.color || "#2563eb");
  const material = new THREE.MeshStandardMaterial({
    color,
    emissive: color.clone(),
    emissiveIntensity: 0,
    roughness: 0.58,
    metalness: 0.05,
  });
  const wire = new THREE.Mesh(
    new THREE.TubeGeometry(
      curve,
      profile.tubularSegments,
      JUMPER_SPEC.wireRadiusSceneUnit,
      8,
      false,
    ),
    material,
  );
  wire.userData.wireId = connection.id;
  wire.castShadow = true;

  const group = new THREE.Group();
  group.name = connection.id;
  group.userData = {
    wireId: connection.id,
    validation: connection.validation,
    curveLength: curve.getLength(),
    curveHeight: profile.lift,
  };
  group.add(wire);
  group.add(makeConnector(
    source,
    sourceDirection,
    color,
    connection.sourceConnector,
    sourceEndpoint,
  ));
  group.add(makeConnector(
    target,
    targetDirection,
    color,
    connection.targetConnector,
    targetEndpoint,
  ));
  return group;
}

function wireTypeLabel(wireType) {
  return wireType
    ?.split("-")
    .map((connector) => (connector === "male" ? "수" : connector === "female" ? "암" : connector))
    .join("-");
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

export default function Circuit3DView({ circuit, interactive = false }) {
  const containerRef = useRef(null);
  const actionsRef = useRef({});
  const gridRef = useRef(null);
  const wireObjectsRef = useRef(new Map());
  const pinTargetsRef = useRef([]);
  const [showGrid, setShowGrid] = useState(true);
  const [showWires, setShowWires] = useState(true);
  const [selectedWireId, setSelectedWireId] = useState(null);
  const [hiddenWireIds, setHiddenWireIds] = useState(() => new Set());
  const [resolvedWires, setResolvedWires] = useState([]);
  const [pinSelection, setPinSelection] = useState(null);
  const [interactiveWireCount, setInteractiveWireCount] = useState(0);
  const [loadState, setLoadState] = useState({ loaded: 0, status: "loading", total: 0 });
  const selectedWire = useMemo(
    () => resolvedWires.find((wire) => wire.id === selectedWireId) ?? null,
    [resolvedWires, selectedWireId],
  );

  useEffect(() => {
    if (gridRef.current) gridRef.current.visible = showGrid;
  }, [showGrid]);

  useEffect(() => {
    wireObjectsRef.current.forEach((group, wireId) => {
      const hidden = !showWires || hiddenWireIds.has(wireId);
      group.visible = !hidden;
      const selected = wireId === selectedWireId;
      group.traverse((object) => {
        if (!object.isMesh || !object.userData.wireId) return;
        object.material.emissiveIntensity = selected ? 0.55 : 0;
        object.scale.setScalar(selected ? 1.35 : 1);
      });
    });
  }, [hiddenWireIds, selectedWireId, showWires]);

  useEffect(() => {
    const container = containerRef.current;
    const parts = circuit?.parts ?? [];
    if (!container || parts.length === 0) return undefined;

    let disposed = false;
    let animationFrame = 0;
    setSelectedWireId(null);
    setPinSelection(null);
    setInteractiveWireCount(0);
    setHiddenWireIds(new Set());
    setResolvedWires([]);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f8fc);
    scene.fog = new THREE.Fog(0xf5f8fc, 23, 48);

    const camera = new THREE.PerspectiveCamera(38, 1, 0.02, 200);
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    container.appendChild(renderer.domElement);
    renderer.domElement.style.cursor = "grab";

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.maxPolarAngle = Math.PI * 0.49;
    controls.minDistance = 3;
    controls.maxDistance = 42;

    scene.add(new THREE.HemisphereLight(0xffffff, 0xa8b5c5, 2.4));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.6);
    keyLight.position.set(-5, 12, 8);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.left = -18;
    keyLight.shadow.camera.right = 18;
    keyLight.shadow.camera.top = 18;
    keyLight.shadow.camera.bottom = -18;
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xc7dcff, 1.4);
    fillLight.position.set(8, 5, -7);
    scene.add(fillLight);

    const assembly = new THREE.Group();
    scene.add(assembly);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 28),
      new THREE.ShadowMaterial({ color: 0x526276, opacity: 0.15 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    scene.add(ground);

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

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const handlePointerDown = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(
        pinTargetsRef.current,
        true,
      ).find((intersection) => intersection.object.userData.pinRef);
      if (hit) {
        actionsRef.current.selectPin?.(hit.object.userData.pinRef);
        return;
      }
      const wireHit = raycaster.intersectObjects(
        [...wireObjectsRef.current.values()],
        true,
      ).find((intersection) => intersection.object.userData.wireId);
      if (wireHit) setSelectedWireId(wireHit.object.userData.wireId);
    };
    renderer.domElement.addEventListener("pointerdown", handlePointerDown);

    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(render);
    };
    render();

    const loader = new GLTFLoader();
    const layoutBounds = getLayoutBounds(parts);
    setLoadState({ loaded: 0, status: "loading", total: parts.length });

    Promise.all(
      parts.map(async (part) => {
        const asset = assetBySlug.get(part.componentKey);
        if (!asset) throw new Error(`Missing GLB: ${part.componentKey}`);
        const gltf = await loader.loadAsync(asset.url);
        if (disposed) {
          disposeObject(gltf.scene);
          return null;
        }
        const record = prepareModel(gltf, part, asset, layoutBounds);
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
        const pinTargetGroup = new THREE.Group();
        pinTargetGroup.name = "pin-snap-targets";
        pinTargetGroup.visible = interactive;
        recordsById.forEach((record) => {
          getSelectablePinKeys(record).forEach((pinKey) => {
            const marker = makePinTarget(record, pinKey);
            pinTargetsRef.current.push(marker);
            pinTargetGroup.add(marker);
          });
        });
        assembly.add(pinTargetGroup);
        const normalizedWires = [];
        let signalIndex = 0;
        const addConnection = (connection, index, isInteractive = false) => {
          const sourceRecord = recordsById.get(connection.source);
          const targetRecord = recordsById.get(connection.target);
          if (!sourceRecord || !targetRecord) return null;
          const sourceEndpoint = createPinEndpoint(sourceRecord, connection.sourcePin);
          const targetEndpoint = createPinEndpoint(targetRecord, connection.targetPin);
          const resolved = resolveJumperWire(
            connection,
            sourceEndpoint,
            targetEndpoint,
            signalIndex,
          );
          if (resolved.colorRole === "signal") signalIndex += 1;
          resolved.interactive = isInteractive;
          const group = makeWire(
            resolved,
            pinWorldPosition(sourceRecord, connection.sourcePin),
            pinWorldPosition(targetRecord, connection.targetPin),
            pinWorldDirection(sourceRecord, sourceEndpoint),
            pinWorldDirection(targetRecord, targetEndpoint),
            sourceEndpoint,
            targetEndpoint,
            index,
          );
          group.userData.interactive = isInteractive;
          wireObjectsRef.current.set(connection.id, group);
          wireGroup.add(group);
          return resolved;
        };
        (circuit.connections ?? []).forEach((connection, index) => {
          const resolved = addConnection(connection, index);
          if (resolved) normalizedWires.push(resolved);
        });
        setResolvedWires(normalizedWires);
        assembly.add(wireGroup);
        frameAssembly(camera, controls, assembly);
        let pendingPin = null;
        let nextWireIndex = 0;
        const resetPinSelection = () => {
          pendingPin = null;
          setPinSelection(null);
          pinTargetsRef.current.forEach((marker) => {
            marker.material.color.set(0x0ea5e9);
            marker.scale.setScalar(1);
          });
        };
        actionsRef.current = {
          isometric: () => frameAssembly(camera, controls, assembly, "isometric"),
          top: () => frameAssembly(camera, controls, assembly, "top"),
          clearPinSelection: resetPinSelection,
          clearInteractiveWires: () => {
            [...wireObjectsRef.current.entries()].forEach(([wireId, group]) => {
              if (!group.userData.interactive) return;
              wireGroup.remove(group);
              disposeObject(group);
              wireObjectsRef.current.delete(wireId);
            });
            setResolvedWires((current) => current.filter((wire) => !wire.interactive));
            setInteractiveWireCount(0);
          },
          selectPin: (pinRef) => {
              if (!interactive) return;
              if (!pendingPin) {
                pendingPin = pinRef;
                setPinSelection({
                  from: `${pinRef.record.part.label} ${pinRef.pinKey}`,
                  to: null,
                });
                pinTargetsRef.current.forEach((marker) => {
                  const candidate = marker.userData.pinRef;
                  const isSelected = candidate === pinRef;
                  marker.material.color.set(isSelected ? 0xf59e0b : 0x22c55e);
                  marker.scale.setScalar(isSelected ? 1.7 : 1.15);
                });
                return;
              }

              if (
                pendingPin.record.part.id === pinRef.record.part.id
                && pendingPin.pinKey === pinRef.pinKey
              ) {
                resetPinSelection();
                return;
              }

              const connection = {
                id: `interactive-wire-${Date.now()}-${nextWireIndex}`,
                source: pendingPin.record.part.id,
                sourcePin: pendingPin.pinKey,
                target: pinRef.record.part.id,
                targetPin: pinRef.pinKey,
                label: `${pendingPin.pinKey} ↔ ${pinRef.pinKey}`,
              };
              const resolved = addConnection(
                connection,
                normalizedWires.length + nextWireIndex,
                true,
              );
              nextWireIndex += 1;
              if (resolved) {
                setResolvedWires((current) => [...current, resolved]);
                setInteractiveWireCount((count) => count + 1);
                setSelectedWireId(resolved.id);
              }
              resetPinSelection();
          },
        };
        setLoadState({ loaded: records.length, status: "ready", total: parts.length });
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
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      controls.dispose();
      wireObjectsRef.current.clear();
      pinTargetsRef.current = [];
      disposeObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [circuit]);

  const toggleWireHidden = (wireId) => {
    setHiddenWireIds((current) => {
      const next = new Set(current);
      if (next.has(wireId)) next.delete(wireId);
      else next.add(wireId);
      return next;
    });
  };

  return (
    <div className="circuit3dWorkspace">
      <div className="circuit3dToolbar">
        <div className="circuit3dTitle">
          <Box size={18} aria-hidden="true" />
          <strong>3D 회로</strong>
          <span>{loadState.loaded}/{loadState.total} 부품</span>
          {interactive && <span>{interactiveWireCount}개 직접 연결</span>}
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
            className={showWires ? "active" : ""}
            title={showWires ? "점퍼선 숨기기" : "점퍼선 표시"}
            aria-label={showWires ? "점퍼선 숨기기" : "점퍼선 표시"}
            onClick={() => setShowWires((visible) => !visible)}
          >
            {showWires ? <Eye size={17} /> : <EyeOff size={17} />}
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
            title="3D 시점 초기화"
            aria-label="3D 시점 초기화"
            onClick={() => actionsRef.current.isometric?.()}
          >
            <RotateCcw size={17} />
          </button>
        </div>
      </div>

      <div className="circuit3dCanvas" ref={containerRef}>
        {loadState.status !== "ready" && (
          <div className={`circuit3dState ${loadState.status}`}>
            <strong>{loadState.status === "error" ? "3D 에셋을 불러오지 못했습니다" : "3D 회로 조립 중"}</strong>
            <span>{loadState.message ?? `${loadState.loaded}/${loadState.total} 부품 불러오는 중`}</span>
          </div>
        )}
      </div>

      <div className="circuit3dLegend" aria-label="3D 점퍼선 연결 목록">
        {resolvedWires.map((connection) => (
          <button
            type="button"
            className={[
              "circuit3dLegendItem",
              selectedWireId === connection.id ? "selected" : "",
              hiddenWireIds.has(connection.id) ? "hidden" : "",
              connection.validation.valid ? "" : "invalid",
            ].filter(Boolean).join(" ")}
            key={connection.id}
            title={
              connection.validation.valid
                ? connection.label
                : connection.validation.issues.map((issue) => issue.message).join(" ")
            }
            onClick={() => setSelectedWireId(connection.id)}
            onDoubleClick={() => toggleWireHidden(connection.id)}
          >
            <span style={{ backgroundColor: connection.color }} />
            <b>{connection.sourcePin} ↔ {connection.targetPin}</b>
            <small>{wireTypeLabel(connection.wireType)}</small>
            <i>{connection.validation.valid ? "정상" : "오류"}</i>
          </button>
        ))}
      </div>

      {interactive && (
        <div className="circuit3dPinGuide">
          <div>
            <strong>{pinSelection ? "두 번째 핀을 선택하세요" : "첫 번째 핀을 선택하세요"}</strong>
            <span>
              {pinSelection
                ? `${pinSelection.from}에서 연결 시작 · 초록색 핀 중 하나를 클릭하세요.`
                : "파란 핀 마커 두 개를 차례로 누르면 점퍼선 종류와 색상이 자동 결정됩니다."}
            </span>
          </div>
          <div>
            {pinSelection && (
              <button type="button" onClick={() => actionsRef.current.clearPinSelection?.()}>
                선택 취소
              </button>
            )}
            {interactiveWireCount > 0 && (
              <button type="button" onClick={() => actionsRef.current.clearInteractiveWires?.()}>
                직접 연결 초기화
              </button>
            )}
          </div>
        </div>
      )}
      {selectedWire && (
        <div className="circuit3dSelection" role="status">
          <div>
            <strong>{selectedWire.sourcePin} ↔ {selectedWire.targetPin}</strong>
            <span>
              {wireTypeLabel(selectedWire.wireType)} · {selectedWire.colorRole}
              {!selectedWire.validation.valid && ` · ${selectedWire.validation.issues[0]?.message}`}
            </span>
          </div>
          <button type="button" onClick={() => toggleWireHidden(selectedWire.id)}>
            {hiddenWireIds.has(selectedWire.id) ? "다시 표시" : "선 숨기기"}
          </button>
        </div>
      )}
    </div>
  );
}
