from aegis_orchestrator import SeverityAssessment
from aegis_contracts import IncidentSummary

def analyze_severity(summary: IncidentSummary) -> SeverityAssessment:
    critical = summary.severity_counts["CRITICAL"]
    warning = summary.severity_counts["WARNING"]
    info = summary.severity_counts["INFO"]

    if critical> 0:
        return SeverityAssessment(incident_id=summary.incident_id,risk_level="HIGH",reason="Critical events detected in incident evidence",requires_immediate_attention=True)
    elif warning > 0 :
        return SeverityAssessment(incident_id=summary.incident_id,risk_level="MEDIUM",reason="Warning events detected; no critical events",requires_immediate_attention=False)
    elif info > 0 :
        return SeverityAssessment(incident_id=summary.incident_id,risk_level="LOW",reason="Informational events only",requires_immediate_attention=False)
    else:
        return SeverityAssessment(incident_id=summary.incident_id,risk_level="UNKNOWN",reason="No incident events available for severity assessment",requires_immediate_attention=False)

