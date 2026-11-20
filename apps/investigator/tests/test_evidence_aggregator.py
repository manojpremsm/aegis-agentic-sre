from aegis_simulator import create_incident_event
from aegis_contracts import IncidentEvent,IncidentSeverity
import uuid
from aegis_investigator import aggregate_events
import pytest

def test_aggregate_events_counts_severities_and_sources():

    incident_id = uuid.uuid4()
    event1 = create_incident_event(incident_id=incident_id,severity=IncidentSeverity.WARNING,source = "checkout-service",title="checkout 1")
    event2 = create_incident_event(incident_id=incident_id,severity=IncidentSeverity.INFO,source = "payment-service",title="payment 1")
    event3 = create_incident_event(incident_id=incident_id,severity=IncidentSeverity.WARNING,source = "checkout-service",title="checkout 2")
    events = [event1,event2,event3]
    summary = aggregate_events(incident_id, events)

    assert summary.incident_id == incident_id
    assert summary.total_events == 3
    assert summary.severity_counts == {"WARNING":2,"INFO":1,"CRITICAL":0}
    assert summary.sources == ["checkout-service","payment-service"]

def test_aggregate_events_handles_empty_event_list():

    incident_id = uuid.uuid4()
    events = []
    summary = aggregate_events(incident_id, events)

    assert summary.incident_id == incident_id
    assert summary.total_events == 0
    assert summary.severity_counts == {"WARNING":0,"INFO":0,"CRITICAL":0}
    assert summary.sources == []

def test_aggregate_events_rejects_events_from_another_incident():
    incident_a = uuid.uuid4()
    incident_b = uuid.uuid4()

    event1 = create_incident_event(
        incident_id=incident_a,
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="High checkout latency",
    )

    event2 = create_incident_event(
        incident_id=incident_b,
        severity=IncidentSeverity.CRITICAL,
        source="payment-service",
        title="Payment failures",
    )

    events = [event1, event2]

    with pytest.raises(ValueError, match="different incident"):
        aggregate_events(incident_a, events)
