from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.assembly_plan import AssemblyPlan
from app.services.component_rules import (
    pin_capabilities,
    required_wire_connector,
    supported_component_keys,
    supported_component_pins,
    supported_pin_keys,
)


SUPPORTED_COMPONENT_PINS = supported_component_pins()

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
    id: str = Field(
        description=(
            "Unique instance id for this part. Connections source and target "
            "must reference this value."
        )
    )
    label: str
    component_key: str = Field(
        alias="componentKey",
        json_schema_extra={"enum": list(supported_component_keys())},
    )
    position: Position
    width: float = Field(gt=0)


class CircuitConnection(ApiModel):
    id: str
    source: str = Field(
        description="Part instance id from circuit.parts; never a pin name."
    )
    source_pin: str = Field(
        alias="sourcePin",
        description="Pin name on the source part; never a part id.",
        json_schema_extra={"enum": list(supported_pin_keys())},
    )
    target: str = Field(
        description="Part instance id from circuit.parts; never a pin name."
    )
    target_pin: str = Field(
        alias="targetPin",
        description="Pin name on the target part; never a part id.",
        json_schema_extra={"enum": list(supported_pin_keys())},
    )
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
    tutor_steps: list[TutorStep] = Field(alias="tutorSteps", max_length=5)
    warnings: list[str] = Field(max_length=4)
    validation_results: list[ValidationResult] = Field(
        alias="validationResults",
        max_length=6,
    )
    unsupported_components: list[str] = Field(alias="unsupportedComponents")
    assembly_plan: AssemblyPlan | None = Field(default=None, alias="assemblyPlan")

    @staticmethod
    def _required_wire_connector(component_key: str) -> WireConnector:
        return required_wire_connector(component_key)

    @staticmethod
    def _is_ground_pin(component_key: str, pin_key: str) -> bool:
        return "ground" in pin_capabilities(component_key, pin_key)

    @staticmethod
    def _is_power_pin(component_key: str, pin_key: str) -> bool:
        capabilities = pin_capabilities(component_key, pin_key)
        return bool({"power", "power_5v", "power_3v3"} & capabilities)

    @model_validator(mode="after")
    def validate_circuit_references(self):
        parts_by_id = {part.id: part for part in self.circuit.parts}
        if len(parts_by_id) != len(self.circuit.parts):
            seen: set[str] = set()
            duplicates: set[str] = set()
            for part in self.circuit.parts:
                if part.id in seen:
                    duplicates.add(part.id)
                seen.add(part.id)
            raise ValueError(
                "Circuit part ids must be unique. Duplicate ids: "
                f"{', '.join(sorted(duplicates))}."
            )

        for part in self.circuit.parts:
            if part.component_key not in SUPPORTED_COMPONENT_PINS:
                raise ValueError(
                    f"Unsupported componentKey: {part.component_key}"
                )

        signal_index = 0
        for connection in self.circuit.connections:
            source = parts_by_id.get(connection.source)
            target = parts_by_id.get(connection.target)
            if source is None:
                raise ValueError(
                    f"Connection '{connection.id}' source references unknown "
                    f"part id '{connection.source}'."
                )
            if target is None:
                raise ValueError(
                    f"Connection '{connection.id}' target references unknown "
                    f"part id '{connection.target}'."
                )

            if connection.source_pin not in SUPPORTED_COMPONENT_PINS[
                source.component_key
            ]:
                allowed_pins = ", ".join(
                    sorted(SUPPORTED_COMPONENT_PINS[source.component_key])
                )
                raise ValueError(
                    f"Connection '{connection.id}' source pin "
                    f"'{connection.source_pin}' is invalid for part "
                    f"'{source.id}' ({source.component_key}). Allowed pins: "
                    f"{allowed_pins}."
                )
            if connection.target_pin not in SUPPORTED_COMPONENT_PINS[
                target.component_key
            ]:
                allowed_pins = ", ".join(
                    sorted(SUPPORTED_COMPONENT_PINS[target.component_key])
                )
                raise ValueError(
                    f"Connection '{connection.id}' target pin "
                    f"'{connection.target_pin}' is invalid for part "
                    f"'{target.id}' ({target.component_key}). Allowed pins: "
                    f"{allowed_pins}."
                )

            connection.source_connector = self._required_wire_connector(
                source.component_key
            )
            connection.target_connector = self._required_wire_connector(
                target.component_key
            )
            connection.wire_type = (
                f"{connection.source_connector}-{connection.target_connector}"
            )

            if self._is_ground_pin(
                source.component_key, connection.source_pin
            ) or self._is_ground_pin(
                target.component_key, connection.target_pin
            ):
                connection.color = "#1f2937"
            elif self._is_power_pin(
                source.component_key, connection.source_pin
            ) or self._is_power_pin(
                target.component_key, connection.target_pin
            ):
                connection.color = "#dc2626"
            else:
                connection.color = SIGNAL_WIRE_COLORS[
                    signal_index % len(SIGNAL_WIRE_COLORS)
                ]
                signal_index += 1

        return self
