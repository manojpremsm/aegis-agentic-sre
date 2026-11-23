import httpx
import uuid
import pytest
from aegis_orchestrator import fetch_incident_summary,fetch_incident_events
from aegis_simulator import create_incident_event
from aegis_contracts import IncidentEvent
from pydantic import ValidationError

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

def test_fetch_incident_events_returns_validated_events():
    incident_id = uuid.uuid4()


    event1 = create_incident_event(incident_id,"CRITICAL","checkout-service","Payment gateway timeout","A timeout occurred while processing the payment through the gateway.")
    event2 = create_incident_event(incident_id,"CRITICAL","checkout-service","Payment  timeout","A timeout occurred while processing the payment through the gateway.")
    payload = [event1,event2]


    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Verify GET method and URL.
        assert request.method == "GET"
        assert request.url == f"http://investigator/v1/incidents/{incident_id}/events"

        return httpx.Response(status_code = 200, json=[
            event.model_dump(mode="json")
            for event in payload
        ],)

        ...

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(transport=transport) as client:
        events = fetch_incident_events(
            incident_id=incident_id,
            base_url="http://investigator",
            client=client,
        )

    assert len(events) == 2
    assert all(isinstance(event, IncidentEvent) for event in events)

def test_fetch_incident_events_returns_empty_list():
    incident_id = uuid.uuid4()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=[])
    )

    with httpx.Client(transport=transport) as client:
        events = fetch_incident_events(
            incident_id,
            "http://investigator",
            client,
        )

    assert events == []

def test_fetch_incident_events_raises_on_http_503():
    incident_id = uuid.uuid4()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(503)
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_incident_events(
                incident_id,
                "http://investigator",
                client,
            )

def test_fetch_incident_events_rejects_invalid_event():
    incident_id = uuid.uuid4()

    invalid_event = {
        "event_id": str(uuid.uuid4()),
        "incident_id": str(incident_id),
        "severity": "INVALID_SEVERITY",
        "occurred_at": "2026-11-23T10:00:00Z",
        "source": "payment-service",
        "schema_version": "1.0",
        "title": "Database connection failure",
    }

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=[invalid_event],
        )
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ValidationError):
            fetch_incident_events(
                incident_id,
                "http://investigator",
                client,
            )