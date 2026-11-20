from aegis_contracts import IncidentSeverity,IncidentEvent
from aegis_investigator import IncidentSummary
import uuid


def aggregate_events(
    incident_id: uuid.UUID,
    events: list[IncidentEvent],
) -> IncidentSummary:

    severity_counts = {"WARNING":0,"INFO":0,"CRITICAL":0}
    unique_sources = set()
    
    for event in events:
        if event.incident_id != incident_id:
            raise ValueError("Event belongs to a different incident")
        unique_sources.add(event.source)
        severity_counts[event.severity.value] += 1
    

    return IncidentSummary(incident_id=incident_id,total_events=len(events),severity_counts=severity_counts,sources=sorted(unique_sources))

