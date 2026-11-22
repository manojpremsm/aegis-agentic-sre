from aegis_orchestrator import (
    InvestigationResult,
    InvestigationStatus,
    investigate_incident,
)
import pytest
import uuid
import httpx


def test_investigate_incident_returns_completed_result():
    incident_id = uuid.uuid4()
    summary_data = {
        "incident_id": str(incident_id),
        "total_events": 3,
        "severity_counts": {
            "INFO": 0,
            "WARNING": 2,
            "CRITICAL": 1,
        },
        "sources": [
            "checkout-service",
            "payment-service",
        ],
    }

    def mock_handler(request: httpx.Request):
        assert request.method == "GET"
        assert str(request.url) == (
            f"http://localhost:8000/v1/incidents/{incident_id}/summary"
        )

        return httpx.Response(200, json=summary_data)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://localhost:8000",
            client=client,
        )
        assert result.status == InvestigationStatus.COMPLETED
        assert isinstance(result, InvestigationResult)
        assert result.incident_id == incident_id
        assert result.summary is not None
        assert result.summary.total_events == 3
        assert result.error is None


def test_investigate_incident_returns_failed_on_http_503():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request):
        return httpx.Response(
            status_code=503,
            json={"detail": "Service unavailable"},
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://localhost:8000",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.error == "Investigator service unavailable"


def test_investigate_incident_returns_failed_on_timeout():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request):
        raise httpx.ReadTimeout(
            "Investigator timed out",
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://localhost:8000",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.error == "Investigator service unavailable"
