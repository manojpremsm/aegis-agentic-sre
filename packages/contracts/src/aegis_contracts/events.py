from enum import Enum
from pydantic import BaseModel,AwareDatetime,Field,StringConstraints
from uuid import UUID
from datetime import datetime
from typing import Annotated,Literal

class IncidentSeverity(str,Enum):

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class IncidentEvent(BaseModel):

    event_id:UUID
    incident_id:UUID
    severity:IncidentSeverity
    occurred_at:AwareDatetime
    source:Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    schema_version: Literal["1.0"]
    title:Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = None
