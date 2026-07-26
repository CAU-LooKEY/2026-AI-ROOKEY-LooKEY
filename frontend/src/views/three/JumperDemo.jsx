import { ArrowLeft, Cable, CheckCircle2, CircleAlert, MousePointer2 } from "lucide-react";
import { useMemo, useState } from "react";
import Circuit3DView from "./Circuit3DView.jsx";
import "./jumperDemo.css";

const parts = [
  {
    id: "arduino",
    label: "Arduino UNO R3",
    componentKey: "arduino-uno-r3",
    position: { x: 60, y: 170 },
    width: 260,
  },
  {
    id: "breadboard",
    label: "Breadboard Half",
    componentKey: "breadboard-half",
    position: { x: 430, y: 230 },
    width: 300,
  },
  {
    id: "sensor",
    label: "HC-SR04",
    componentKey: "hc-sr04",
    position: { x: 470, y: 40 },
    width: 220,
  },
  {
    id: "resistor",
    label: "220Ω Resistor",
    componentKey: "resistor-220-ohm",
    position: { x: 760, y: 270 },
    width: 150,
  },
];

const validConnections = [
  {
    id: "demo-male-male",
    source: "arduino",
    sourcePin: "5V",
    target: "breadboard",
    targetPin: "A1",
    label: "Arduino female header ↔ breadboard female hole",
  },
  {
    id: "demo-male-female",
    source: "arduino",
    sourcePin: "D9",
    target: "sensor",
    targetPin: "TRIG",
    label: "Arduino female header ↔ sensor male pin",
  },
  {
    id: "demo-female-female",
    source: "sensor",
    sourcePin: "ECHO",
    target: "resistor",
    targetPin: "LEAD_A",
    label: "Sensor male pin ↔ resistor male lead",
  },
  {
    id: "demo-ground",
    source: "sensor",
    sourcePin: "GND",
    target: "arduino",
    targetPin: "GND_P1",
    label: "Ground color rule",
  },
];

const invalidConnection = {
  id: "demo-invalid-gender",
  source: "arduino",
  sourcePin: "D3",
  sourceConnector: "female",
  target: "breadboard",
  targetPin: "A5",
  targetConnector: "female",
  label: "Invalid female connector pairing",
};

const scenarios = [
  ["수-수", "Arduino 헤더 ↔ 브레드보드 홀", "male-male"],
  ["수-암", "Arduino 헤더 ↔ 센서 수 핀", "male-female"],
  ["암-암", "센서 수 핀 ↔ 저항 리드", "female-female"],
];

export default function JumperDemo() {
  const [showInvalidExample, setShowInvalidExample] = useState(false);
  const circuit = useMemo(
    () => ({
      title: "Interactive jumper connector demo",
      parts,
      connections: showInvalidExample
        ? [...validConnections, invalidConnection]
        : validConnections,
    }),
    [showInvalidExample],
  );

  return (
    <main className="jumperDemo">
      <header className="jumperDemoHeader">
        <div>
          <a href="/assets-3d" aria-label="3D Asset Lab으로 돌아가기">
            <ArrowLeft size={18} />
          </a>
          <Cable size={21} aria-hidden="true" />
          <div>
            <h1>Jumper Connector Lab</h1>
            <p>두 핀을 선택해 적합한 점퍼선을 즉시 생성하고 검사합니다.</p>
          </div>
        </div>
        <label className={showInvalidExample ? "invalidToggle active" : "invalidToggle"}>
          <input
            type="checkbox"
            checked={showInvalidExample}
            onChange={(event) => setShowInvalidExample(event.target.checked)}
          />
          <CircleAlert size={16} />
          오류 조합 예시
        </label>
      </header>

      <section className="jumperScenarioGrid" aria-label="점퍼선 자동 선택 규격">
        {scenarios.map(([type, description, code]) => (
          <article key={type}>
            <CheckCircle2 size={17} aria-hidden="true" />
            <div>
              <strong>{type}</strong>
              <span>{description}</span>
            </div>
            <code>{code}</code>
          </article>
        ))}
        <article className="interactionHint">
          <MousePointer2 size={17} aria-hidden="true" />
          <div>
            <strong>직접 연결</strong>
            <span>파란 핀 두 개를 차례로 선택</span>
          </div>
        </article>
      </section>

      <section className="jumperDemoStage">
        <Circuit3DView circuit={circuit} interactive />
      </section>

      <footer className="jumperDemoFooter">
        <span><i className="power" />전원 빨강</span>
        <span><i className="ground" />GND 검정</span>
        <span><i className="signal" />신호선 자동 배색</span>
        <span>브레드보드 홀: 2.54mm pitch · 0.64mm 수 핀</span>
      </footer>
    </main>
  );
}
