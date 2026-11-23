from aegis_orchestrator import (
    InvestigationStatus,
    InvestigationResult,
    fetch_incident_summary,
    SeverityAssessment,

)
from aegis_orchestrator.agents.severity_agent import analyze_severity
import uuid
import httpx


def investigate_incident(
    incident_id: uuid.UUID,
    base_url: str,
    client: httpx.Client,
) -> InvestigationResult:
    try:
        summary = fetch_incident_summary(incident_id, base_url, client)
        assessment = analyze_severity(summary=summary)
        return InvestigationResult(
            incident_id=(incident_id),
            status=InvestigationStatus.COMPLETED,
            summary=summary,
            severity_assessment = assessment,
            error=None,
        )
    except httpx.HTTPError:
        return InvestigationResult(
            incident_id=incident_id,
            status=InvestigationStatus.FAILED,
            summary=None,
            severity_assessment = None,
            error="Investigator service unavailable",
        )
