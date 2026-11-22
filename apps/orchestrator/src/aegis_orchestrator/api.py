import uuid
import httpx

from fastapi import FastAPI

from aegis_orchestrator.workflow import investigate_incident
from aegis_orchestrator import InvestigationResult

app = FastAPI()

INVESTIGATOR_BASE_URL = "http://localhost:8000"


@app.get("/health")
def get_health():
    return {"status": "healthy"}


@app.post(
    "/v1/incidents/{incident_id}/investigate",
    response_model=InvestigationResult,
)
def investigating_incident(incident_id: uuid.UUID):
    with httpx.Client(timeout=5.0) as client:
        return investigate_incident(
            incident_id=incident_id,
            base_url=INVESTIGATOR_BASE_URL,
            client=client,
        )
