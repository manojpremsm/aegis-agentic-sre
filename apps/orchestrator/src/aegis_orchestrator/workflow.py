from aegis_orchestrator import (
    InvestigationStatus,
    InvestigationResult,
    fetch_incident_summary,
)
import uuid
import httpx


def investigate_incident(
    incident_id: uuid.UUID,
    base_url: str,
    client: httpx.Client,
) -> InvestigationResult:
    try:
        summary = fetch_incident_summary(incident_id, base_url, client)
        return InvestigationResult(
            incident_id=(incident_id),
            status=InvestigationStatus.COMPLETED,
            summary=summary,
            error=None,
        )
    except httpx.HTTPError:
        return InvestigationResult(
            incident_id=incident_id,
            status=InvestigationStatus.FAILED,
            summary=None,
            error="Investigator service unavailable",
        )
