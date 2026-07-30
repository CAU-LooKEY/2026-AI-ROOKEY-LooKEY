from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.assembly_plan import AssemblyPlan


SUPPORTED_COMPONENT_PINS = {
    "arduino-uno-r3": {
        "SCL",
        "SDA",
        "AREF",
        "GND_D",
        "D13",
        "D12",
        "D11",
        "D10",
        "D9",
        "D8",
        "D7",
        "D6",
        "D5",
        "D4",
        "D3",
        "D2",
        "D1",
        "D0",
        "IOREF",
        "RESET",
        "3V3",
        "5V",
        "GND_P1",
        "GND_P2",
        "VIN",
        "A0",
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "AUX_RX",
        "AUX_TX",
        "AUX_5V",
        "AUX_GND_1",
        "AUX_SDA",
        "AUX_SCL",
        "AUX_3V3",
        "AUX_GND_2",
    },
    "hc-sr04": {"VCC", "TRIG", "ECHO", "GND"},
    "led-5mm-blue": {"ANODE", "CATHODE"},
    "pushbutton-6x6": {"A1", "A2", "B1", "B2"},
    "resistor-220-ohm": {"LEAD_A", "LEAD_B"},
}

SupportedComponentKey = Literal[
    "arduino-uno-r3",
    "hc-sr04",
    "led-5mm-blue",
    "pushbutton-6x6",
    "resistor-220-ohm",
]

SupportedPinKey = Literal[
    "SCL",
    "SDA",
    "AREF",
    "GND_D",
    "D13",
    "D12",
    "D11",
    "D10",
    "D9",
    "D8",
    "D7",
    "D6",
    "D5",
    "D4",
    "D3",
    "D2",
    "D1",
    "D0",
    "IOREF",
    "RESET",
    "3V3",
    "5V",
    "GND_P1",
    "GND_P2",
    "VIN",
    "A0",
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "AUX_RX",
    "AUX_TX",
    "AUX_5V",
    "AUX_GND_1",
    "AUX_SDA",
    "AUX_SCL",
    "AUX_3V3",
    "AUX_GND_2",
    "VCC",
    "TRIG",
    "ECHO",
    "GND",
    "ANODE",
    "CATHODE",
    "A1",
    "A2",
    "B1",
    "B2",
    "LEAD_A",
    "LEAD_B",
]

WireConnector = Literal["male", "female"]
WireType = Literal["male-male", "male-female", "female-male", "female-female"]

SIGNAL_WIRE_COLORS = [
    "#2563eb",
    "#059669",
    "#7c3aed",
    "#ea580c",
    "#0891b2",
    "#db2777",
]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CircuitGenerateRequest(ApiModel):
    prompt: str = Field(min_length=1, max_length=2000)


class Position(ApiModel):
    x: float
    y: float


class Component(ApiModel):
    id: str
    name: str
    quantity: int = Field(ge=1)
    role: str


class CircuitPart(ApiModel):
    id: str
    label: str
    component_key: SupportedComponentKey = Field(alias="componentKey")
    position: Position
    width: float = Field(gt=0)


class CircuitConnection(ApiModel):
    id: str
    source: str
    source_pin: SupportedPinKey = Field(alias="sourcePin")
    target: str
    target_pin: SupportedPinKey = Field(alias="targetPin")
    label: str
    color: str
    source_connector: WireConnector | None = Field(
        default=None,
        alias="sourceConnector",
    )
    target_connector: WireConnector | None = Field(
        default=None,
        alias="targetConnector",
    )
    wire_type: WireType | None = Field(default=None, alias="wireType")


class Circuit(ApiModel):
    parts: list[CircuitPart]
    connections: list[CircuitConnection]


class CodeMeta(ApiModel):
    used_pins: list[str]


class TutorStep(ApiModel):
    title: str
    desc: str


class ValidationResult(ApiModel):
    rule_id: str = Field(alias="ruleId")
    level: Literal["PASS", "WARNING", "ERROR"]
    message: str


class CircuitGenerationResponse(ApiModel):
    title: str
    intent: str
    difficulty: str
    estimated_time: str = Field(alias="estimatedTime")
    components: list[Component]
    circuit: Circuit
    code: str
    code_meta: CodeMeta = Field(alias="codeMeta")
    tutor_steps: list[TutorStep] = Field(alias="tutorSteps")
    warnings: list[str]
    validation_results: list[ValidationResult] = Field(alias="validationResults")
    unsupported_components: list[str] = Field(alias="unsupportedComponents")
    assembly_plan: AssemblyPlan | None = Field(default=None, alias="assemblyPlan")

    @staticmethod
    def _required_wire_connector(component_key: str) -> WireConnector:
        return "male" if component_key == "arduino-uno-r3" else "female"

    @staticmethod
    def _is_ground_pin(pin_key: str) -> bool:
        return "GND" in pin_key

    @staticmethod
    def _is_power_pin(pin_key: str) -> bool:
        return pin_key in {"5V", "3V3", "VCC", "VIN", "AUX_5V", "AUX_3V3"}

    @model_validator(mode="after")
    def validate_circuit_references(self):
        parts_by_id = {part.id: part for part in self.circuit.parts}
        if len(parts_by_id) != len(self.circuit.parts):
            raise ValueError("Circuit part ids must be unique.")

        for part in self.circuit.parts:
            if part.component_key not in SUPPORTED_COMPONENT_PINS:
                raise ValueError(
                    f"Unsupported componentKey: {part.component_key}"
                )

        used_arduino_pins: set[tuple[str, str]] = set()
        signal_index = 0
        for connection in self.circuit.connections:
            source = parts_by_id.get(connection.source)
            target = parts_by_id.get(connection.target)
            if source is None or target is None:
                raise ValueError("Connection references an unknown part id.")

            if connection.source_pin not in SUPPORTED_COMPONENT_PINS[
                source.component_key
            ]:
                raise ValueError(
                    f"Unknown source pin: {connection.source_pin}"
                )
            if connection.target_pin not in SUPPORTED_COMPONENT_PINS[
                target.component_key
            ]:
                raise ValueError(
                    f"Unknown target pin: {connection.target_pin}"
                )

            for component, pin in (
                (source, connection.source_pin),
                (target, connection.target_pin),
            ):
                if component.component_key != "arduino-uno-r3":
                    continue
                pin_ref = (component.id, pin)
                if pin_ref in used_arduino_pins:
                    raise ValueError(
                        f"Arduino pin {component.id}:{pin} is used by more than one jumper."
                    )
                used_arduino_pins.add(pin_ref)

            connection.source_connector = self._required_wire_connector(
                source.component_key
            )
            connection.target_connector = self._required_wire_connector(
                target.component_key
            )
            connection.wire_type = (
                f"{connection.source_connector}-{connection.target_connector}"
            )

            if self._is_ground_pin(connection.source_pin) or self._is_ground_pin(
                connection.target_pin
            ):
                connection.color = "#1f2937"
            elif self._is_power_pin(connection.source_pin) or self._is_power_pin(
                connection.target_pin
            ):
                connection.color = "#dc2626"
            else:
                connection.color = SIGNAL_WIRE_COLORS[
                    signal_index % len(SIGNAL_WIRE_COLORS)
                ]
                signal_index += 1

        return self
