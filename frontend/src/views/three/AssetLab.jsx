import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Box,
  Cable,
  CheckCircle2,
  CircleAlert,
  Crosshair,
  Database,
  FolderOpen,
  Grid3X3,
  MapPin,
  RefreshCw,
  Search,
} from "lucide-react";
import ThreeAssetViewer from "./ThreeAssetViewer.jsx";
import { modelRegistry } from "./modelRegistry.js";
import "./assetLab.css";

const cameraViews = [
  { key: "isometric", label: "Iso" },
  { key: "front", label: "Front" },
  { key: "top", label: "Top" },
  { key: "right", label: "Right" },
];

function formatNumber(value) {
  if (!Number.isFinite(value)) return "-";
  if (value !== 0 && Math.abs(value) < 0.001) return value.toExponential(2);
  return value.toFixed(3);
}

function formatVector(vector) {
  if (!Array.isArray(vector)) return "-";
  return vector.map(formatNumber).join(", ");
}

function formatBytes(value) {
  if (!Number.isFinite(value) || value <= 0) return "-";
  if (value < 1024 * 1024) return (value / 1024).toFixed(1) + " KB";
  return (value / (1024 * 1024)).toFixed(2) + " MB";
}

function MetadataBadge({ status }) {
  const isReady = status === "approved";
  const isMissing = status === "missing";
  const Icon = isReady ? CheckCircle2 : isMissing ? CircleAlert : Database;
  return (
    <span className={"metadataBadge " + status}>
      <Icon size={13} aria-hidden="true" />
      {status}
    </span>
  );
}

function Toggle({ checked, icon: Icon, label, onChange }) {
  return (
    <label className={checked ? "toolToggle active" : "toolToggle"}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
    </label>
  );
}

export default function AssetLab() {
  const initialAssetSlug = new URLSearchParams(window.location.search).get("asset");
  const defaultAsset =
    modelRegistry.find((asset) => asset.slug === initialAssetSlug) ??
    modelRegistry.find((asset) => asset.slug === "arduino-uno-r3") ??
    modelRegistry[0] ??
    null;
  const [selectedKey, setSelectedKey] = useState(defaultAsset?.key ?? "");
  const [localAsset, setLocalAsset] = useState(null);
  const [query, setQuery] = useState("");
  const [cameraView, setCameraView] = useState("isometric");
  const [reloadKey, setReloadKey] = useState(0);
  const [inspection, setInspection] = useState(null);
  const [settings, setSettings] = useState({
    axes: true,
    grid: true,
    jumperFit: true,
    pins: false,
  });
  const fileInputRef = useRef(null);

  useEffect(
    () => () => {
      if (localAsset?.isLocal) URL.revokeObjectURL(localAsset.url);
    },
    [localAsset],
  );

  const assets = useMemo(
    () => (localAsset ? [localAsset, ...modelRegistry] : modelRegistry),
    [localAsset],
  );

  const selectedAsset =
    assets.find((asset) => asset.key === selectedKey) ?? assets[0] ?? null;

  const filteredAssets = assets.filter((asset) => {
    const searchValue = query.trim().toLowerCase();
    if (!searchValue) return true;
    return (
      asset.label.toLowerCase().includes(searchValue) ||
      asset.fileName.toLowerCase().includes(searchValue)
    );
  });

  const updateSetting = (key, checked) => {
    setSettings((current) => ({ ...current, [key]: checked }));
  };

  const handleLocalFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const key = "local-" + file.name + "-" + file.lastModified;
    const asset = {
      fileName: file.name,
      isLocal: true,
      key,
      label: file.name.replace(/\.glb$/i, ""),
      metadata: null,
      metadataSourcePath: null,
      metadataStatus: "missing",
      slug: file.name.replace(/\.glb$/i, ""),
      sourcePath: "Local preview",
      url: URL.createObjectURL(file),
    };
    setLocalAsset(asset);
    setSelectedKey(key);
    setInspection(null);
    event.target.value = "";
  };

  const handleSelectAsset = (asset) => {
    setSelectedKey(asset.key);
    setInspection(null);
    if (!asset.isLocal) {
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("asset", asset.slug);
      window.history.replaceState(null, "", nextUrl);
    }
  };

  const physicalDimensions = selectedAsset?.metadata?.physicalDimensions;
  const runtimeCoordinates =
    selectedAsset?.metadata?.coordinateSystems?.runtime;
  const metadataPins = selectedAsset?.metadata?.pins ?? [];
  const pinNodes = inspection?.pinNodes ?? [];
  const extensionsUsed = inspection?.extensionsUsed ?? [];
  const usesLegacySpecGloss = extensionsUsed.includes(
    "KHR_materials_pbrSpecularGlossiness",
  );

  return (
    <main className="assetLab">
      <header className="assetLabHeader">
        <a className="backLink" href="/" title="Back to Prompt to Circuit">
          <ArrowLeft size={18} aria-hidden="true" />
        </a>
        <Box size={21} aria-hidden="true" />
        <h1>3D Asset Lab</h1>
        <span className="modelCount">{modelRegistry.length} repo models</span>
        <a className="jumperLabLink" href="/assets-3d/jumper-demo">
          <Cable size={15} aria-hidden="true" />
          Jumper Lab
        </a>
      </header>

      <aside className="assetSidebar">
        <div className="assetSidebarTools">
          <label className="assetSearch">
            <Search size={16} aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search models"
              aria-label="Search models"
            />
          </label>
          <button
            className="openLocalButton"
            type="button"
            onClick={() => fileInputRef.current?.click()}
          >
            <FolderOpen size={16} aria-hidden="true" />
            Local GLB
          </button>
          <input
            ref={fileInputRef}
            className="hiddenFileInput"
            type="file"
            accept=".glb,model/gltf-binary"
            onChange={handleLocalFile}
          />
        </div>

        <div className="assetList">
          {filteredAssets.map((asset) => (
            <button
              className={
                asset.key === selectedAsset?.key
                  ? "assetListItem active"
                  : "assetListItem"
              }
              key={asset.key}
              type="button"
              onClick={() => handleSelectAsset(asset)}
            >
              <span className="assetListIcon">
                <Box size={17} aria-hidden="true" />
              </span>
              <span className="assetListText">
                <strong>{asset.label}</strong>
                <small>{asset.fileName}</small>
              </span>
              <MetadataBadge status={asset.metadataStatus} />
            </button>
          ))}
        </div>
      </aside>

      <section className="assetWorkspace">
        <div className="assetToolbar">
          <div className="activeAssetName">
            <strong>{selectedAsset?.label ?? "No GLB models"}</strong>
            {selectedAsset && (
              <MetadataBadge status={selectedAsset.metadataStatus} />
            )}
          </div>

          <div className="cameraTabs" aria-label="Camera view">
            {cameraViews.map((view) => (
              <button
                className={cameraView === view.key ? "active" : ""}
                key={view.key}
                type="button"
                onClick={() => setCameraView(view.key)}
              >
                {view.label}
              </button>
            ))}
          </div>

          <div className="viewerTools">
            <Toggle
              checked={settings.grid}
              icon={Grid3X3}
              label="Grid"
              onChange={(checked) => updateSetting("grid", checked)}
            />
            <Toggle
              checked={settings.axes}
              icon={Crosshair}
              label="Axes"
              onChange={(checked) => updateSetting("axes", checked)}
            />
            <Toggle
              checked={settings.pins}
              icon={MapPin}
              label="Pins"
              onChange={(checked) => updateSetting("pins", checked)}
            />
            <Toggle
              checked={settings.jumperFit}
              icon={Cable}
              label="Jumper"
              onChange={(checked) => updateSetting("jumperFit", checked)}
            />
            <button
              className="iconButton"
              type="button"
              onClick={() => setReloadKey((value) => value + 1)}
              title="Reload model"
              aria-label="Reload model"
            >
              <RefreshCw size={17} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="assetViewport">
          {selectedAsset ? (
            <ThreeAssetViewer
              asset={selectedAsset}
              cameraView={cameraView}
              reloadKey={reloadKey}
              settings={settings}
              onInspection={setInspection}
            />
          ) : (
            <div className="emptyViewer">
              <CircleAlert size={28} aria-hidden="true" />
              <strong>No GLB files found</strong>
            </div>
          )}
          <div className="pinLegend">
            <span><i className="nodePinDot" />GLB pin_* node</span>
            <span><i className="metadataPinDot" />Metadata position</span>
            {inspection?.jumperFit && (
              <span><i className="jumperFitDot" />0.64 mm jumper</span>
            )}
          </div>
        </div>
      </section>

      <aside className="assetInspector">
        <section>
          <h2>Asset</h2>
          <dl>
            <div><dt>File</dt><dd>{selectedAsset?.fileName ?? "-"}</dd></div>
            <div><dt>File size</dt><dd>{formatBytes(inspection?.fileBytes)}</dd></div>
            <div><dt>Metadata</dt><dd>{selectedAsset?.metadataStatus ?? "-"}</dd></div>
            <div><dt>Scale</dt><dd>{selectedAsset?.metadata?.asset?.scaleStatus ?? "unknown"}</dd></div>
            <div><dt>Runtime unit</dt><dd>{runtimeCoordinates?.unit ?? "unknown"}</dd></div>
          </dl>
        </section>

        <section>
          <h2>Compatibility</h2>
          <dl>
            <div><dt>Animations</dt><dd>{inspection?.animationCount ?? "-"}</dd></div>
            <div><dt>Extensions</dt><dd>{extensionsUsed.length || "none"}</dd></div>
          </dl>
          {usesLegacySpecGloss && (
            <div className="compatibilityNotice">
              Legacy spec-gloss material. Re-export with glTF metallic-roughness.
            </div>
          )}
          {extensionsUsed.length > 0 && (
            <ul className="extensionList">
              {extensionsUsed.map((extension) => (
                <li key={extension}>{extension}</li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2>Bounds</h2>
          <dl>
            <div><dt>X</dt><dd>{formatNumber(inspection?.size?.[0])}</dd></div>
            <div><dt>Y</dt><dd>{formatNumber(inspection?.size?.[1])}</dd></div>
            <div><dt>Z</dt><dd>{formatNumber(inspection?.size?.[2])}</dd></div>
            <div><dt>Center</dt><dd>{formatVector(inspection?.center)}</dd></div>
          </dl>
          {physicalDimensions && (
            <div className="physicalSize">
              <span>Physical mm</span>
              <strong>
                {physicalDimensions.width} x {physicalDimensions.depth} x{" "}
                {physicalDimensions.height}
              </strong>
            </div>
          )}
        </section>

        {inspection?.jumperFit && (
          <section>
            <div className="sectionHeading">
              <h2>Jumper fit</h2>
              <span className="fitPass">PASS</span>
            </div>
            <dl>
              <div><dt>Connection</dt><dd>{inspection.jumperFit.connection}</dd></div>
              <div><dt>Male pin</dt><dd>0.640 mm</dd></div>
              <div><dt>Socket</dt><dd>0.724 mm</dd></div>
              <div><dt>Clearance</dt><dd>0.084 mm</dd></div>
              <div><dt>Insert depth</dt><dd>6.000 / 7.096 mm</dd></div>
            </dl>
          </section>
        )}

        <section className="pinInspector">
          <div className="sectionHeading">
            <h2>GLB pin nodes</h2>
            <span>{pinNodes.length}</span>
          </div>
          {pinNodes.length ? (
            <ul>
              {pinNodes.map((pin) => (
                <li key={pin.name}>
                  <strong>{pin.name}</strong>
                  <span>{formatVector(pin.position)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No exported pin_* nodes</p>
          )}
        </section>

        <section className="pinInspector">
          <div className="sectionHeading">
            <h2>Metadata pins</h2>
            <span>{metadataPins.length}</span>
          </div>
          {metadataPins.length ? (
            <ul>
              {metadataPins.map((pin) => (
                <li key={pin.pinKey}>
                  <strong>{pin.pinKey}</strong>
                  <span>{formatVector(pin.position)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No component metadata</p>
          )}
        </section>
      </aside>
    </main>
  );
}
