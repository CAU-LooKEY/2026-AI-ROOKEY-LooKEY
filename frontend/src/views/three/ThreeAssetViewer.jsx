import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const cameraDirections = {
  isometric: new THREE.Vector3(1.4, 1.1, 1.4),
  front: new THREE.Vector3(0, 0, 1),
  top: new THREE.Vector3(0, 1, 0.001),
  right: new THREE.Vector3(1, 0, 0),
};

function disposeObject(root) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.geometry?.dispose();
    const materials = Array.isArray(object.material)
      ? object.material
      : [object.material];
    materials.forEach((material) => {
      if (!material) return;
      Object.values(material).forEach((value) => {
        if (value?.isTexture) value.dispose();
      });
      material.dispose();
    });
  });
}

function makeMarker(position, radius, color, wireframe = false) {
  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 18, 12),
    new THREE.MeshBasicMaterial({
      color,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      opacity: wireframe ? 0.75 : 0.95,
      wireframe,
    }),
  );
  marker.position.copy(position);
  marker.renderOrder = 20;
  return marker;
}

function getPinNodes(root) {
  const pins = [];
  root.updateMatrixWorld(true);
  root.traverse((object) => {
    if (!object.name.toLowerCase().startsWith("pin_")) return;
    const position = new THREE.Vector3();
    object.getWorldPosition(position);
    pins.push({
      name: object.name,
      position: position.toArray(),
      type: object.type,
    });
  });
  return pins;
}

function makeJumperFitPreview(pinNodes) {
  const byName = new Map(pinNodes.map((pin) => [pin.name.toLowerCase(), pin]));
  const source = byName.get("pin_a1");
  const target = byName.get("pin_a5");
  if (!source || !target) return null;

  const group = new THREE.Group();
  group.name = "jumper-fit-preview";
  const seatingOffsetY = -0.001;
  const pinMaterial = new THREE.MeshStandardMaterial({
    color: 0xd9a441,
    metalness: 0.85,
    roughness: 0.25,
  });
  const housingMaterial = new THREE.MeshStandardMaterial({
    color: 0x172033,
    roughness: 0.5,
  });
  const wireMaterial = new THREE.MeshStandardMaterial({
    color: 0xf59e0b,
    roughness: 0.45,
  });

  const points = [source, target].map((pin) =>
    new THREE.Vector3().fromArray(pin.position),
  );
  points.forEach((position) => {
    // 10 mm male pin: 6 mm below the socket plane and 4 mm visible above it.
    const malePin = new THREE.Mesh(
      new THREE.BoxGeometry(0.00064, 0.01, 0.00064),
      pinMaterial,
    );
    malePin.position.copy(position).add(new THREE.Vector3(0, -0.001, 0));
    group.add(malePin);

    const housing = new THREE.Mesh(
      new THREE.BoxGeometry(0.00254, 0.003, 0.00254),
      housingMaterial,
    );
    housing.position
      .copy(position)
      .add(new THREE.Vector3(0, 0.0045 + seatingOffsetY, 0));
    group.add(housing);
  });

  const wireStart = points[0]
    .clone()
    .add(new THREE.Vector3(0, 0.006 + seatingOffsetY, 0));
  const wireEnd = points[1]
    .clone()
    .add(new THREE.Vector3(0, 0.006 + seatingOffsetY, 0));
  const midpoint = wireStart.clone().add(wireEnd).multiplyScalar(0.5);
  midpoint.y += Math.max(points[0].distanceTo(points[1]) * 0.65, 0.008);
  const curve = new THREE.CatmullRomCurve3([
    wireStart,
    wireStart.clone().add(new THREE.Vector3(0, 0.004, 0)),
    midpoint,
    wireEnd.clone().add(new THREE.Vector3(0, 0.004, 0)),
    wireEnd,
  ]);
  group.add(
    new THREE.Mesh(
      new THREE.TubeGeometry(curve, 40, 0.00055, 10, false),
      wireMaterial,
    ),
  );
  return group;
}

