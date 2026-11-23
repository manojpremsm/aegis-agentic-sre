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

import uuid

from fastapi.testclient import TestClient

from aegis_orchestrator import api
from aegis_orchestrator.model.investigation_result import (
    InvestigationResult,
    InvestigationStatus,
)
from aegis_orchestrator.model.severity_assessment import (
    RiskLevel,
    SeverityAssessment,
)
from aegis_contracts import IncidentSummary


def test_investigate_endpoint_returns_severity_assessment(monkeypatch):
    incident_id = uuid.uuid4()

    summary = IncidentSummary(
        incident_id=incident_id,
        total_events=2,
        severity_counts={
            "INFO": 0,
            "WARNING": 1,
            "CRITICAL": 1,
        },
        sources=["payment-service"],
    )

    assessment = SeverityAssessment(
        incident_id=incident_id,
        risk_level=RiskLevel.HIGH,
        reason="Critical events detected in incident evidence",
        requires_immediate_attention=True,
    )

    def fake_investigate_incident(incident_id, base_url, client):
        return InvestigationResult(
            incident_id=incident_id,
            status=InvestigationStatus.COMPLETED,
            summary=summary,
            severity_assessment=assessment,
            error=None,
        )

    monkeypatch.setattr(
        api,
        "investigate_incident",
        fake_investigate_incident,
    )

    client = TestClient(api.app)

    response = client.post(
        f"/v1/incidents/{incident_id}/investigate"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "COMPLETED"
    assert data["summary"]["total_events"] == 2

    assert data["severity_assessment"]["incident_id"] == str(incident_id)
    assert data["severity_assessment"]["risk_level"] == "HIGH"
    assert data["severity_assessment"]["requires_immediate_attention"] is True
    assert data["severity_assessment"]["reason"]
    assert data["error"] is None

def test_investigate_endpoint_returns_null_assessment_on_failure(monkeypatch):
    incident_id = uuid.uuid4()

    def fake_investigate_incident(incident_id, base_url, client):
        return InvestigationResult(
            incident_id=incident_id,
            status=InvestigationStatus.FAILED,
            summary=None,
            severity_assessment=None,
            error="Investigator service unavailable",
        )

    monkeypatch.setattr(
        api,
        "investigate_incident",
        fake_investigate_incident,
    )

    client = TestClient(api.app)

    response = client.post(
        f"/v1/incidents/{incident_id}/investigate"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "FAILED"
    assert data["summary"] is None
    assert data["severity_assessment"] is None
    assert data["error"] == "Investigator service unavailable"