import { Component, useState } from "react";
import { Box, Workflow } from "lucide-react";
import { CircuitGenerationError, generateCircuit } from "./api/circuitApi.js";
import CanvasView from "./views/canvas/CanvasView.jsx";
import Circuit3DView from "./views/three/Circuit3DView.jsx";
import {
  examplePrompts,
  ledBlinkDemoCircuit,
  ledBlinkDemoProject,
  sampleSavedProjects,
} from "./sampleProject.js";
import "./App.css";

const resultSteps = [
  { key: "summary", label: "요약" },
  { key: "wiring", label: "배선 정리" },
  { key: "circuit", label: "회로도" },
  { key: "code", label: "예제 코드" },
  { key: "tutor", label: "AI 튜터" },
  { key: "history", label: "저장/공유" },
];

const componentDisplayNames = {
  "arduino-uno-r3": "Arduino",
  "hc-sr04": "HC-SR04",
  "led-5mm-blue": "LED",
  "pushbutton-6x6": "푸시 버튼",
  "resistor-220-ohm": "220옴 저항",
  "breadboard-half": "브레드보드",
};

export default function App() {
  const [page, setPage] = useState("home");
  const [prompt, setPrompt] = useState(examplePrompts[1].prompt);
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [shareMessage, setShareMessage] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const [project, setProject] = useState(null);
  const [circuit, setCircuit] = useState(null);
  const [apiMessage, setApiMessage] = useState("");
  const [generationError, setGenerationError] = useState(null);

  const isGenerating = page === "loading";
  const hasGeneratedResult = Boolean(project && circuit);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setGenerationError({
        title: "입력 문장이 비어 있습니다.",
        reason: "AI가 회로를 만들려면 만들고 싶은 동작 설명이 필요합니다.",
        suggestions: ["예시 문장을 선택하거나 원하는 회로 동작을 한 문장으로 입력해주세요."],
      });
      setPage("error");
      return;
    }

    setPage("loading");
    setApiMessage("");
    setGenerationError(null);

    try {
      const result = await generateCircuit(prompt);
      setProject(result.project);
      setCircuit(result.circuit);
      setApiMessage("K-EXAONE API에서 새로 생성한 결과입니다.");
      setPage("summary");
    } catch (error) {
      if (error instanceof CircuitGenerationError) {
        setGenerationError({
          title: error.title,
          reason: error.reason,
          suggestions: error.suggestions,
          rawMessage: error.rawMessage,
          code: error.code,
        });
      } else {
        setGenerationError({
          title: "K-EXAONE 회로 생성에 실패했습니다.",
          reason: error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다.",
          suggestions: [
            "문장을 더 짧고 구체적으로 입력해보세요.",
            "지원 부품만 사용해보세요: LED, 버튼, 초음파 센서, 저항.",
            "잠시 후 다시 시도해보세요.",
          ],
        });
      }
      setPage("error");
    }
  };

  const openLocalDemo = () => {
    const demoPrompt = "LED가 1초마다 깜빡이는 회로를 만들어줘 버튼 누르면 on/off 되고";
    setPrompt(demoPrompt);
    setProject(ledBlinkDemoProject);
    setCircuit(ledBlinkDemoCircuit);
    setApiMessage("API 없이 확인하는 로컬 3D 검증용 샘플입니다.");
    setGenerationError(null);
    setPage("summary");
  };

  const savePrompt = () => {
    setSavedPrompts((items) => {
      if (items.includes(prompt)) return items;
      return [prompt, ...items];
    });
  };

  const sharePrompt = () => {
    savePrompt();
    setShareMessage(project.shareMessage);
  };

  return (
    <div className="app">
      <header className="nav">
        <button className="logoButton" disabled={isGenerating} onClick={() => setPage("home")}>
          ⚙️ Prompt to Circuit
        </button>
        <div className="menu">
          <button disabled={isGenerating} onClick={() => setPage("home")}>홈</button>
          <button disabled={isGenerating || !hasGeneratedResult} onClick={() => setPage("summary")}>내 프로젝트</button>
          <button disabled={isGenerating || !hasGeneratedResult} onClick={() => setPage("tutor")}>AI 튜터</button>
          <button disabled={isGenerating || !hasGeneratedResult} onClick={() => setPage("history")}>저장</button>
          <a className="navLink" href="/assets-3d">3D 에셋</a>
        </div>
      </header>

      {page === "home" && (
        <HomePage
          prompt={prompt}
          onPromptChange={setPrompt}
          onExampleSelect={setPrompt}
          onNext={handleGenerate}
          onLocalDemo={openLocalDemo}
        />
      )}
      {page === "loading" && <LoadingPage prompt={prompt} />}
      {page === "error" && (
        <GenerationErrorPage
          prompt={prompt}
          message={generationError}
          onBack={() => setPage("home")}
          onRetry={handleGenerate}
          onLocalDemo={openLocalDemo}
        />
      )}
      {page === "summary" && (
        <SummaryPage
          prompt={prompt}
          project={project}
          circuit={circuit}
          apiMessage={apiMessage}
          onStepSelect={setPage}
          onBack={() => setPage("home")}
          onNext={() => setPage("wiring")}
        />
      )}
      {page === "wiring" && (
        <WiringPage
          circuit={circuit}
          onStepSelect={setPage}
          onBack={() => setPage("summary")}
          onNext={() => setPage("circuit")}
        />
      )}
      {page === "circuit" && (
        <CircuitPage
          circuit={circuit}
          project={project}
          onStepSelect={setPage}
          onBack={() => setPage("wiring")}
          onNext={() => setPage("code")}
        />
      )}
      {page === "code" && (
        <CodePage
          project={project}
          copyMessage={copyMessage}
          onCopyMessage={setCopyMessage}
          onStepSelect={setPage}
          onBack={() => setPage("circuit")}
          onNext={() => setPage("tutor")}
        />
      )}
      {page === "tutor" && (
        <TutorPage project={project} onStepSelect={setPage} onBack={() => setPage("code")} onNext={() => setPage("history")} />
      )}
      {page === "history" && (
        <HistoryPage
          prompt={prompt}
          project={project}
          savedPrompts={savedPrompts}
          shareMessage={shareMessage}
          onSave={savePrompt}
          onShare={sharePrompt}
          onStepSelect={setPage}
          onBack={() => setPage("tutor")}
          onHome={() => setPage("home")}
        />
      )}
    </div>
  );
}

