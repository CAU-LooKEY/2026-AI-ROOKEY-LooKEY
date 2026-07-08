import { useState } from "react";
import CanvasView from "./views/canvas/CanvasView.jsx";
import { sampleCircuit } from "./views/canvas/sampleCircuit.js";
import { examplePrompts, sampleProject, sampleSavedProjects } from "./sampleProject.js";
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
  const [prompt, setPrompt] = useState(examplePrompts[1].prompt);
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [shareMessage, setShareMessage] = useState("");
  const [copyMessage, setCopyMessage] = useState("");

  const savePrompt = () => {
    setSavedPrompts((items) => {
      if (items.includes(prompt)) return items;
      return [prompt, ...items];
    });
  };

  const sharePrompt = () => {
    savePrompt();
    setShareMessage(sampleProject.shareMessage);
  };

  return (
    <div className="app">
      <header className="nav">
        <button className="logoButton" onClick={() => setPage("home")}>
          ⚙️ Prompt to Circuit
        </button>
        <div className="menu">
          <button onClick={() => setPage("home")}>홈</button>
          <button onClick={() => setPage("summary")}>내 프로젝트</button>
          <button onClick={() => setPage("tutor")}>AI 튜터</button>
          <button onClick={() => setPage("history")}>저장</button>
        </div>
      </header>

      {page === "home" && (
        <HomePage
          prompt={prompt}
          onPromptChange={setPrompt}
          onExampleSelect={setPrompt}
          onNext={() => setPage("loading")}
        />
      )}
      {page === "loading" && <LoadingPage onNext={() => setPage("summary")} />}
      {page === "summary" && (
        <SummaryPage
          prompt={prompt}
          onStepSelect={setPage}
          onBack={() => setPage("home")}
          onNext={() => setPage("circuit")}
        />
      )}
      {page === "circuit" && (
        <CircuitPage onStepSelect={setPage} onBack={() => setPage("summary")} onNext={() => setPage("code")} />
      )}
      {page === "code" && (
        <CodePage
          copyMessage={copyMessage}
          onCopyMessage={setCopyMessage}
          onStepSelect={setPage}
          onBack={() => setPage("circuit")}
          onNext={() => setPage("tutor")}
        />
      )}
      {page === "tutor" && <TutorPage onStepSelect={setPage} onBack={() => setPage("code")} onNext={() => setPage("history")} />}
      {page === "history" && (
        <HistoryPage
          prompt={prompt}
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

        <button className="mainBtn" onClick={onNext}>
          AI로 회로 만들기
        </button>
      </section>
    </main>
  );
}

function LoadingPage({ onNext }) {
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
            <b>동작 분석 완료</b>
            <span>사용자가 원하는 기능을 이해했어요.</span>
          </div>
          <div className="done">
            <b>필요한 부품 찾기 완료</b>
            <span>거리 센서, LED, 저항 등을 선택했어요.</span>
          </div>
          <div className="active">
            <b>회로 연결 구성 중</b>
            <span>핀 번호와 연결 구조를 설계하고 있어요.</span>
          </div>
          <div>
            <b>코드 작성 중</b>
            <span>Arduino 예제 코드를 생성합니다.</span>
          </div>
          <div>
            <b>AI 튜터 설명 준비 중</b>
            <span>초보자 눈높이에 맞춰 설명합니다.</span>
          </div>
        </div>

        <div className="pageActions loadingActions">
          <button className="secondaryBtn">이전</button>
          <button className="mainBtn" onClick={onNext}>
            결과 보기
          </button>
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

function SummaryPage({ prompt, onStepSelect, onBack, onNext }) {
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
      <div className="promptPreview">{prompt}</div>

      <div className="stats">
        <div>
          <b>필요 부품</b>
          <strong>{sampleCircuit.parts.length}개</strong>
        </div>
        <div>
          <b>난이도</b>
          <strong>{sampleProject.difficulty}</strong>
        </div>
        <div>
          <b>예상 시간</b>
          <strong>{sampleProject.estimatedTime}</strong>
        </div>
      </div>

      <div className="parts">
        {sampleProject.parts.map((part) => (
          <PartCard key={part.title} title={part.title} desc={part.desc} />
        ))}
      </div>
    </ResultShell>
  );
}

function CircuitPage({ onStepSelect, onBack, onNext }) {
  return (
    <ResultShell
      activeStep="circuit"
      title="회로도"
      desc="전원, 접지, 신호선을 구분해서 부품 사이의 실제 연결을 확인합니다."
      onStepSelect={onStepSelect}
      onBack={onBack}
      onNext={onNext}
      nextLabel="예제 코드 보기"
    >
      <div className="circuitStage">
        <div className="circuitChecklist">
          <div className="done">① 보드 배치 ✓</div>
          <div className="done">② 센서 연결 ✓</div>
          <div className="active">③ LED 연결 ●</div>
          <div>④ 전체 회로 확인</div>
        </div>
        <div className="circuitCanvasPanel">
          <CanvasView />
        </div>
      </div>
      <div className="explainBox">
        <b>3단계.</b> LED와 저항을 연결합니다. D3 핀 → LED(+) → LED(-) → 저항 → GND 순서로 연결합니다.
      </div>
    </ResultShell>
  );
}

function CodePage({ copyMessage, onCopyMessage, onStepSelect, onBack, onNext }) {
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(sampleProject.code);
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
        <code>{sampleProject.code}</code>
      </pre>
      <div className="explainBox">
        이 코드는 거리 센서의 초음파 왕복 시간을 이용해 거리를 계산합니다. 계산된 거리가 가까우면 LED를 켜고, 멀어지면 LED를 끕니다.
      </div>
    </ResultShell>
  );
}

function TutorPage({ onStepSelect, onBack, onNext }) {
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
          {sampleProject.tutorSteps.map((step) => (
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

function HistoryPage({ prompt, savedPrompts, shareMessage, onSave, onShare, onStepSelect, onBack, onHome }) {
  const projects =
    savedPrompts.length > 0
      ? [
          {
            ...sampleSavedProjects[0],
            title: sampleProject.title,
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
