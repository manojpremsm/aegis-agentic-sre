import uuid

import pytest
from pydantic import ValidationError

from aegis_orchestrator.model.severity_assessment import (
    RiskLevel,
    SeverityAssessment,
)


def test_severity_contract():
    incident_id = uuid.uuid4()

    assessment = SeverityAssessment(
        incident_id=incident_id,
        risk_level="HIGH",
        reason="checkout not working",
        requires_immediate_attention=True,
    )

    assert assessment.incident_id == incident_id
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.reason == "checkout not working"
    assert assessment.requires_immediate_attention is True


def test_severity_reason_non_empty():
    with pytest.raises(ValidationError):
        SeverityAssessment(
            incident_id=uuid.uuid4(),
            risk_level="HIGH",
            reason="   ",
            requires_immediate_attention=True,
        )

import uuid

from aegis_contracts import IncidentSummary
from aegis_orchestrator.model.severity_assessment import RiskLevel
from aegis_orchestrator.agents.severity_agent import analyze_severity



import uuid

import pytest

from aegis_contracts import IncidentSummary
from aegis_orchestrator.agents.severity_agent import analyze_severity
from aegis_orchestrator.model.severity_assessment import RiskLevel


@pytest.mark.parametrize(
    "severity_counts, expected_risk, expected_attention",
    [
        pytest.param(
            {"INFO": 0, "WARNING": 0, "CRITICAL": 1},
            RiskLevel.HIGH,
            True,
            id="critical-incident",
        ),
        pytest.param(
            {"INFO": 0, "WARNING": 2, "CRITICAL": 0},
            RiskLevel.MEDIUM,
            False,
            id="warning-incident",
        ),
        pytest.param(
            {"INFO": 3, "WARNING": 0, "CRITICAL": 0},
            RiskLevel.LOW,
            False,
            id="informational-incident",
        ),
        pytest.param(
            {"INFO": 0, "WARNING": 0, "CRITICAL": 0},
            RiskLevel.UNKNOWN,
            False,
            id="empty-incident",
        ),
        pytest.param(
            {"INFO": 100, "WARNING": 50, "CRITICAL": 1},
            RiskLevel.HIGH,
            True,
            id="mixed-severity-critical-precedence",
        ),
    ],
)
def test_analyze_severity(
    severity_counts,
    expected_risk,
    expected_attention,
):
    incident_id = uuid.uuid4()

    summary = IncidentSummary(
        incident_id=incident_id,
        total_events=sum(severity_counts.values()),
        severity_counts=severity_counts,
        sources=["checkout-service"],
    )

    assessment = analyze_severity(summary)

    assert assessment.incident_id == incident_id
    assert assessment.risk_level == expected_risk
    assert assessment.requires_immediate_attention is expected_attention
    assert assessment.reason.strip()