export default function ThreeAssetViewer({
  asset,
  cameraView,
  reloadKey,
  settings,
  onInspection,
}) {
  const containerRef = useRef(null);
  const gridRef = useRef(null);
  const axesRef = useRef(null);
  const pinsRef = useRef(null);
  const jumperRef = useRef(null);
  const applyCameraViewRef = useRef(null);
  const cameraViewRef = useRef(cameraView);
  const settingsRef = useRef(settings);
  const [loadState, setLoadState] = useState({
    message: "Loading GLB",
    progress: 0,
    status: "loading",
  });

  cameraViewRef.current = cameraView;
  settingsRef.current = settings;

  useEffect(() => {
    gridRef.current && (gridRef.current.visible = settings.grid);
  }, [settings.grid]);

  useEffect(() => {
    axesRef.current && (axesRef.current.visible = settings.axes);
  }, [settings.axes]);

  useEffect(() => {
    pinsRef.current && (pinsRef.current.visible = settings.pins);
  }, [settings.pins]);

  useEffect(() => {
    jumperRef.current &&
      (jumperRef.current.visible = settings.jumperFit);
  }, [settings.jumperFit]);

  useEffect(() => {
    applyCameraViewRef.current?.(cameraView);
  }, [cameraView]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !asset) return undefined;

    let animationFrame = 0;
    let disposed = false;
    let transferredBytes = 0;
    let loadedRoot = null;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf3f6fa);

    const initialWidth = Math.max(container.clientWidth, 1);
    const initialHeight = Math.max(container.clientHeight, 1);
    const camera = new THREE.PerspectiveCamera(
      38,
      initialWidth / initialHeight,
      0.001,
      10000,
    );
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(initialWidth, initialHeight, false);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x94a3b8, 2.2));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.4);
    keyLight.position.set(3, 5, 4);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xbfd7ff, 1.8);
    fillLight.position.set(-4, 2, -3);
    scene.add(fillLight);

    const helperGroup = new THREE.Group();
    scene.add(helperGroup);

    const resizeObserver = new ResizeObserver(() => {
      const width = Math.max(container.clientWidth, 1);
      const height = Math.max(container.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      applyCameraViewRef.current?.(cameraViewRef.current);
    });
    resizeObserver.observe(container);

    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(render);
    };
    render();

    setLoadState({
      message: "Loading " + asset.fileName,
      progress: 0,
      status: "loading",
    });
    onInspection?.(null);

    const loader = new GLTFLoader();
    loader.load(
      asset.url,
      (gltf) => {
        if (disposed) {
          disposeObject(gltf.scene);
          return;
        }

        loadedRoot = gltf.scene;
        loadedRoot.name = asset.slug;
        scene.add(loadedRoot);
        loadedRoot.updateMatrixWorld(true);

        const bounds = new THREE.Box3().setFromObject(loadedRoot);
        const size = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        const maxSize = Math.max(size.x, size.y, size.z, 0.001);
        const pinNodes = getPinNodes(loadedRoot);

        camera.near = Math.max(maxSize / 10000, 0.00001);
        camera.far = Math.max(maxSize * 1000, 100);
        camera.updateProjectionMatrix();

        const gridSize = maxSize * 2.6;
        const grid = new THREE.GridHelper(gridSize, 24, 0x91a4bd, 0xcbd5e1);
        grid.material.transparent = true;
        grid.material.opacity = 0.55;
        grid.visible = settingsRef.current.grid;
        helperGroup.add(grid);
        gridRef.current = grid;

        const axes = new THREE.AxesHelper(maxSize * 0.34);
        axes.visible = settingsRef.current.axes;
        axes.renderOrder = 10;
        helperGroup.add(axes);
        axesRef.current = axes;

        const pinGroup = new THREE.Group();
        const markerRadius = Math.max(maxSize * 0.012, 0.0004);
        pinNodes.forEach((pin) => {
          pinGroup.add(
            makeMarker(
              new THREE.Vector3().fromArray(pin.position),
              markerRadius,
              0xd11f4b,
            ),
          );
        });
        asset.metadata?.pins?.forEach((pin) => {
          pinGroup.add(
            makeMarker(
              new THREE.Vector3().fromArray(pin.position),
              markerRadius * 1.35,
              0x087f8c,
              true,
            ),
          );
        });
        pinGroup.visible = settingsRef.current.pins;
        helperGroup.add(pinGroup);
        pinsRef.current = pinGroup;

        const jumperFit =
          asset.slug === "breadboard-half"
            ? makeJumperFitPreview(pinNodes)
            : null;
        if (jumperFit) {
          jumperFit.visible = settingsRef.current.jumperFit;
          helperGroup.add(jumperFit);
          jumperRef.current = jumperFit;
        }

        const frameCamera = (viewName) => {
          const direction =
            cameraDirections[viewName] ?? cameraDirections.isometric;
          const verticalFov = THREE.MathUtils.degToRad(camera.fov);
          const horizontalFov = 2 * Math.atan(
            Math.tan(verticalFov / 2) * camera.aspect,
          );
          const limitingFov = Math.min(verticalFov, horizontalFov);
          const distance =
            maxSize / (2 * Math.tan(limitingFov / 2));
          camera.position
            .copy(center)
            .add(direction.clone().normalize().multiplyScalar(distance * 1.65));
          camera.up.set(0, 1, 0);
          if (viewName === "top") camera.up.set(0, 0, -1);
          controls.target.copy(center);
          controls.update();
        };
        applyCameraViewRef.current = frameCamera;
        frameCamera(cameraViewRef.current);

        onInspection?.({
          animationCount: gltf.animations.length,
          bounds: {
            max: bounds.max.toArray(),
            min: bounds.min.toArray(),
          },
          center: center.toArray(),
          extensionsRequired: gltf.parser?.json?.extensionsRequired ?? [],
          extensionsUsed: gltf.parser?.json?.extensionsUsed ?? [],
          fileBytes: transferredBytes,
          jumperFit: jumperFit
            ? {
                connection: "A1 ↔ A5",
              }
            : null,
          pinNodes,
          size: size.toArray(),
        });
        setLoadState({
          message: "Loaded",
          progress: 100,
          status: "ready",
        });
      },
      (event) => {
        if (disposed) return;
        transferredBytes = event.total || event.loaded || transferredBytes;
        const progress = event.total
          ? Math.round((event.loaded / event.total) * 100)
          : 0;
        setLoadState({
          message: "Loading " + asset.fileName,
          progress,
          status: "loading",
        });
      },
      (error) => {
        if (disposed) return;
        console.error("GLB load failed", error);
        setLoadState({
          message: error?.message || "Could not load this GLB.",
          progress: 0,
          status: "error",
        });
      },
    );

    return () => {
      disposed = true;
      applyCameraViewRef.current = null;
      gridRef.current = null;
      axesRef.current = null;
      pinsRef.current = null;
      jumperRef.current = null;
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      controls.dispose();
      if (loadedRoot) disposeObject(loadedRoot);
      helperGroup.traverse((object) => {
        object.geometry?.dispose();
        object.material?.dispose?.();
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [asset, reloadKey]);

  return (
    <div className="threeViewer" ref={containerRef}>
      {loadState.status !== "ready" && (
        <div className={"viewerState " + loadState.status}>
          <strong>{loadState.message}</strong>
          {loadState.status === "loading" && (
            <div className="loadTrack" aria-label="GLB loading progress">
              <span style={{ width: loadState.progress + "%" }} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
