
import uuid

import httpx
import pytest

from aegis_contracts import IncidentSeverity
from aegis_simulator import create_incident_event
from aegis_orchestrator import (
    InvestigationResult,
    InvestigationStatus,
    RiskLevel,
    investigate_incident,
)


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

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        if request.url.path == f"/v1/incidents/{incident_id}/summary":
            return httpx.Response(200, json=summary_data)

        if request.url.path == f"/v1/incidents/{incident_id}/events":
            return httpx.Response(200, json=[])

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert isinstance(result, InvestigationResult)
    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.COMPLETED
    assert result.summary is not None
    assert result.summary.total_events == 3
    assert result.events == []
    assert result.error is None


def test_investigate_incident_returns_failed_on_http_503():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            json={"detail": "Service unavailable"},
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.events is None
    assert result.severity_assessment is None
    assert result.error == "Investigator service unavailable"


def test_investigate_incident_returns_failed_on_timeout():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Investigator timed out",
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.events is None
    assert result.severity_assessment is None
    assert result.error == "Investigator service unavailable"


def test_investigation_includes_severity_assessment():
    incident_id = uuid.uuid4()

    summary_data = {
        "incident_id": str(incident_id),
        "total_events": 3,
        "severity_counts": {
            "INFO": 1,
            "WARNING": 1,
            "CRITICAL": 1,
        },
        "sources": [
            "checkout-service",
            "payment-service",
        ],
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        if request.url.path == f"/v1/incidents/{incident_id}/summary":
            return httpx.Response(200, json=summary_data)

        if request.url.path == f"/v1/incidents/{incident_id}/events":
            return httpx.Response(200, json=[])

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.COMPLETED

    assert result.summary is not None
    assert result.summary.total_events == 3

    assert result.events == []

    assert result.severity_assessment is not None
    assert result.severity_assessment.risk_level == RiskLevel.HIGH
    assert result.severity_assessment.requires_immediate_attention is True
    assert result.severity_assessment.incident_id == incident_id
    assert result.severity_assessment.reason.strip()

    assert result.error is None


def test_investigation_failure_has_no_severity_assessment():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"detail": "Service unavailable"},
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.events is None
    assert result.severity_assessment is None
    assert result.error == "Investigator service unavailable"


def test_investigation_returns_summary_and_events():
    incident_id = uuid.uuid4()

    summary_data = {
        "incident_id": str(incident_id),
        "total_events": 1,
        "severity_counts": {
            "INFO": 0,
            "WARNING": 0,
            "CRITICAL": 1,
        },
        "sources": ["checkout-service"],
    }

    event = create_incident_event(
        incident_id=incident_id,
        severity=IncidentSeverity.CRITICAL,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        if request.url.path == f"/v1/incidents/{incident_id}/summary":
            return httpx.Response(200, json=summary_data)

        if request.url.path == f"/v1/incidents/{incident_id}/events":
            return httpx.Response(
                200,
                json=[event.model_dump(mode="json")],
            )

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.COMPLETED

    assert result.summary is not None
    assert result.summary.total_events == 1

    assert result.events is not None
    assert len(result.events) == 1
    assert result.events[0].event_id == event.event_id
    assert result.events[0].incident_id == incident_id
    assert result.events[0].severity == IncidentSeverity.CRITICAL
    assert result.events[0].source == "checkout-service"
    assert result.events[0].title == "Payment gateway timeout"

    assert result.severity_assessment is not None
    assert result.severity_assessment.risk_level == RiskLevel.HIGH
    assert result.severity_assessment.requires_immediate_attention is True

    assert result.error is None


def test_investigation_fails_when_event_retrieval_fails():
    incident_id = uuid.uuid4()

    summary_data = {
        "incident_id": str(incident_id),
        "total_events": 1,
        "severity_counts": {
            "INFO": 0,
            "WARNING": 0,
            "CRITICAL": 1,
        },
        "sources": ["payment-service"],
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        if request.url.path == f"/v1/incidents/{incident_id}/summary":
            return httpx.Response(200, json=summary_data)

        if request.url.path == f"/v1/incidents/{incident_id}/events":
            return httpx.Response(
                503,
                json={"detail": "Service unavailable"},
            )

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        result = investigate_incident(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert result.incident_id == incident_id
    assert result.status == InvestigationStatus.FAILED
    assert result.summary is None
    assert result.events is None
    assert result.severity_assessment is None
    assert result.error == "Investigator service unavailable"