function HomePage({ prompt, onPromptChange, onExampleSelect, onNext, onLocalDemo }) {
  return (
    <main className="hero">
      <section className="card">
        <h1>무엇을 만들고 싶나요?</h1>
        <p>원하는 동작을 문장으로 입력하면 AI가 회로와 코드를 만들어드려요.</p>

        <div className="inputBox">
          <input value={prompt} onChange={(event) => onPromptChange(event.target.value)} />
          <button onClick={onNext}>→</button>
        </div>

        <h3>예시 프로젝트</h3>
        <div className="chips">
          {examplePrompts.map((example) => (
            <button key={example.label} onClick={() => onExampleSelect(example.prompt)}>
              {example.label}
            </button>
          ))}
        </div>

        <div className="homeActions">
          <button className="secondaryBtn" onClick={onLocalDemo}>
            샘플 3D 보기
          </button>
          <button className="mainBtn" onClick={onNext}>
            AI로 회로 만들기
          </button>
        </div>
      </section>
    </main>
  );
}

function LoadingPage({ prompt }) {
  return (
    <main className="hero">
      <section className="card loading">
        <div className="loadingIntro">
          <div className="robotFace">
            <span></span>
            <span></span>
          </div>
          <h1>AI가 회로를 만들고 있어요!</h1>
          <p>입력한 문장을 분석해서 부품, 회로, 코드, 설명 자료를 구성합니다.</p>
        </div>

        <div className="steps loadingSteps">
          <div className="done">
            <b>K-EXAONE 요청 전송 완료</b>
            <span>입력 문장과 회로 생성 규칙을 모델에 전달했습니다.</span>
          </div>
          <div className="active">
            <b>회로와 코드 생성 중</b>
            <span>요청에 맞는 부품, 핀 연결, Arduino 코드를 만들고 있어요.</span>
          </div>
          <div>
            <b>응답 검증 대기</b>
            <span>JSON 형식과 지원 부품, 핀 연결을 확인합니다.</span>
          </div>
        </div>

        <div className="loadingRequest">
          <b>입력 문장</b>
          <span>{prompt}</span>
          <p>생성이 완료되면 결과 화면으로 자동 이동합니다. 보통 15~60초 정도 걸립니다.</p>
        </div>
      </section>
    </main>
  );
}

