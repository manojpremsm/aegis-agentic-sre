from dataclasses import dataclass
from aegis_contracts import IncidentSeverity

@dataclass(frozen=True)
class IncidentScenario:
    severity: IncidentSeverity
    source: str
    title: str
    description: str | None = None

PaymentGatewayTimeoutScenario = IncidentScenario(
    severity=IncidentSeverity.WARNING,
    source="checkout-service",
    title="Payment gateway timeout",
    description="Payment requests exceeded the configured gateway timeout.",
)