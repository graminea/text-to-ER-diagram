"""Canonical conceptual ER contract, independent from providers and persistence."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Attribute(Contract):
    name: Name
    data_type: Literal["string", "integer", "decimal", "boolean", "date"] | None = None
    is_identifier: bool = False


class Entity(Contract):
    name: Name
    attributes: list[Attribute] = Field(min_length=1, max_length=50)


class Participation(Contract):
    entity: Name
    role: Name
    min_cardinality: Literal[0, 1]
    max_cardinality: Literal[1, "N"]

    @field_validator("min_cardinality", "max_cardinality", mode="before")
    @classmethod
    def reject_boolean_bounds(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Cardinality must not be a boolean.")
        return value


class Relationship(Contract):
    name: Name
    participants: list[Participation] = Field(min_length=2, max_length=2)


class ConceptualSchema(Contract):
    entities: list[Entity] = Field(min_length=1, max_length=40)
    relationships: list[Relationship] = Field(default_factory=list, max_length=80)
    assumptions: list[Text] = Field(default_factory=list, max_length=40)
    ambiguities: list[Text] = Field(default_factory=list, max_length=40)


class Issue(Contract):
    code: str
    path: str
    message: str
    severity: Literal["error", "warning"] = "error"


class ValidationReport(Contract):
    valid: bool
    issues: list[Issue]
