
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4
from aegis_investigator.api import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_receive_valid_incident_event():
    event_id = uuid4()
    incident_id = uuid4()

    payload = {
        "event_id": str(event_id),
        "incident_id": str(incident_id),
        "severity": "WARNING",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source": "checkout-service",
        "schema_version": "1.0",
        "title": "Payment gateway timeout",
        "description": "Payment requests exceeded timeout.",
    }

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "event_id": str(event_id),
        "status": "received",
    }


def test_receive_invalid_incident_event():
    event_id = uuid4()
    incident_id = uuid4()
    payload = {
        "event_id": str(event_id),
        "incident_id": str(incident_id),
        "severity": "WARNING",  # Invalid severity
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source": "checkout-service",
        "schema_version": "2.0",
        "title": "Payment gateway timeout",
        "description": "Payment requests exceeded timeout.",
    }

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 422  # Unprocessable Entity