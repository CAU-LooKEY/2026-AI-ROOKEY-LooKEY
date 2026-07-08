import { FormEvent, useMemo, useState } from "react";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  ChevronRight,
  Code2,
  Cpu,
  Layers3,
  Play,
  RefreshCcw,
  Route,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MiniMap,
  Node,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";

import { CircuitEdge, CircuitNode, useCircuitDemo } from "../../hooks/useCircuitDemo";

type StageKey = "prompt" | "components" | "diagram" | "code";

const stages: Array<{
  key: StageKey;
  label: string;
  caption: string;
}> = [
  { key: "prompt", label: "1. 요청 입력", caption: "자연어로 만들고 싶은 장치를 설명" },
  { key: "components", label: "2. 부품 분석", caption: "필요한 보드, 입력, 출력, 저항 확인" },
  { key: "diagram", label: "3. 회로 배치", caption: "React Flow 캔버스에서 연결 구조 확인" },
  { key: "code", label: "4. 코드/검증", caption: "Arduino 코드와 안전 경고 검토" },
];

const nodeColors: Record<CircuitNode["type"], string> = {
  board: "#0f766e",
  input: "#2563eb",
  output: "#dc2626",
  passive: "#9333ea",
  power: "#ea580c",
};

function toFlowNodes(nodes: CircuitNode[]): Node[] {
  return nodes.map((node) => ({
    id: node.id,
    position: node.position,
    data: {
      label: node.label,
      componentKey: node.componentKey,
    },
    style: {
      width: 210,
      border: `2px solid ${nodeColors[node.type]}`,
      borderRadius: 8,
      color: "#111827",
      fontSize: 13,
      fontWeight: 700,
      padding: 12,
      background: "#ffffff",
      boxShadow: "0 8px 22px rgba(15, 23, 42, 0.12)",
    },
  }));
}

function toFlowEdges(edges: CircuitEdge[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label ?? undefined,
    type: "smoothstep",
    animated: true,
    style: {
      stroke: String(edge.data.wireColor ?? "#475569"),
      strokeWidth: 2,
    },
    labelStyle: {
      fill: "#334155",
      fontSize: 11,
      fontWeight: 700,
    },
    labelBgStyle: {
      fill: "#ffffff",
      fillOpacity: 0.92,
    },
  }));
}

