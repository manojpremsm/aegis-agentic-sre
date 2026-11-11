# Aegis Contracts

`aegis-contracts` defines shared, versioned data contracts used by Aegis services. It is independent of the simulator and investigator implementations, allowing those applications to be developed and deployed separately.

## IncidentEvent (schema version 1.0)

`IncidentEvent` represents an incident notification that can initiate or inform an investigation. The model is defined in `aegis_contracts.events` and exposed through the `aegis_contracts` package.

| Field | Type | Required | Meaning and validation |
| --- | --- | --- | --- |
| `event_id` | `UUID` | Yes | Identifier for this individual event. |
| `incident_id` | `UUID` | Yes | Identifier shared by events associated with the same incident. |
| `severity` | `IncidentSeverity` | Yes | One of `INFO`, `WARNING`, or `CRITICAL` (case-sensitive). |
| `occurred_at` | `AwareDatetime` | Yes | Time the producer observed the event; timezone information is required. |
| `source` | `str` | Yes | Originating service or monitoring source; surrounding whitespace is trimmed and an empty result is rejected. |
| `schema_version` | `Literal["1.0"]` | Yes | Explicit event contract version; only `"1.0"` is accepted by this model. |
| `title` | `str` | Yes | Short incident summary; surrounding whitespace is trimmed and an empty result is rejected. |
| `description` | `str \| None` | No | Optional additional detail; defaults to `None`. When provided as a string, it is trimmed and must not be empty. |

## Identity and delivery semantics

- `event_id` identifies an event, while `incident_id` groups related events into an incident. Different events may share an `incident_id` but should have different `event_id` values.
- Retrying delivery of the **same event** should preserve its `event_id`.
- UUID field validation checks that identifiers have a valid UUID representation. It does **not** enforce global uniqueness, prevent duplicate deliveries, or implement idempotency. Producers are responsible for assigning identifiers; the investigator will need its own deduplication strategy.

## Timestamp semantics

`occurred_at` is the producer-side observation time, **not** the time the investigator receives the message. It must be timezone-aware; UTC is recommended for consistency but is not required by the model. Events may be delivered out of order, so arrival order should not be treated as occurrence order. Consumer-side receipt timestamps, if needed, belong to ingestion metadata rather than this event contract.

## Version compatibility

Every event must explicitly provide `schema_version="1.0"`. Missing versions and unsupported values such as `"2.0"` fail validation. The version identifies the expected payload shape; it does not automatically migrate events between versions.

## Usage and JSON round trip

```python
from datetime import datetime, timezone
from uuid import uuid4

from aegis_contracts import IncidentEvent, IncidentSeverity

event = IncidentEvent(
    event_id=uuid4(),
    incident_id=uuid4(),
    severity=IncidentSeverity.WARNING,
    occurred_at=datetime.now(timezone.utc),
    source="checkout-service",
    schema_version="1.0",
    title="Checkout error rate elevated",
    description="5xx responses exceeded the configured threshold.",
)

message = event.model_dump_json()  # JSON string for transport
restored = IncidentEvent.model_validate_json(message)
assert restored == event
```

`model_dump_json()` includes `"description": null` when the description is absent, unless serialization is configured to exclude `None` values (for example, `exclude_none=True`).

## Validation and tests

The model validates event structure and individual field constraints; it does not provide message transport, persistence, deduplication, or investigation logic.

From the repository root, run:

```powershell
python -m pytest packages/contracts/tests -v
```
