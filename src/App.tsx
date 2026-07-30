import { Cable, Cpu, Database, Image as ImageIcon, Layers3, MapPin, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { IsometricCircuit } from "./components/IsometricCircuit";
import { demoCircuits } from "./data/demoCircuits";
import { loadCircuitAssets } from "./lib/assetRepository";
import { CircuitGenerationError, generateCircuitScene } from "./lib/circuitApi";
import type { CircuitScene } from "./types/circuit";
import type { AssetImageKind, CircuitComponentAsset } from "./types/circuit";

const imageKinds: Array<{ value: AssetImageKind; label: string }> = [
  { value: "isometric_2d", label: "2.5D" },
  { value: "preview_3d", label: "3D preview" },
];

export function App() {
  const [assets, setAssets] = useState<CircuitComponentAsset[]>([]);
  const [source, setSource] = useState<"supabase" | "local">("local");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scene, setScene] = useState<CircuitScene>(demoCircuits[0]);
  const [sceneSource, setSceneSource] = useState<"sample" | "k-exaone">("sample");
  const [prompt, setPrompt] = useState(demoCircuits[0].prompt);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [showPinLabels, setShowPinLabels] = useState(true);
  const [imageKind, setImageKind] = useState<AssetImageKind>("isometric_2d");

  useEffect(() => {
    loadCircuitAssets().then((result) => {
      setAssets(result.assets);
      setSource(result.source);
      setLoadError(result.error ?? null);
    });
  }, []);

  const assetMap = useMemo(() => new Map(assets.map((asset) => [asset.slug, asset])), [assets]);
  const placedAssets = scene.placements
    .map((placement) => assetMap.get(placement.componentSlug))
    .filter((asset): asset is CircuitComponentAsset => Boolean(asset));

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setGenerationError("만들고 싶은 회로를 먼저 입력해주세요.");
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);

    try {
      const generatedScene = await generateCircuitScene(prompt);
      setScene(generatedScene);
      setSceneSource("k-exaone");
    } catch (error) {
      setGenerationError(
        error instanceof CircuitGenerationError || error instanceof Error
          ? error.message
          : "K-EXAONE 검색/조립 중 알 수 없는 오류가 발생했습니다.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const openSample = (sampleScene: CircuitScene) => {
    setScene(sampleScene);
    setSceneSource("sample");
    setPrompt(sampleScene.prompt);
    setGenerationError(null);
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
            {isGenerating ? "K-EXAONE 검색 중" : "K-EXAONE으로 회로 조립"}
          </button>
          {generationError && <p className="error-text">{generationError}</p>}
        </section>

        <section className="control-group">
          <div className="section-title">
            <Layers3 aria-hidden="true" size={18} />
            프리셋
          </div>
          <div className="preset-list">
            {demoCircuits.map((candidate) => (
              <button
                className={sceneSource === "sample" && candidate.id === scene.id ? "preset-button active" : "preset-button"}
                key={candidate.id}
                type="button"
                onClick={() => openSample(candidate)}
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
          <p className="status-text">
            {sceneSource === "sample"
              ? "샘플만 즉시 표시 중입니다."
              : "K-EXAONE 응답으로 조립한 회로입니다."}
          </p>
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
            <p>{scene.connections.length} wires · {placedAssets.length} components · {scene.prompt}</p>
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
