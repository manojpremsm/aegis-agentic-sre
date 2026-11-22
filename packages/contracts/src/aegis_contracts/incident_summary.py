from uuid import UUID

from pydantic import BaseModel, Field


class IncidentSummary(BaseModel):
    incident_id: UUID
    total_events: int = Field(ge=0)
    severity_counts: dict[str, int]
    sources: list[str]