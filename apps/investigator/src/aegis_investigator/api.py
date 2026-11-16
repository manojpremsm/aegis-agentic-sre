from fastapi import FastAPI
from aegis_contracts import IncidentEvent
import uuid
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/v1/events")
async def receive_event(event_data: IncidentEvent):

    return {"event_id":event_data.event_id,"status":"received"}