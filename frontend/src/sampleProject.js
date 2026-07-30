export const examplePrompts = [
  {
    label: "버튼 LED 깜빡이기",
    prompt: "LED가 1초마다 깜빡이는 회로를 만들어줘 버튼 누르면 on/off 되고",
  },
  {
    label: "거리 감지 조명",
    prompt: "손을 가까이 대면 LED가 켜지는 장치를 만들어줘",
  },
  {
    label: "버튼 부저",
    prompt: "버튼을 누르면 소리가 나는 회로를 만들어줘",
  },
  {
    label: "온도 측정기",
    prompt: "온도를 측정해서 시리얼 모니터에 보여줘",
  },
];

export const sampleProject = {
  title: "손 가까이 대면 LED 켜기",
  difficulty: "초급",
  estimatedTime: "15분",
  shareMessage: "공유 링크가 준비되었습니다. 백엔드 연결 전까지는 데모 메시지로 표시됩니다.",
  parts: [
    {
      title: "1. Arduino Uno",
      desc: "센서 값을 읽고 LED를 제어하는 중심 보드입니다.",
    },
    {
      title: "2. HC-SR04 거리 센서",
      desc: "손과 센서 사이의 거리를 초음파로 측정합니다.",
    },
    {
      title: "3. LED + 220Ω 저항",
      desc: "가까운 물체가 감지되면 빛으로 상태를 알려줍니다.",
    },
  ],
  code: `const int trigPin = 9;
const int echoPin = 10;
const int ledPin = 3;

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH);
  int distance = duration * 0.034 / 2;

  digitalWrite(ledPin, distance > 0 && distance < 15 ? HIGH : LOW);
  Serial.println(distance);
  delay(100);
}`,
  tutorSteps: [
    {
      title: "1. 거리 측정",
      desc: "Arduino가 TRIG 핀으로 초음파 센서에 짧은 신호를 보내면 센서가 초음파를 발사합니다.",
    },
    {
      title: "2. 시간 계산",
      desc: "ECHO 핀은 초음파가 되돌아오는 시간을 Arduino에 알려주고, 코드는 이 시간으로 거리를 계산합니다.",
    },
    {
      title: "3. LED 제어",
      desc: "계산한 거리가 15cm보다 가까우면 D3 핀을 HIGH로 만들어 LED를 켭니다.",
    },
    {
      title: "주의할 점",
      desc: "LED에는 반드시 저항을 직렬로 연결해야 하며, 센서의 VCC와 GND가 빠지면 측정이 되지 않습니다.",
    },
  ],
};

export const ledBlinkDemoProject = {
  title: "버튼으로 LED 1초 깜빡임 켜고 끄기",
  difficulty: "초급",
  estimatedTime: "15분",
  shareMessage: "버튼으로 LED 1초 깜빡임을 켜고 끄는 데모 프로젝트를 공유합니다.",
  parts: [
    {
      title: "1. Arduino Uno",
      desc: "D2로 버튼 입력을 읽고 D3로 LED 깜빡임 출력을 제어합니다.",
    },
    {
      title: "2. 6x6 푸시 버튼",
      desc: "누를 때마다 LED 깜빡임 동작을 켜거나 끄는 입력 부품입니다.",
    },
    {
      title: "3. LED + 220Ω 저항",
      desc: "LED는 1초마다 깜빡이고 저항은 LED 전류를 제한합니다.",
    },
  ],
  code: `const int buttonPin = 2;
const int ledPin = 3;
bool blinkEnabled = false;
bool lastButtonState = HIGH;
unsigned long lastBlinkTime = 0;
bool ledState = LOW;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  int buttonState = digitalRead(buttonPin);

  if (lastButtonState == HIGH && buttonState == LOW) {
    blinkEnabled = !blinkEnabled;
    delay(30);
  }
  lastButtonState = buttonState;

  if (blinkEnabled && millis() - lastBlinkTime >= 1000) {
    lastBlinkTime = millis();
    ledState = !ledState;
    digitalWrite(ledPin, ledState);
  }

  if (!blinkEnabled) {
    ledState = LOW;
    digitalWrite(ledPin, LOW);
  }
}`,
  tutorSteps: [
    {
      title: "1. 버튼 입력",
      desc: "버튼 한쪽은 D2에, 반대쪽은 GND에 연결하고 코드에서 INPUT_PULLUP을 사용합니다.",
    },
    {
      title: "2. LED 출력",
      desc: "LED에 너무 큰 전류가 흐르지 않도록 보호합니다.",
    },
    {
      title: "3. 토글 깜빡임",
      desc: "버튼을 누를 때마다 깜빡임 상태가 바뀌고, 켜진 동안 millis()로 1초마다 LED 상태를 전환합니다.",
    },
  ],
  warnings: [
    "LED에는 반드시 220Ω 저항을 직렬로 연결하세요.",
    "INPUT_PULLUP 회로이므로 버튼을 5V에 직접 연결하지 않습니다.",
  ],
  validationResults: [
    {
      ruleId: "DEMO",
      level: "PASS",
      message: "로컬 검증용 샘플 회로입니다. API 없이 2D/3D 화면을 확인할 수 있습니다.",
    },
  ],
  unsupportedComponents: [],
};

