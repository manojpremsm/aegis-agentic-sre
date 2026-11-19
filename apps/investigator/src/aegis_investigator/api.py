import os
import sqlite3
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from aegis_contracts import IncidentEvent
from aegis_investigator import (
    initialize_database,
    insert_event,
    get_events_by_incident_id,
)


db_path = os.getenv("AEGIS_DB_PATH", "aegis_events.db")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    initialize_database(db_path)
    yield
    # Shutdown logic

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/v1/events")
def receive_event(event_data: IncidentEvent):
    try:
        insert_event(db_path, event_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Event storage temporarily unavailable",
        ) from exc

    return {
        "event_id": event_data.event_id,
        "status": "received",
    }

@app.get("/v1/incidents/{incident_id}/events",response_model=list[IncidentEvent],)
def get_incident_events(incident_id: uuid.UUID):
    try:
        return get_events_by_incident_id(db_path,incident_id)
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Event storage temporarily unavailable",
        ) from exc