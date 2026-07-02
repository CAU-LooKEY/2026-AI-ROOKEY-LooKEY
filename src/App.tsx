import { Cable, Cpu, Database, Image as ImageIcon, Layers3, MapPin, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { IsometricCircuit } from "./components/IsometricCircuit";
import { demoCircuits } from "./data/demoCircuits";
import { loadCircuitAssets } from "./lib/assetRepository";
import type { AssetImageKind, CircuitComponentAsset } from "./types/circuit";

const imageKinds: Array<{ value: AssetImageKind; label: string }> = [
  { value: "isometric_2d", label: "2.5D" },
  { value: "preview_3d", label: "3D preview" },
];

export function App() {
  const [assets, setAssets] = useState<CircuitComponentAsset[]>([]);
  const [source, setSource] = useState<"supabase" | "local">("local");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sceneId, setSceneId] = useState(demoCircuits[0].id);
  const [prompt, setPrompt] = useState(demoCircuits[0].prompt);
  const [showPinLabels, setShowPinLabels] = useState(true);
  const [imageKind, setImageKind] = useState<AssetImageKind>("isometric_2d");

  useEffect(() => {
    loadCircuitAssets().then((result) => {
      setAssets(result.assets);
      setSource(result.source);
      setLoadError(result.error ?? null);
    });
  }, []);

  const scene = useMemo(
    () => demoCircuits.find((candidate) => candidate.id === sceneId) ?? demoCircuits[0],
    [sceneId],
  );

  const assetMap = useMemo(() => new Map(assets.map((asset) => [asset.slug, asset])), [assets]);
  const placedAssets = scene.placements
    .map((placement) => assetMap.get(placement.componentSlug))
    .filter((asset): asset is CircuitComponentAsset => Boolean(asset));

  const handleGenerate = () => {
    const normalized = prompt.toLowerCase();
    const nextScene = normalized.includes("raspberry") || normalized.includes("pi")
      ? "pi-led"
      : normalized.includes("nano") || normalized.includes("dht")
        ? "nano-dht11"
        : "uno-led";
    setSceneId(nextScene);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <Cpu aria-hidden="true" size={24} />
          <div>
            <h1>2.5D Circuit Lab</h1>
            <p>{source === "supabase" ? "Supabase assets" : "Local sample assets"}</p>
          </div>
        </div>

        <section className="control-group">
          <label htmlFor="prompt">요청 회로</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={4}
          />
          <button className="primary-button" type="button" onClick={handleGenerate}>
            <Cable aria-hidden="true" size={18} />
            회로 생성
          </button>
        </section>

        <section className="control-group">
          <div className="section-title">
            <Layers3 aria-hidden="true" size={18} />
            프리셋
          </div>
          <div className="preset-list">
            {demoCircuits.map((candidate) => (
              <button
                className={candidate.id === scene.id ? "preset-button active" : "preset-button"}
                key={candidate.id}
                type="button"
                onClick={() => {
                  setSceneId(candidate.id);
                  setPrompt(candidate.prompt);
                }}
              >
                {candidate.title}
              </button>
            ))}
          </div>
        </section>

        <section className="control-group">
          <div className="section-title">
            <ImageIcon aria-hidden="true" size={18} />
            에셋 모드
          </div>
          <div className="segmented-control">
            {imageKinds.map((kind) => (
              <button
                className={imageKind === kind.value ? "active" : ""}
                key={kind.value}
                type="button"
                onClick={() => setImageKind(kind.value)}
              >
                {kind.label}
              </button>
            ))}
          </div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={showPinLabels}
              onChange={(event) => setShowPinLabels(event.target.checked)}
            />
            <span>핀 라벨</span>
          </label>
        </section>

        <section className="control-group compact">
          <div className="section-title">
            <Database aria-hidden="true" size={18} />
            데이터
          </div>
          <p className="status-text">{assets.length} components loaded</p>
          {loadError && <p className="error-text">{loadError}</p>}
          <a className="doc-link" href="/docs/asset-pipeline.md" target="_blank" rel="noreferrer">
            <Upload aria-hidden="true" size={16} />
            asset pipeline
          </a>
        </section>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <h2>{scene.title}</h2>
            <p>{scene.connections.length} wires · {placedAssets.length} components</p>
          </div>
          <div className="source-pill">
            <MapPin aria-hidden="true" size={16} />
            image-space pins
          </div>
        </header>

        <IsometricCircuit
          assets={assets}
          scene={scene}
          imageKind={imageKind}
          showPinLabels={showPinLabels}
        />

        <div className="pin-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Pins</th>
                <th>License</th>
              </tr>
            </thead>
            <tbody>
              {placedAssets.map((asset) => (
                <tr key={asset.slug}>
                  <td>{asset.displayName}</td>
                  <td>{asset.pins.length}</td>
                  <td>{asset.licenseStatus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
