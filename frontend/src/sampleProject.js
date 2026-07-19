export const examplePrompts = [
  {
    label: "LED 깜빡이기",
    prompt: "LED가 1초마다 깜빡이는 회로를 만들어줘",
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
