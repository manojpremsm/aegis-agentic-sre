import pytest
from aegis_investigator import initialize_database, insert_event, get_events_by_incident_id
import sqlite3
from aegis_contracts import IncidentEvent, IncidentSeverity
from aegis_simulator import create_incident_event
import uuid
from fastapi.testclient import TestClient
import aegis_investigator.api as api
from aegis_investigator.api import app


client = TestClient(app)



def test_initialize_database_creates_incident_events_table(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(str(db_path))
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incident_events';")
        table_exists = cursor.fetchone()
        assert table_exists is not None, "incident_events table should be created"
    finally:
        conn.close()

def test_initialize_database_can_be_called_twice(tmp_path):
    db_path = tmp_path / "test.db"
    
    
    initialize_database(str(db_path))
    initialize_database(str(db_path))

def test_initialize_database_invalid_path(tmp_path):
    db_path = tmp_path / "missing_directory" / "test.db"

    with pytest.raises(sqlite3.OperationalError):
        initialize_database(str(db_path))  # Call it again to ensure no errors

def test_insert_event_persists_event(tmp_path):
    db_path  =  tmp_path / "test.db"
    initialize_database(str(db_path))
    event = create_incident_event(incident_id=uuid.uuid4(), severity=IncidentSeverity.CRITICAL, source="test_source", title="Test Incident", description="This is a test incident.")
    assert insert_event(str(db_path), event) is True
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
        assert row[1] == str(event.incident_id)
        assert row[2] == event.severity.value
        assert row[3] == event.occurred_at.isoformat()
        assert row[4] == event.source
        assert row[5] == event.schema_version
        assert row[6] == event.title
        assert row[7] == event.description
    finally:
        conn.close()

def test_insert_duplicate_event_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(str(db_path))
    event = create_incident_event(incident_id=uuid.uuid4(), severity=IncidentSeverity.CRITICAL, source="test_source", title="Test Incident", description="This is a test incident.")
    assert insert_event(str(db_path), event) is True
    assert insert_event(str(db_path), event) is False
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM incident_events WHERE event_id = ?
            """,
            (str(event.event_id),),
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Duplicate event should not be inserted"
    finally:
        conn.close()

def test_insert_event_rejects_conflicting_duplicate(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(str(db_path))
    event1 = create_incident_event(incident_id=uuid.uuid4(), severity=IncidentSeverity.CRITICAL, source="test_source", title="Test Incident", description="This is a test incident.")
    event2 = IncidentEvent(
        event_id=event1.event_id,
        incident_id=uuid.uuid4(),
        severity=IncidentSeverity.WARNING,
        occurred_at=event1.occurred_at,
        source="different_source",
        schema_version="1.0",
        title="Different Title",
        description="Different description."
    )
    assert insert_event(str(db_path), event1) is True
    with pytest.raises(ValueError, match="already exists with different data"):
        insert_event(str(db_path), event2)

def test_get_events_by_incident_id_returns_matching_events(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(str(db_path))
    incident_id = uuid.uuid4()
    event1 = create_incident_event(incident_id=incident_id, severity=IncidentSeverity.CRITICAL, source="test_source", title="Test Incident 1", description="This is the first test incident.")
    event2 = create_incident_event(incident_id=incident_id, severity=IncidentSeverity.WARNING, source="test_source", title="Test Incident 2", description="This is the second test incident.")
    event3 = create_incident_event(incident_id=uuid.uuid4(), severity=IncidentSeverity.INFO, source="test_source", title="Test Incident 3", description="This is a different incident.")
    insert_event(str(db_path), event1)
    insert_event(str(db_path), event2)
    insert_event(str(db_path), event3)

    events = get_events_by_incident_id(str(db_path), incident_id)
    assert len(events) == 2
    assert {event.event_id for event in events} == {
    event1.event_id,
    event2.event_id,
}

    assert all(event.incident_id == incident_id for event in events)

def test_get_events_by_incident_id_returns_empty_list(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(str(db_path))

    unknown_incident_id = uuid.uuid4()

    events = get_events_by_incident_id(
        str(db_path),
        unknown_incident_id,
    )

    assert events == []
    
