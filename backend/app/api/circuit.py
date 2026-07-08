from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


class CircuitGenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        examples=["버튼을 누르면 LED가 켜지는 회로를 만들고 싶어"],
    )


class Position(BaseModel):
    x: float
    y: float


class CircuitNode(BaseModel):
    id: str
    componentKey: str
    type: Literal["board", "input", "output", "passive", "power"]
    label: str
    position: Position
    data: dict[str, Any]


class CircuitEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    label: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class CircuitResponse(BaseModel):
    id: str
    title: str
    userPrompt: str
    summary: str
    nodes: list[CircuitNode]
    edges: list[CircuitEdge]
    code: str
    warnings: list[str]
    explanation: list[str]


DEMO_PROMPT = "버튼을 누르면 LED가 켜지는 회로를 만들고 싶어"

DEMO_CODE = """\
const int buttonPin = 2;
const int ledPin = 9;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  int buttonState = digitalRead(buttonPin);

  if (buttonState == LOW) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}
"""


def build_demo_circuit(prompt: str = DEMO_PROMPT) -> CircuitResponse:
    return CircuitResponse(
        id="demo-button-led",
        title="버튼으로 LED 켜기",
        userPrompt=prompt,
        summary="푸시 버튼을 누르면 빨간 LED가 켜지는 가장 기본적인 입력-출력 회로입니다.",
        nodes=[
            CircuitNode(
                id="board-01",
                componentKey="generic_uno_board",
                type="board",
                label="범용 마이크로컨트롤러 보드",
                position=Position(x=100, y=200),
                data={
                    "pins": ["5V", "GND", "D2", "D9"],
                    "asset": "/assets/boards/generic_uno_board.glb",
                },
            ),
            CircuitNode(
                id="button-01",
                componentKey="push_button",
                type="input",
                label="푸시 버튼",
                position=Position(x=380, y=120),
                data={
                    "description": "사용자가 누르는 입력 부품입니다.",
                    "asset": "/assets/components/push_button.glb",
                },
            ),
            CircuitNode(
                id="resistor-01",
                componentKey="resistor_220_ohm",
                type="passive",
                label="220옴 저항",
                position=Position(x=390, y=280),
                data={
                    "resistanceOhm": 220,
                    "description": "LED에 너무 큰 전류가 흐르지 않도록 제한합니다.",
                    "asset": "/assets/components/resistor_220_ohm.glb",
                },
            ),
            CircuitNode(
                id="led-01",
                componentKey="red_led",
                type="output",
                label="빨간 LED",
                position=Position(x=640, y=280),
                data={
                    "color": "red",
                    "description": "전기 신호를 빛으로 보여주는 출력 부품입니다.",
                    "asset": "/assets/components/red_led.glb",
                },
            ),
        ],
        edges=[
            CircuitEdge(
                id="wire-01",
                source="board-01",
                sourceHandle="D2",
                target="button-01",
                targetHandle="signal",
                label="D2 -> Button",
                data={"wireColor": "green"},
            ),
            CircuitEdge(
                id="wire-02",
                source="board-01",
                sourceHandle="GND",
                target="button-01",
                targetHandle="gnd",
                label="GND -> Button",
                data={"wireColor": "black"},
            ),
            CircuitEdge(
                id="wire-03",
                source="board-01",
                sourceHandle="D9",
                target="resistor-01",
                targetHandle="input",
                label="D9 -> Resistor",
                data={"wireColor": "yellow"},
            ),
            CircuitEdge(
                id="wire-04",
                source="resistor-01",
                sourceHandle="output",
                target="led-01",
                targetHandle="anode",
                label="Resistor -> LED +",
                data={"wireColor": "yellow"},
            ),
            CircuitEdge(
                id="wire-05",
                source="led-01",
                sourceHandle="cathode",
                target="board-01",
                targetHandle="GND",
                label="LED - -> GND",
                data={"wireColor": "black"},
            ),
        ],
        code=DEMO_CODE,
        warnings=[
            "LED에는 반드시 저항을 직렬로 연결하세요.",
            "전원을 연결하기 전에 VCC와 GND가 직접 연결되지 않았는지 확인하세요.",
        ],
        explanation=[
            "버튼은 사용자의 입력을 보드의 D2 핀으로 전달합니다.",
            "LED는 D9 핀의 출력 신호에 따라 켜지거나 꺼집니다.",
            "저항은 LED를 보호하기 위해 전류를 제한합니다.",
        ],
    )


@router.get("/demo", response_model=CircuitResponse)
def get_demo_circuit():
    return build_demo_circuit()


@router.post("/generate", response_model=CircuitResponse)
def generate_circuit(request: CircuitGenerateRequest):
    return build_demo_circuit(prompt=request.prompt)
