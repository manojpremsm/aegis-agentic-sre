from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from aegis_contracts import IncidentSummary
from aegis_orchestrator import SeverityAssessment


class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InvestigationResult(BaseModel):
    incident_id: UUID
    status: InvestigationStatus
    summary: IncidentSummary | None = None
    severity_assessment: SeverityAssessment | None = None
    error: str | None = None
