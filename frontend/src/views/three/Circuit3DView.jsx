import { useEffect, useRef, useState } from "react";
import { Box, Grid3X3, RotateCcw } from "lucide-react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import pinCatalog from "../../assets/all_component_pin_coordinates.json";
import { modelRegistry } from "./modelRegistry.js";

const assetBySlug = new Map(modelRegistry.map((asset) => [asset.slug, asset]));
const REAL_WORLD_SCENE_UNITS_PER_METER = 80;

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
    part,
    pinAnchors,
    pinLayout: profile.pinLayout,
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

  const position = pinLocalPosition(record, pinKey);
  record.group.updateMatrixWorld(true);
  return record.group.localToWorld(position);
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
      new THREE.CylinderGeometry(0.025, 0.025, 0.16, 10),
      new THREE.MeshStandardMaterial({ color: 0xc8a951, metalness: 0.8, roughness: 0.25 }),
    );
    pin.position.y = -0.08;
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
  wire.castShadow = true;

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
    if (!container || parts.length === 0) return undefined;

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
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    container.appendChild(renderer.domElement);

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
        (circuit.connections ?? []).forEach((connection, index) => {
          const sourceRecord = recordsById.get(connection.source);
          const targetRecord = recordsById.get(connection.target);
          if (!sourceRecord || !targetRecord) return;
          wireGroup.add(
            makeWire(
              connection,
              pinWorldPosition(sourceRecord, connection.sourcePin),
              pinWorldPosition(targetRecord, connection.targetPin),
              index,
            ),
          );
        });
        assembly.add(wireGroup);
        frameAssembly(camera, controls, assembly);
        actionsRef.current = {
          isometric: () => frameAssembly(camera, controls, assembly, "isometric"),
          top: () => frameAssembly(camera, controls, assembly, "top"),
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
        {(circuit.connections ?? []).map((connection) => (
          <div className="circuit3dLegendItem" key={connection.id} title={connection.label}>
            <span style={{ backgroundColor: connection.color }} />
            <b>{connection.sourcePin} ↔ {connection.targetPin}</b>
            <small>{wireTypeLabel(connection.wireType)}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
