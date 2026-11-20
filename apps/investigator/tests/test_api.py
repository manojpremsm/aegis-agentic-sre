
from aegis_contracts import IncidentSeverity
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4
from aegis_investigator.api import app
import aegis_investigator.api as api
import sqlite3
from aegis_simulator import create_incident_event
from aegis_investigator import get_events_by_incident_id
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

def test_app_startup_initializes_database(tmp_path, monkeypatch):
    db_path = tmp_path / "startup_test.db"
    monkeypatch.setattr(api, "db_path", str(db_path))
    with TestClient(app) as client:
        # Trigger the startup event
        response = client.get("/health")
        assert response.status_code == 200
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='incident_events';"
        )
        table_exists = cursor.fetchone()
        assert table_exists is not None, "incident_events table should be created on startup"
    finally:
        conn.close()

def test_receive_event_persists_to_database(tmp_path, monkeypatch):
    db_path = tmp_path / "events.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.CRITICAL,
        source="test_source",
        title="Database persistence test",
    )

    with TestClient(api.app) as client:
        response = client.post(
            "/v1/events",
            json=event.model_dump(mode="json"),
        )

        assert response.status_code == 200

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT event_id, incident_id, severity, occurred_at,
                   source, schema_version, title, description
            FROM incident_events
            WHERE event_id = ?
            """,
            (str(event.event_id),),
        )
        row = cursor.fetchone()
        assert row is not None, "Inserted event should be found in the database"
        assert row[0] == str(event.event_id)
    finally:
        conn.close()

def test_receive_duplicate_event_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "duplicate_events.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.CRITICAL,
        source="test_source",
        title="Duplicate delivery test",
    )

    with TestClient(api.app) as client:
        response1 = client.post("/v1/events", json=event.model_dump(mode="json"))
        response2 = client.post("/v1/events", json=event.model_dump(mode="json"))
        assert response1.status_code == 200
        assert response2.status_code == 200

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT count(*) FROM incident_events WHERE event_id = ?
            """,
            (str(event.event_id),)
        )
        row = cursor.fetchone()
        assert row is not None, "Inserted event should be found in the database"
        assert row[0] == 1
    finally:
        conn.close()

def test_receive_conflicting_event_returns_409(tmp_path, monkeypatch):
    db_path = tmp_path / "conflicting_events.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    # Create the original event
    event1 = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.CRITICAL,
        source="test_source",
        title="Original Incident",
    )

    # Create a conflicting event with the same event_id
    # but a different title
    event2 = event1.model_copy(
        update={"title": "Conflicting Incident"}
    )

    with TestClient(api.app) as client:
        # First event should be accepted
        response1 = client.post(
            "/v1/events",
            json=event1.model_dump(mode="json"),
        )
        assert response1.status_code == 200

        # Conflicting event should be rejected
        response2 = client.post(
            "/v1/events",
            json=event2.model_dump(mode="json"),
        )
        assert response2.status_code == 409

    # Verify that the original event remains unchanged
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT title
            FROM incident_events
            WHERE event_id = ?
            """,
            (str(event1.event_id),),
        )

        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "Original Incident"

        # Ensure only one event exists with this ID
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM incident_events
            WHERE event_id = ?
            """,
            (str(event1.event_id),),
        )

        assert cursor.fetchone()[0] == 1

    finally:
        conn.close()

def test_receive_event_returns_503_when_database_fails(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "events.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.CRITICAL,
        source="test_source",
        title="Database failure test",
    )

    def failing_insert(db_path, event_data):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(api, "insert_event", failing_insert)

    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/events",
            json=event.model_dump(mode="json"),
        )

    assert response.status_code == 503

