from datetime import datetime, UTC
from pydantic import BaseModel, ConfigDict, Field


class OMPEnvelope(BaseModel):
    """Standard OMP envelope for wrapping messages."""

    omp_schema: str = Field(..., alias="schema", serialization_alias="schema")
    data: dict
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )
