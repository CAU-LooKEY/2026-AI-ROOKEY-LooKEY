from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssemblyModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class Vector3(AssemblyModel):
    x: float
    y: float
    z: float


class Transform(AssemblyModel):
    position: Vector3
    rotation: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=0))
    scale: Vector3 = Field(default_factory=lambda: Vector3(x=1, y=1, z=1))


class AssemblyComponent(AssemblyModel):
    instance_id: str = Field(alias="instanceId", min_length=1)
    asset_slug: str = Field(alias="assetSlug", min_length=1)
    label: str


class Placement(AssemblyModel):
    component_id: str = Field(alias="componentId")
    transform: Transform
    mode: Literal["free", "board", "breadboard"] = "free"
    addresses: dict[str, str] = Field(default_factory=dict)


class ConnectionEndpoint(AssemblyModel):
    component_id: str = Field(alias="componentId")
    pin: str
    address: str | None = None


class AssemblyConnection(AssemblyModel):
    id: str
    source: ConnectionEndpoint
    target: ConnectionEndpoint
    electrical_node: str = Field(alias="electricalNode")
    color: str


class AssemblyWarning(AssemblyModel):
    code: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    message: str
    component_ids: list[str] = Field(default_factory=list, alias="componentIds")
    connection_ids: list[str] = Field(default_factory=list, alias="connectionIds")


class AssemblyPlan(AssemblyModel):
    schema_version: Literal["1.0"] = Field(default="1.0", alias="schemaVersion")
    components: list[AssemblyComponent]
    placements: list[Placement]
    connections: list[AssemblyConnection]
    warnings: list[AssemblyWarning]

    @model_validator(mode="after")
    def validate_references(self):
        component_ids = [component.instance_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Assembly component instanceIds must be unique.")
        known = set(component_ids)
        if {item.component_id for item in self.placements} != known:
            raise ValueError("Every component must have exactly one placement.")
        if len(self.placements) != len(known):
            raise ValueError("Placement componentIds must be unique.")
        for connection in self.connections:
            if connection.source.component_id not in known:
                raise ValueError("Connection source references an unknown component.")
            if connection.target.component_id not in known:
                raise ValueError("Connection target references an unknown component.")
        return self