function CircuitCanvasContent() {
  const { circuit, error, generateCircuit, isLoading, loadDemo } = useCircuitDemo();
  const [activeStage, setActiveStage] = useState<StageKey>("prompt");
  const [prompt, setPrompt] = useState("버튼을 누르면 LED가 켜지는 회로를 만들고 싶어");

  const flowNodes = useMemo(() => (circuit ? toFlowNodes(circuit.nodes) : []), [circuit]);
  const flowEdges = useMemo(() => (circuit ? toFlowEdges(circuit.edges) : []), [circuit]);
  const componentCount = circuit?.nodes.length ?? 0;
  const wireCount = circuit?.edges.length ?? 0;
  const warningCount = circuit?.warnings.length ?? 0;

  const submitPrompt = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await generateCircuit(prompt);
    setActiveStage("components");
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Sparkles size={19} />
          </div>
          <div>
            <span className="eyebrow">LooKEY</span>
            <h1>Prompt-to-Circuit Studio</h1>
          </div>
        </div>
        <button className="icon-button" onClick={loadDemo} disabled={isLoading} title="데모 회로 새로고침">
          <RefreshCcw size={18} />
          <span>{isLoading ? "Loading" : "Reload"}</span>
        </button>
      </header>

      <section className="project-strip">
        <div className="project-copy">
          <span className="section-kicker">AI circuit workflow</span>
          <h2>{circuit?.title ?? "회로 생성 과정을 시작하세요"}</h2>
          <p>{circuit?.summary ?? "원하는 동작을 자연어로 입력하면 부품, 회로, 코드, 안전 경고를 단계별로 확인합니다."}</p>
        </div>
        <div className="metric-grid">
          <article className="metric-card">
            <Boxes size={18} />
            <div>
              <strong>{componentCount}</strong>
              <span>Components</span>
            </div>
          </article>
          <article className="metric-card">
            <Route size={18} />
            <div>
              <strong>{wireCount}</strong>
              <span>Wires</span>
            </div>
          </article>
          <article className="metric-card">
            <ShieldCheck size={18} />
            <div>
              <strong>{warningCount}</strong>
              <span>Safety checks</span>
            </div>
          </article>
        </div>
      </section>

      <nav className="stage-nav" aria-label="회로 생성 단계">
        {stages.map((stage, index) => (
          <button
            className={stage.key === activeStage ? "stage-button active" : "stage-button"}
            key={stage.key}
            onClick={() => setActiveStage(stage.key)}
            type="button"
          >
            <span className="stage-index">{index + 1}</span>
            <span>
              <strong>{stage.label}</strong>
              <small>{stage.caption}</small>
            </span>
          </button>
        ))}
      </nav>

      {activeStage === "prompt" && (
        <section className="stage-workbench prompt-stage">
          <div className="prompt-panel">
            <span className="section-kicker">Step 1</span>
            <h2>무엇을 만들고 싶나요?</h2>
            <p>초보자는 부품명을 몰라도 괜찮습니다. 원하는 동작을 말하면 다음 단계에서 필요한 부품과 연결 구조를 확인합니다.</p>
            <form onSubmit={submitPrompt}>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="예: 손을 가까이 대면 LED가 켜지는 장치를 만들고 싶어"
              />
              <button className="primary-action" disabled={isLoading || prompt.trim().length === 0} type="submit">
                <Play size={17} />
                <span>{isLoading ? "분석 중" : "회로 생성 시작"}</span>
              </button>
            </form>
          </div>
          <div className="preview-panel">
            <h3>진행 흐름</h3>
            <ol className="flow-steps">
              <li>자연어 요청을 구조화합니다.</li>
              <li>필요한 부품과 연결선을 정리합니다.</li>
              <li>회로 다이어그램과 Arduino 코드를 생성합니다.</li>
              <li>안전 경고와 학습 설명을 제공합니다.</li>
            </ol>
          </div>
        </section>
      )}

      {activeStage === "components" && (
        <section className="stage-workbench split-stage">
          <div className="wide-panel">
            <div className="section-title">
              <Layers3 size={17} />
              <h3>추천 부품</h3>
            </div>
            <div className="component-grid">
              {(circuit?.nodes ?? []).map((node) => (
                <article className="component-card" key={node.id}>
                  <span className="component-dot" style={{ backgroundColor: nodeColors[node.type] }} />
                  <div>
                    <strong>{node.label}</strong>
                    <span>{node.componentKey}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>
          <div className="narrow-panel">
            <h3>다음 단계</h3>
            <p>부품 구성이 맞다면 회로 배치 단계로 넘어가 연결 구조를 확인하세요.</p>
            <button className="secondary-action" onClick={() => setActiveStage("diagram")} type="button">
              <span>회로 배치 보기</span>
              <ChevronRight size={17} />
            </button>
          </div>
        </section>
      )}

      {activeStage === "diagram" && (
        <section className="workspace diagram-workspace">
          <aside className="left-panel">
            <section className="panel-section">
              <div className="section-title">
                <CheckCircle2 size={17} />
                <h3>제작 단계</h3>
              </div>
              <ol className="steps-list">
                {(circuit?.explanation ?? ["API 응답을 기다리는 중입니다."]).map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </section>
          </aside>

          <div className="canvas-panel">
            <div className="canvas-toolbar">
              <div className="toolbar-title">
                <Cpu size={18} />
                <span>회로 다이어그램</span>
              </div>
              <span className={error ? "status-badge error" : "status-badge"}>
                {error ? "API offline" : "API ready"}
              </span>
            </div>

            <div className="flow-wrap">
              <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
                <MiniMap pannable zoomable />
                <Controls />
                <Background gap={24} size={1.2} color="#cbd5e1" />
              </ReactFlow>
            </div>
          </div>
        </section>
      )}

      {activeStage === "code" && (
        <section className="stage-workbench split-stage">
          <div className="wide-panel">
            <div className="section-title">
              <Code2 size={17} />
              <h3>Arduino 코드</h3>
            </div>
            <pre className="code-block">{circuit?.code ?? "// API 응답 후 코드가 표시됩니다."}</pre>
          </div>
          <div className="narrow-panel">
            <div className="section-title">
              <AlertTriangle size={17} />
              <h3>안전 경고</h3>
            </div>
            <ul>
              {(circuit?.warnings ?? ["백엔드 서버가 켜져 있는지 확인하세요."]).map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </main>
  );
}

export function CircuitCanvas() {
  return (
    <ReactFlowProvider>
      <CircuitCanvasContent />
    </ReactFlowProvider>
  );
}
