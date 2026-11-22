from fastapi.testclient import TestClient
import aegis_orchestrator.api as api
from aegis_orchestrator import InvestigationResult, InvestigationStatus
from aegis_contracts import IncidentSummary

import uuid


def test_health_endpoint():

    with TestClient(api.app) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_investigating_incident_valid_result(monkeypatch):
    incident_id = uuid.uuid4()

    result_data = InvestigationResult(
        incident_id=incident_id,
        status=InvestigationStatus.COMPLETED,
        summary=IncidentSummary(
            incident_id=incident_id,
            total_events=3,
            severity_counts={
                "WARNING": 2,
                "INFO": 1,
                "CRITICAL": 0,
            },
            sources=["checkout-service", "payment-service"],
        ),
        error=None,
    )

    def fake_investigate_incident(incident_id, base_url, client):
        return result_data

    monkeypatch.setattr(
        api,
        "investigate_incident",
        fake_investigate_incident,
    )

    with TestClient(api.app) as client:
        response = client.post(f"/v1/incidents/{incident_id}/investigate")

    assert response.status_code == 200

    data = response.json()
    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "COMPLETED"
    assert data["summary"]["total_events"] == 3
    assert data["error"] is None


def test_investigating_incident_failed_result(monkeypatch):
    incident_id = uuid.uuid4()
    result_data = InvestigationResult(
        incident_id=incident_id,
        status=InvestigationStatus.FAILED,
        summary=None,
        error="Investigator service unavailable",
    )

    def fake_investigate_incident(incident_id, base_url, client):
        return result_data

    monkeypatch.setattr(
        api,
        "investigate_incident",
        fake_investigate_incident,
    )

    with TestClient(api.app) as client:
        response = client.post(f"/v1/incidents/{incident_id}/investigate")

    assert response.status_code == 200

    data = response.json()
    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "FAILED"
    assert data["summary"] is None
    assert data["error"] == "Investigator service unavailable"