export const ledBlinkDemoCircuit = {
  parts: [
    {
      id: "arduino",
      label: "Arduino Uno",
      componentKey: "arduino-uno-r3",
      position: { x: 45, y: 135 },
      width: 230,
    },
    {
      id: "button",
      label: "Push Button",
      componentKey: "pushbutton-6x6",
      position: { x: 390, y: 210 },
      width: 90,
    },
    {
      id: "resistor",
      label: "220Ω 저항",
      componentKey: "resistor-220-ohm",
      position: { x: 430, y: 330 },
      width: 125,
    },
    {
      id: "led",
      label: "LED",
      componentKey: "led-5mm-blue",
      position: { x: 620, y: 300 },
      width: 68,
    },
  ],
  connections: [
    {
      id: "button-signal",
      source: "arduino",
      sourcePin: "D2",
      target: "button",
      targetPin: "A1",
      label: "D2 -> 버튼",
      color: "#2563eb",
      sourceConnector: "male",
      targetConnector: "female",
      wireType: "male-female",
    },
    {
      id: "button-ground",
      source: "button",
      sourcePin: "B1",
      target: "arduino",
      targetPin: "GND_P1",
      label: "버튼 -> GND",
      color: "#1f2937",
      sourceConnector: "female",
      targetConnector: "male",
      wireType: "female-male",
    },
    {
      id: "led-signal",
      source: "arduino",
      sourcePin: "D3",
      target: "resistor",
      targetPin: "LEAD_A",
      label: "D3 -> 저항",
      color: "#f97316",
      sourceConnector: "male",
      targetConnector: "female",
      wireType: "male-female",
    },
    {
      id: "wire-resistor-led",
      source: "resistor",
      sourcePin: "LEAD_B",
      target: "led",
      targetPin: "ANODE",
      label: "저항 -> LED +",
      color: "#ea580c",
      sourceConnector: "female",
      targetConnector: "female",
      wireType: "female-female",
    },
    {
      id: "wire-led-gnd",
      source: "led",
      sourcePin: "CATHODE",
      target: "arduino",
      targetPin: "GND_P2",
      label: "LED - -> GND",
      color: "#1f2937",
      sourceConnector: "female",
      targetConnector: "male",
      wireType: "female-male",
    },
  ],
  assemblyPlan: {
    schemaVersion: "1.0",
    components: [
      { instanceId: "breadboard-1", assetSlug: "breadboard-half", label: "Half-size Breadboard" },
      { instanceId: "arduino", assetSlug: "arduino-uno-r3", label: "Arduino Uno" },
      { instanceId: "button", assetSlug: "pushbutton-6x6", label: "Push Button 6x6" },
      { instanceId: "resistor", assetSlug: "resistor-220-ohm", label: "220Ω 저항" },
      { instanceId: "led", assetSlug: "led-5mm-blue", label: "LED" },
    ],
    placements: [
      {
        componentId: "breadboard-1",
        mode: "board",
        status: "placed",
        transform: { position: { x: 0, y: 0, z: 0 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 } },
        addresses: {},
      },
      {
        componentId: "arduino",
        mode: "free",
        status: "placed",
        transform: { position: { x: -10.2, y: 0, z: 0 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 } },
        addresses: {},
      },
      {
        componentId: "button",
        mode: "breadboard",
        status: "placed",
        transform: { position: { x: -0.031145, y: 0, z: -0.000665 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 } },
        addresses: { A1: "E2", A2: "F2", B1: "E5", B2: "F5" },
      },
      {
        componentId: "resistor",
        mode: "breadboard",
        status: "placed",
        transform: { position: { x: -0.012095, y: 0, z: -0.004565 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 } },
        addresses: { LEAD_A: "E9", LEAD_B: "E13" },
      },
      {
        componentId: "led",
        mode: "breadboard",
        status: "placed",
        transform: { position: { x: -0.023525, y: 0, z: -0.004565 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 } },
        addresses: { ANODE: "E6", CATHODE: "E7" },
      },
    ],
    connections: [
      {
        id: "button-signal",
        source: { componentId: "arduino", pin: "D2" },
        target: { componentId: "button", pin: "A1", address: "D2" },
        electricalNode: "node:breadboard:terminal-AE-2",
        color: "#2563eb",
      },
      {
        id: "button-ground",
        source: { componentId: "button", pin: "B1", address: "D5" },
        target: { componentId: "arduino", pin: "GND_P1" },
        electricalNode: "node:breadboard:terminal-AE-5",
        color: "#1f2937",
      },
      {
        id: "led-signal",
        source: { componentId: "arduino", pin: "D3" },
        target: { componentId: "resistor", pin: "LEAD_A", address: "A9" },
        electricalNode: "node:breadboard:terminal-AE-9",
        color: "#f97316",
      },
      {
        id: "wire-resistor-led",
        source: { componentId: "resistor", pin: "LEAD_B", address: "A13" },
        target: { componentId: "led", pin: "ANODE", address: "A6" },
        electricalNode: "node:breadboard:terminal-AE-13",
        color: "#ea580c",
      },
      {
        id: "wire-led-gnd",
        source: { componentId: "led", pin: "CATHODE", address: "A7" },
        target: { componentId: "arduino", pin: "GND_P2" },
        electricalNode: "node:breadboard:terminal-AE-7",
        color: "#1f2937",
      },
    ],
    warnings: [
      {
        code: "LOCAL_DEMO",
        severity: "INFO",
        message: "API 없이 3D 조립 화면을 검증하기 위한 로컬 Assembly Plan입니다.",
        componentIds: [],
        connectionIds: [],
      },
    ],
  },
};

export const sampleSavedProjects = [
  {
    title: "손 가까이 대면 LED 켜기",
    tags: ["거리 센서", "LED", "완료"],
    updatedAt: "2026.05.07",
    status: "complete",
  },
  {
    title: "버튼 누르면 부저 울리기",
    tags: ["버튼", "부저"],
    updatedAt: "2026.05.06",
  },
  {
    title: "온도 측정기 만들기",
    tags: ["온도 센서", "LCD"],
    updatedAt: "2026.05.05",
  },
];
