from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class SeverityAssessment(BaseModel):
    incident_id: UUID
    risk_level: RiskLevel
    reason: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    requires_immediate_attention: bool