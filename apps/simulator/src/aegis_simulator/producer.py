from aegis_contracts.events import IncidentEvent, IncidentSeverity
from datetime import  datetime,timezone
from uuid import uuid4,UUID


def create_incident_event(incident_id: UUID, severity: IncidentSeverity,source: str, title: str, description: str | None = None) -> IncidentEvent:
    """
    Create an IncidentEvent object.

    Args:
        incident_id (UUID): Unique identifier for the incident.
        severity (IncidentSeverity): Severity level of the incident.
        source (str): Source of the incident report.
        title (str): Title of the incident.
        description (str | None)Optional: Description of the incident.

    Returns:
        IncidentEvent: An instance of the IncidentEvent class.
    """

    return IncidentEvent(
        event_id=uuid4(),
        incident_id=incident_id,
        severity=severity,
        occurred_at=datetime.now(timezone.utc),
        source=source,
        schema_version="1.0",
        title=title,
        description=description
    )