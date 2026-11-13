import pytest
from aegis_simulator import create_incident_event,PaymentGatewayTimeoutScenario
from aegis_contracts import IncidentSeverity,IncidentEvent
import uuid


@pytest.fixture()
def valid_incedent_event_data():
    return {
        "incident_id": uuid.uuid4(),
        "severity": IncidentSeverity.WARNING,
        "source": "checkout-service",
        "title": "Payment gateway timeout",
        "description": "A timeout occurred while processing the payment through the gateway."
    }

def test_multiple_events_same_incident(valid_incedent_event_data):
    event1 = create_incident_event(**valid_incedent_event_data)
    event2 = create_incident_event(**valid_incedent_event_data)
    assert event1.incident_id == event2.incident_id
    assert event1.event_id != event2.event_id

def test_occurred_at_is_timezone_aware(valid_incedent_event_data):
    event = create_incident_event(**valid_incedent_event_data)
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.utcoffset().total_seconds() == 0

def test_description_omitted(valid_incedent_event_data):
    valid_incedent_event_data.pop("description")
    event = create_incident_event(**valid_incedent_event_data)
    assert event.description is None

def test_producers_contract(valid_incedent_event_data):
    event = create_incident_event(**valid_incedent_event_data)
    assert isinstance(event, IncidentEvent)
    assert isinstance(event.event_id, uuid.UUID)
    assert event.schema_version == "1.0"
    assert isinstance(event.source, str) and event.source.strip() != ""
    assert isinstance(event.title, str) and event.title.strip() != ""
    assert isinstance(event.severity, IncidentSeverity)
    assert event.source == valid_incedent_event_data["source"]
    assert event.title == valid_incedent_event_data["title"]
    assert event.severity == valid_incedent_event_data["severity"]
    assert event.incident_id == valid_incedent_event_data["incident_id"]

def test_payment_gateway_timeout_scenario():
    scenario = PaymentGatewayTimeoutScenario
    incident_id = uuid.uuid4()

    event = create_incident_event(
        incident_id=incident_id,
        severity=scenario.severity,
        source=scenario.source,
        title=scenario.title,
        description=scenario.description,
    )
    assert isinstance(event, IncidentEvent)
    assert event.incident_id == incident_id
    assert event.severity == scenario.severity
    assert event.source == scenario.source
    assert event.title == scenario.title
    assert event.description == scenario.description
    assert scenario.severity == IncidentSeverity.WARNING
    assert scenario.source == "checkout-service"
    assert scenario.title == "Payment gateway timeout"
    assert scenario.description == "Payment requests exceeded the configured gateway timeout."