def test_event_survives_application_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "restart_test.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.CRITICAL,
        source="test_source",
        title="Persistence across restart",
        description="Verify that the event survives application restart.",
    )

    # First startup: receive and persist the event
    with TestClient(api.app) as client:
        response = client.post(
            "/v1/events",
            json=event.model_dump(mode="json"),
        )

        assert response.status_code == 200
        assert response.json()["event_id"] == str(event.event_id)

    # The first TestClient context has exited.
    # Start the application again using the same database.
    with TestClient(api.app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        # Retrieve the event after the simulated restart
        stored_events = get_events_by_incident_id(
            str(db_path),
            event.incident_id,
        )

        assert len(stored_events) == 1
        assert stored_events[0].event_id == event.event_id
        assert stored_events[0].incident_id == event.incident_id
        assert stored_events[0].severity == event.severity
        assert stored_events[0].title == event.title
        assert stored_events[0].description == event.description

def test_get_incident_events_returns_matching_events(
    tmp_path,
    monkeypatch,
):
    incident_id =uuid4()
    db_path = tmp_path/"test_db.db"
    monkeypatch.setattr(api,"db_path",str(db_path))
    event1 = create_incident_event(incident_id=incident_id,severity=IncidentSeverity.WARNING,source="test_source",title="getting matching events",description="check whether get route is working")
    event2 = create_incident_event(incident_id=incident_id,severity=IncidentSeverity.WARNING,source="test_source",title="getting  events",description="check whether it is working")
    event3 = create_incident_event(incident_id=uuid4(),severity=IncidentSeverity.WARNING,source="test_source",title="getting  events",description="check whether it is working")
    with TestClient(api.app) as client:
        response1 = client.post("/v1/events/",json=event1.model_dump(mode="json"))
        response2 = client.post("/v1/events/",json=event2.model_dump(mode="json"))
        response3 = client.post("/v1/events/",json=event3.model_dump(mode="json"))
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        response = client.get(f"/v1/incidents/{incident_id}/events")
        assert response.status_code == 200
        returned_events = response.json()
        assert len(returned_events) == 2
        returned_event_ids = {
        event["event_id"] for event in returned_events
        }
        expected_event_ids = {
        str(event1.event_id),
        str(event2.event_id),
        }
        assert returned_event_ids == expected_event_ids

def test_get_incident_events_returns_empty_list(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path /"test.db"
    monkeypatch.setattr(api,"db_path",str(db_path))
    incident_id = uuid4()
    with TestClient(api.app) as client:

        response = client.get(f"/v1/incidents/{incident_id}/events")
        assert response.status_code == 200
        assert response.json() == []

def test_get_incident_events_rejects_invalid_uuid(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path /"test.db"
    monkeypatch.setattr(api,"db_path",str(db_path))
    incident_id = 12367
    with TestClient(api.app) as client:

        response = client.get(f"/v1/incidents/{incident_id}/events")
        assert response.status_code == 422

def test_get_incident_events_returns_503_when_database_fails(
    tmp_path,
    monkeypatch,
):
    # Arrange
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(api, "db_path", str(db_path))

    incident_id = uuid4()

    # Simulate a SQLite database failure
    def failing_get_events(db_path, incident_id):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(
        api,
        "get_events_by_incident_id",
        failing_get_events,
    )

    # Act
    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/v1/incidents/{incident_id}/events"
        )

    # Assert
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Event storage temporarily unavailable"
    )

def test_get_incident_summary_returns_aggregated_evidence(
    tmp_path,
    monkeypatch,
):
    # Arrange: isolate this test from the real database
    test_db_path = tmp_path / "test_summary.db"
    monkeypatch.setattr(api, "db_path", str(test_db_path))

    incident_id = uuid4()

    event1 = create_incident_event(
        incident_id=incident_id,
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="High checkout latency",
    )

    event2 = create_incident_event(
        incident_id=incident_id,
        severity=IncidentSeverity.CRITICAL,
        source="payment-service",
        title="Payment failures",
    )

    event3 = create_incident_event(
        incident_id=incident_id,
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Checkout latency increasing",
    )

    events = [event1, event2, event3]

    with TestClient(api.app) as client:

        # Act: persist the events through the ingestion API
        for event in events:
            response = client.post(
                "/v1/events",
                json=event.model_dump(mode="json"),
            )
            assert response.status_code == 200

        # Act: retrieve the aggregated incident summary
        response = client.get(
            f"/v1/incidents/{incident_id}/summary"
        )

    # Assert: verify the summary response
    assert response.status_code == 200

    summary = response.json()

    assert summary["incident_id"] == str(incident_id)
    assert summary["total_events"] == 3

    assert summary["severity_counts"] == {
        "INFO": 0,
        "WARNING": 2,
        "CRITICAL": 1,
    }

    assert summary["sources"] == [
        "checkout-service",
        "payment-service",
    ]

def test_get_incident_summary_returns_empty_summary(
    tmp_path,
    monkeypatch,
):
    incident_id = uuid4()
    events = []
    db_path = tmp_path/"test.db"
    monkeypatch.setattr(api,"db_path",db_path)
    with TestClient(api.app) as client:
        for event in events:
            response = client.post(
                            "/v1/events",
                            json=event.model_dump(mode="json"),
                        )
            assert response.status_code == 200
            # Act: retrieve the aggregated incident summary
            response = client.get(
                f"/v1/incidents/{incident_id}/summary"
            )
            summary = response.json()
            assert response.status_code == 200
            assert summary["total_events"] == 0
            assert summary["severity_counts"] == {
                "INFO": 0,
                "WARNING": 0,
                "CRITICAL": 0,
            }
            assert summary["sources"] == []

def test_get_incident_summary_rejects_invalid_uuid(
    tmp_path,
    monkeypatch,
):
    test_db_path = tmp_path / "test_summary.db"
    monkeypatch.setattr(api, "db_path", str(test_db_path))

    with TestClient(api.app) as client:
        response = client.get(
            "/v1/incidents/not-a-valid-uuid/summary"
        )

    assert response.status_code == 422

def test_get_incident_summary_returns_503_when_database_fails(
    tmp_path,
    monkeypatch,
):
    test_db_path = tmp_path / "test_summary.db"
    monkeypatch.setattr(api, "db_path", str(test_db_path))

    incident_id = uuid4()

    def failing_get_events(db_path, incident_id):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(
        api,
        "get_events_by_incident_id",
        failing_get_events,
    )

    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/v1/incidents/{incident_id}/summary"
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Event storage temporarily unavailable"
    }