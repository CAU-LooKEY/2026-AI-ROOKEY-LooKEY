import { useState } from "react";
import { Box, Workflow } from "lucide-react";
import { generateCircuit } from "./api/circuitApi.js";
import CanvasView from "./views/canvas/CanvasView.jsx";
import Circuit3DView from "./views/three/Circuit3DView.jsx";
import { examplePrompts, sampleSavedProjects } from "./sampleProject.js";
import "./App.css";

const resultSteps = [
  { key: "summary", label: "요약" },
  { key: "circuit", label: "회로도" },
  { key: "code", label: "예제 코드" },
  { key: "tutor", label: "AI 튜터" },
  { key: "history", label: "저장/공유" },
];

export default function App() {
  const [page, setPage] = useState("home");
  const [prompt, setPrompt] = useState("");
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [shareMessage, setShareMessage] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const [project, setProject] = useState(null);
  const [circuit, setCircuit] = useState(null);
  const [apiMessage, setApiMessage] = useState("");
  const [generationError, setGenerationError] = useState("");

  const isGenerating = page === "loading";
  const hasGeneratedResult = Boolean(project && circuit);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setGenerationError("만들고 싶은 회로를 문장으로 입력해주세요.");
      setPage("error");
      return;
    }

    setPage("loading");
    setApiMessage("");
    setGenerationError("");

    try {
      const result = await generateCircuit(prompt);
      setProject(result.project);
      setCircuit(result.circuit);
      setApiMessage("입력 문장을 바탕으로 K-EXAONE API에서 새로 생성한 결과입니다.");
      setPage("summary");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "K-EXAONE 회로 생성에 실패했습니다.");
      setPage("error");
    }
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
        </div>
      </header>

      {page === "home" && (
        <HomePage
          prompt={prompt}
          onPromptChange={setPrompt}
          onExampleSelect={setPrompt}
          onNext={handleGenerate}
        />
      )}
      {page === "loading" && <LoadingPage prompt={prompt} />}
      {page === "error" && (
        <GenerationErrorPage
          prompt={prompt}
          message={generationError}
          onBack={() => setPage("home")}
          onRetry={handleGenerate}
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
          onNext={() => setPage("circuit")}
        />
      )}
      {page === "circuit" && (
        <CircuitPage
          circuit={circuit}
          project={project}
          onStepSelect={setPage}
          onBack={() => setPage("summary")}
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

function HomePage({ prompt, onPromptChange, onExampleSelect, onNext }) {
  return (
    <main className="hero">
      <section className="card">
        <h1>무엇을 만들고 싶나요?</h1>
        <p>원하는 동작을 문장으로 입력하면 AI가 회로와 코드를 만들어드려요.</p>

        <div className="inputBox">
          <input
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            placeholder="예: 버튼을 누르면 LED가 켜지는 회로를 만들어줘"
          />
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

        <button className="mainBtn" onClick={onNext}>
          AI로 회로 만들기
        </button>
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
          <p>생성이 완료되면 결과 화면으로 자동 이동합니다. 보통 30~120초 정도 걸립니다.</p>
        </div>
      </section>
    </main>
  );
}

function GenerationErrorPage({ prompt, message, onBack, onRetry }) {
  return (
    <main className="hero">
      <section className="card errorPanel">
        <div className="errorMark">!</div>
        <h1>회로를 생성하지 못했어요</h1>
        <p>샘플 회로로 대체하지 않았습니다. 오류를 확인한 뒤 다시 시도해주세요.</p>
        <div className="errorPrompt">
          <b>입력 문장</b>
          <span>{prompt}</span>
        </div>
        <div className="notice errorNotice">{message}</div>
        <div className="pageActions errorActions">
          <button className="secondaryBtn" onClick={onBack}>입력 수정</button>
          <button className="mainBtn" onClick={onRetry}>다시 생성</button>
        </div>
      </section>
    </main>
  );
}

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
      nextLabel="회로도 보기"
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
          {viewMode === "3d" ? <Circuit3DView circuit={circuit} /> : <CanvasView circuit={circuit} />}
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