function GenerationErrorPage({ prompt, message, onBack, onRetry, onLocalDemo }) {
  const errorInfo = normalizeGenerationError(message);

  return (
    <main className="hero">
      <section className="card errorPanel">
        <div className="errorMark">!</div>
        <h1>{errorInfo.title}</h1>
        <p>샘플 회로로 대체하지 않았습니다. 오류를 확인한 뒤 다시 시도해주세요.</p>
        <div className="errorPrompt">
          <b>입력 문장</b>
          <span>{prompt}</span>
        </div>
        <div className="errorGuide">
          <div>
            <b>원인</b>
            <p>{errorInfo.reason}</p>
          </div>
          <div>
            <b>가능한 해결</b>
            <ul>
              {errorInfo.suggestions.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          </div>
          {errorInfo.rawMessage && <small>상세 오류: {errorInfo.rawMessage}</small>}
        </div>
        <div className="pageActions errorActions">
          <button className="secondaryBtn" onClick={onBack}>입력 수정</button>
          <button className="secondaryBtn" onClick={onLocalDemo}>샘플 3D 보기</button>
          <button className="mainBtn" onClick={onRetry}>다시 생성</button>
        </div>
      </section>
    </main>
  );
}

function normalizeGenerationError(message) {
  if (message && typeof message === "object") {
    return {
      title: message.title ?? "K-EXAONE 응답을 받지 못했습니다.",
      reason: message.reason ?? "알 수 없는 오류가 발생했습니다.",
      suggestions: Array.isArray(message.suggestions) ? message.suggestions : defaultErrorSuggestions,
      rawMessage: message.rawMessage ?? "",
    };
  }

  return {
    title: "K-EXAONE 응답을 받지 못했습니다.",
    reason: message || "알 수 없는 오류가 발생했습니다.",
    suggestions: defaultErrorSuggestions,
    rawMessage: "",
  };
}

const defaultErrorSuggestions = [
  "문장을 더 짧고 구체적으로 입력해보세요.",
  "지원 부품만 사용해보세요: LED, 버튼, 초음파 센서, 저항.",
  "잠시 후 다시 시도해보세요.",
];

function ResultShell({ activeStep, title, desc, children, onBack, onNext, onStepSelect, nextLabel = "다음" }) {
  return (
    <main className="hero">
      <section className="result">
        <StepNav activeStep={activeStep} onStepSelect={onStepSelect} />
        <h2>{title}</h2>
        <p className="centerText">{desc}</p>
        {children}
        <div className="pageActions">
          {onBack && (
            <button className="secondaryBtn" onClick={onBack}>
              이전
            </button>
          )}
          {onNext && (
            <button className="mainBtn" onClick={onNext}>
              {nextLabel}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}

function StepNav({ activeStep, onStepSelect }) {
  const activeIndex = resultSteps.findIndex((step) => step.key === activeStep);

  return (
    <div className="stepNav">
      {resultSteps.map((step, index) => (
        <button
          key={step.key}
          className={index <= activeIndex ? "stepPill active" : "stepPill"}
          onClick={() => onStepSelect?.(step.key)}
        >
          {index + 1}. {step.label}
        </button>
      ))}
    </div>
  );
}

function SummaryPage({ prompt, project, circuit, apiMessage, onStepSelect, onBack, onNext }) {
  return (
    <ResultShell
      activeStep="summary"
      title="프로젝트 요약"
      desc="먼저 만들 회로의 난이도, 예상 시간, 필요한 부품을 확인합니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="배선 정리 보기"
    >
      {apiMessage && <div className="notice compactNotice">{apiMessage}</div>}
      <div className="generatedSummary">
        <span>K-EXAONE 생성 제목</span>
        <h3>{project.title}</h3>
        <p>{prompt}</p>
      </div>

      <div className="stats">
        <div>
          <b>필요 부품</b>
          <strong>{circuit.parts.length}개</strong>
        </div>
        <div>
          <b>난이도</b>
          <strong>{project.difficulty}</strong>
        </div>
        <div>
          <b>예상 시간</b>
          <strong>{project.estimatedTime}</strong>
        </div>
      </div>

      <div className="parts">
        {project.parts.map((part) => (
          <PartCard key={part.title} title={part.title} desc={part.desc} />
        ))}
      </div>
    </ResultShell>
  );
}

function CircuitPage({ circuit, project, onStepSelect, onBack, onNext }) {
  const [viewMode, setViewMode] = useState("3d");

  return (
    <ResultShell
      activeStep="circuit"
      title="3D 회로 조립도"
      desc="실제 부품의 방향과 점퍼선 연결을 돌려보며 확인합니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="예제 코드 보기"
    >
      <div className="circuitStage">
        <div className="circuitChecklist">
          <div className="done">① 보드 배치 ✓</div>
          <div className="done">② 핀 연결 구성 ✓</div>
          <div className="done">③ 응답 형식 검증 ✓</div>
          <div className="active">④ 3D 전체 회로 확인 ●</div>
        </div>
        <div className="circuitCanvasPanel">
          <div className="circuitViewHeader">
            <div>
              <strong>{viewMode === "3d" ? "3D 조립 배치" : "2D 배선도"}</strong>
              <span>{viewMode === "3d" ? "드래그해서 회전하고 휠로 확대하세요." : "핀 이름과 배선 경로를 확인하세요."}</span>
            </div>
            <div className="circuitViewSwitch" role="tablist" aria-label="회로 보기 방식">
              <button
                type="button"
                role="tab"
                aria-selected={viewMode === "3d"}
                className={viewMode === "3d" ? "active" : ""}
                onClick={() => setViewMode("3d")}
              >
                <Box size={16} />
                3D
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={viewMode === "2d"}
                className={viewMode === "2d" ? "active" : ""}
                onClick={() => setViewMode("2d")}
              >
                <Workflow size={16} />
                2D
              </button>
            </div>
          </div>
          <CircuitRenderBoundary key={viewMode}>
            {viewMode === "3d" ? <Circuit3DView circuit={circuit} /> : <CanvasView circuit={circuit} />}
          </CircuitRenderBoundary>
        </div>
      </div>
      {project.validationResults?.length > 0 && (
        <div className="explainBox">
          <b>검증 결과.</b> {project.validationResults.map((item) => item.message).join(" ")}
        </div>
      )}
      {project.tutorSteps?.[0] && (
        <div className="explainBox">
          <b>{project.tutorSteps[0].title}</b> {project.tutorSteps[0].desc}
        </div>
      )}
    </ResultShell>
  );
}

class CircuitRenderBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    console.error("Circuit rendering failed", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="circuitRenderError">
          <strong>회로도를 그리지 못했습니다.</strong>
          <span>배선 정리와 예제 코드는 생성된 K-EXAONE 정보를 기준으로 계속 확인할 수 있습니다.</span>
        </div>
      );
    }

    return this.props.children;
  }
}

function WiringPage({ circuit, onStepSelect, onBack, onNext }) {
  const wiringRows = buildWiringRows(circuit);

  return (
    <ResultShell
      activeStep="wiring"
      title="K-EXAONE 배선 정리"
      desc="AI가 생성한 핀 연결을 실제로 꽂는 순서처럼 다시 정리합니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="회로도 보기"
    >
      <div className="wiringLayout">
        <div className="wiringList">
          {wiringRows.map((row, index) => (
            <div className="wiringItem" key={row.id}>
              <span className="wiringIndex">{index + 1}</span>
              <div>
                <b>{row.summary}</b>
                <p>{row.detail}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="wiringSide">
          <h3>사용 부품</h3>
          {circuit.parts.map((part) => (
            <div className="wiringPart" key={part.id}>
              <b>{getPartName(part)}</b>
              <span>{part.id}</span>
            </div>
          ))}
        </div>
      </div>
    </ResultShell>
  );
}

function buildWiringRows(circuit) {
  const partsById = new Map(circuit.parts.map((part) => [part.id, part]));
  const assemblyConnections = new Map(
    (circuit.assemblyPlan?.connections ?? []).map((connection) => [connection.id, connection]),
  );

  return circuit.connections.map((connection) => {
    const source = partsById.get(connection.source);
    const target = partsById.get(connection.target);
    const sourceName = getPartName(source);
    const targetName = getPartName(target);
    const assembly = assemblyConnections.get(connection.id);
    const sourceAddress = assembly?.source?.address;
    const targetAddress = assembly?.target?.address;
    const hasBreadboardAddress = sourceAddress || targetAddress;

    return {
      id: connection.id,
      summary: `${sourceName} ${formatPin(connection.sourcePin)} -> ${targetName} ${formatPin(connection.targetPin)}`,
      detail: hasBreadboardAddress
        ? `${formatEndpoint(sourceName, connection.sourcePin, sourceAddress)}에서 ${formatEndpoint(targetName, connection.targetPin, targetAddress)}로 점퍼선을 연결합니다.`
        : `${sourceName}의 ${formatPin(connection.sourcePin)} 핀을 ${targetName}의 ${formatPin(connection.targetPin)} 핀과 연결합니다.`,
    };
  });
}

function getPartName(part) {
  if (!part) return "부품";
  return componentDisplayNames[part.componentKey] ?? part.label ?? part.id;
}

function formatPin(pin) {
  if (pin === "ANODE") return "LED(+)";
  if (pin === "CATHODE") return "LED(-)";
  if (pin === "LEAD_A") return "저항 한쪽";
  if (pin === "LEAD_B") return "저항 반대쪽";
  if (pin?.startsWith("GND")) return "GND";
  return pin;
}

function formatEndpoint(name, pin, address) {
  const label = `${name} ${formatPin(pin)}`;
  return address ? `${label}, 브레드보드 ${address}` : label;
}

function CodePage({ project, copyMessage, onCopyMessage, onStepSelect, onBack, onNext }) {
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(project.code);
      onCopyMessage("코드를 클립보드에 복사했습니다.");
    } catch {
      onCopyMessage("복사에 실패했습니다. 코드를 직접 선택해서 복사해주세요.");
    }
  };

  return (
    <ResultShell
      activeStep="code"
      title="Arduino 예제 코드"
      desc="회로를 연결한 뒤 Arduino IDE에 붙여 넣어 동작을 테스트할 수 있습니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="동작 원리 보기"
    >
      <div className="codeToolbar">
        <span>Arduino IDE에 붙여 넣어 테스트하세요.</span>
        <button className="mainBtn compact" onClick={copyCode}>
          코드 복사
        </button>
      </div>
      {copyMessage && <div className="notice compactNotice">{copyMessage}</div>}
      <pre className="codeBlock">
        <code>{project.code}</code>
      </pre>
      <div className="explainBox">
        이 코드는 생성된 회로의 핀 연결을 기준으로 작성되었습니다. 업로드 전 회로도와 사용 핀을 다시 확인해주세요.
      </div>
    </ResultShell>
  );
}

function TutorPage({ project, onStepSelect, onBack, onNext }) {
  return (
    <ResultShell
      activeStep="tutor"
      title="AI 튜터 설명"
      desc="초보자가 회로의 동작 흐름을 이해할 수 있도록 단계별로 설명합니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="저장/공유하기"
    >
      <div className="tutorLayout">
        <div className="tutorGrid">
          {project.tutorSteps.map((step) => (
            <InfoPanel key={step.title} title={step.title}>
              {step.desc}
            </InfoPanel>
          ))}
        </div>
        <div className="changePanel">
          <button className="mainBtn compact">LED 대신 부저로 바꿔줘</button>
          <InfoPanel title="AI 튜터">
            좋아요! LED를 부저로 변경하면 출력 부품이 바뀌기 때문에 연결 핀과 코드가 함께 수정되어야 해요.
          </InfoPanel>
          <div className="changeList">
            <div><b>제거</b><span>LED, 220Ω 저항</span></div>
            <div><b>추가</b><span>부저</span></div>
            <div><b>수정된 핀</b><span>D3 → D6</span></div>
          </div>
        </div>
      </div>
    </ResultShell>
  );
}

function HistoryPage({ prompt, project, savedPrompts, shareMessage, onSave, onShare, onStepSelect, onBack, onHome }) {
  const projects =
    savedPrompts.length > 0
      ? [
          {
            ...sampleSavedProjects[0],
            title: project.title,
            prompt: savedPrompts[0],
          },
          ...sampleSavedProjects.slice(1),
        ]
      : sampleSavedProjects;

  return (
    <ResultShell
      activeStep="history"
      title="프로젝트 저장/공유"
      desc="완성한 회로와 코드를 저장하거나 팀원, 선생님에게 공유할 수 있습니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onHome}
      nextLabel="처음으로"
    >
      <div className="projectGrid">
        {projects.map((project) => (
          <ProjectCard key={project.title} project={project} />
        ))}
      </div>

      {shareMessage && <div className="notice">{shareMessage}</div>}

      <div className="projectActions">
        <button className="secondaryBtn" onClick={onShare}>
          공유 링크 만들기
        </button>
        <button className="secondaryBtn">PDF 내보내기</button>
        <button className="secondaryBtn">코드 내보내기</button>
        <button className="mainBtn" onClick={onHome}>
          새 프로젝트 만들기
        </button>
      </div>
    </ResultShell>
  );
}

function ProjectCard({ project }) {
  return (
    <div className="projectCard">
      <div className="projectPreview">
        <div className="previewBoard"></div>
        <div className="previewLed"></div>
      </div>
      <h3>{project.title}</h3>
      <div className="tagRow">
        {project.tags.map((tag) => (
          <span key={tag} className={tag === "완료" ? "tag doneTag" : "tag"}>
            {tag}
          </span>
        ))}
      </div>
      <p>수정일: {project.updatedAt}</p>
    </div>
  );
}

function InfoPanel({ title, children }) {
  return (
    <div className="infoPanel">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

function PartCard({ title, desc }) {
  return (
    <div className="partCard">
      <div className="partImg">
        <div className="mcu"></div>
        <div className="led"></div>
      </div>
      <h3>{title}</h3>
      <p>{desc}</p>
    </div>
  );
}
