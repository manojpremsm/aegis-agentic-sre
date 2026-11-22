import uuid
import httpx
from aegis_contracts import IncidentSummary


def fetch_incident_summary(
    incident_id: uuid.UUID, base_url: str, client: httpx.Client
) -> IncidentSummary:

    response = client.get(f"{base_url}/v1/incidents/{incident_id}/summary")
    response.raise_for_status()
    return IncidentSummary.model_validate(response.json())
