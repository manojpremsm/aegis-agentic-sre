from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from aegis_contracts import IncidentSummary


class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InvestigationResult(BaseModel):
    incident_id: UUID
    status: InvestigationStatus
    summary: IncidentSummary | None = None
    error: str | None = None
