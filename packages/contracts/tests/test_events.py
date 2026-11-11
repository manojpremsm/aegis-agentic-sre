from aegis_contracts import IncidentSeverity,IncidentEvent
import uuid
from datetime import datetime
from pytz import timezone
import pytest
from pydantic import ValidationError

@pytest.fixture()
def valid_event_data():
    return {
        "event_id": uuid.uuid4(),
        "incident_id": uuid.uuid4(),
        "severity": IncidentSeverity.WARNING,
        "occurred_at": datetime.now(timezone('UTC')),
        "source": "checkout-service",
        "schema_version": "1.0",
        "title": "Checkout error rate elevated",
        "description": "5xx responses exceeded the configured threshold."
    }

def test_valid_incident_event(valid_event_data):
    event = IncidentEvent(**valid_event_data)

    assert event.event_id == valid_event_data["event_id"]
    assert event.severity == IncidentSeverity.WARNING

@pytest.mark.parametrize(
    "invalid_severity",
    ["emergency", "LOW", "critical", ""]
)
def test_invalid_severity(invalid_severity,valid_event_data):
   valid_event_data["severity"] = invalid_severity
   with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
   assert exc_info.value.errors()[0]["loc"] == ("severity",)
   assert exc_info.value.errors()[0]["type"] == "enum"

def test_naive_datetime_rejected(valid_event_data):
    valid_event_data["occurred_at"] = datetime.now()
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)  # Naive datetime   )
    assert exc_info.value.errors()[0]["loc"] == ("occurred_at",)
    assert exc_info.value.errors()[0]["type"] == "timezone_aware"

def test_source_whitespace_normalized(valid_event_data):
    valid_event_data["source"] = "   checkout-service   "
    event = IncidentEvent(**valid_event_data)
    assert event.source == "checkout-service"

def test_source_whitespace_only_rejected(valid_event_data):
    valid_event_data["source"] = "   "
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
    assert exc_info.value.errors()[0]["loc"] == ("source",)
    assert exc_info.value.errors()[0]["type"] == "string_too_short"

def test_incident_event_json_round_trip(valid_event_data):
    event = IncidentEvent(**valid_event_data)
    json_data = event.model_dump_json()
    new_event = IncidentEvent.model_validate_json(json_data)
    assert new_event == event
    assert isinstance(json_data, str)

def test_invalid_schema_version(valid_event_data):
    valid_event_data["schema_version"] = "2.0"
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
    assert exc_info.value.errors()[0]["loc"] == ("schema_version",)
    assert exc_info.value.errors()[0]["type"] == "literal_error"

def test_missing_schema_version(valid_event_data):
    valid_event_data.pop("schema_version")
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
    assert exc_info.value.errors()[0]["loc"] == ("schema_version",)
    assert exc_info.value.errors()[0]["type"] == "missing"

def test_description_omitted(valid_event_data):
    valid_event_data.pop("description")
    event = IncidentEvent(**valid_event_data)
    assert event.description is None

def test_blank_description_rejected(valid_event_data):
    valid_event_data["description"] = "   "
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
    assert exc_info.value.errors()[0]["loc"] == ("description",)
    assert exc_info.value.errors()[0]["type"] == "string_too_short"

def test_blank_title_rejected(valid_event_data):
    valid_event_data["title"] = "   "
    with pytest.raises(ValidationError) as exc_info:
        IncidentEvent(**valid_event_data)
    assert exc_info.value.errors()[0]["loc"] == ("title",)
    assert exc_info.value.errors()[0]["type"] == "string_too_short"