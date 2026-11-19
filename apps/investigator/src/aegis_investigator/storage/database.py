import sqlite3
from aegis_contracts import IncidentEvent
import uuid

def initialize_database(db_path: str) -> None:
    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_events (
                event_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                source TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

def insert_event(db_path: str, event_data: IncidentEvent) -> bool:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO incident_events (event_id, incident_id, severity, occurred_at, source, schema_version, title, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event_data.event_id),
                    str(event_data.incident_id),
                    event_data.severity.value,
                    event_data.occurred_at.isoformat(),
                    event_data.source,
                    event_data.schema_version,
                    event_data.title,
                    event_data.description,
                ),
            )
            connection.commit()
            return True
        except sqlite3.IntegrityError as exc:
            if getattr(exc, "sqlite_errorname", None) != "SQLITE_CONSTRAINT_PRIMARYKEY":
                raise

            cursor.execute(
                """
                SELECT incident_id, severity, occurred_at,
                       source, schema_version, title, description
                FROM incident_events
                WHERE event_id = ?
                """,
                (str(event_data.event_id),),
            )
            existing_row = cursor.fetchone()
            incoming_row = (
                str(event_data.incident_id),
                event_data.severity.value,
                event_data.occurred_at.isoformat(),
                event_data.source,
                event_data.schema_version,
                event_data.title,
                event_data.description,
            )
            if existing_row == incoming_row:
                return False
            else:
                raise ValueError(
                    f"Event with event_id {event_data.event_id} already exists with different data."
                )
                
           
    finally:
        connection.close()

def get_events_by_incident_id(db_path: str,
    incident_id: uuid.UUID,
) -> list[IncidentEvent]:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT event_id, incident_id, severity, occurred_at,
                source, schema_version, title, description
            FROM incident_events
            WHERE incident_id = ?
            ORDER BY occurred_at, event_id
            """,
            (str(incident_id),),
        )
        rows = cursor.fetchall()
        events = []
        for row in rows:
            event = IncidentEvent(
                event_id=uuid.UUID(row[0]),
                incident_id=uuid.UUID(row[1]),
                severity=row[2],
                occurred_at=row[3],
                source=row[4],
                schema_version=row[5],
                title=row[6],
                description=row[7],
            )
            events.append(event)
        return events
    finally:
        connection.close()