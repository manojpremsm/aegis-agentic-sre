import httpx
import uuid
import pytest
from aegis_orchestrator import fetch_incident_summary

def test_http_client_sends_get_request():
    def mock_handler(request: httpx.Request):
        assert request.method == "GET"
        assert str(request.url) == "http://localhost:8000/health"

        return httpx.Response(
            status_code=200,
            json={"status": "healthy"},
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        response = client.get("http://localhost:8000/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_fetch_incident_summary_returns_valid_summary():
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
        summary = fetch_incident_summary(
            incident_id=incident_id,
            base_url="http://localhost:8000",
            client=client,
        )

        assert summary.incident_id == incident_id
        assert summary.total_events == 3
        assert summary.severity_counts == {
            "INFO": 0,
            "WARNING": 2,
            "CRITICAL": 1,
        }
        assert summary.sources == [
            "checkout-service",
            "payment-service",
        ]


def test_fetch_incident_summary_raises_on_http_503():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request):
        return httpx.Response(
            status_code=503,
            json={"detail": "Event storage temporarily unavailable"},
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetch_incident_summary(
                incident_id=incident_id,
                base_url="http://localhost:8000",
                client=client,
            )

    assert exc_info.value.response.status_code == 503


def test_fetch_incident_summary_raises_on_timeout():
    incident_id = uuid.uuid4()

    def mock_handler(request: httpx.Request):
        raise httpx.ReadTimeout(
            "Investigator did not respond in time",
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(httpx.ReadTimeout):
            fetch_incident_summary(
                incident_id=incident_id,
                base_url="http://localhost:8000",
                client=client,
            )
