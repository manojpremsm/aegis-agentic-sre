
from unittest.mock import Mock, patch
from uuid import uuid4
import pytest
import httpx
from aegis_contracts import IncidentSeverity
from aegis_simulator import create_incident_event
from aegis_simulator import send_incident_event


def test_retry_after_503_then_success():
    # ARRANGE: Create a valid incident event.
    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    endpoint = "http://127.0.0.1:8000/v1/events"

    # Create two fake HTTP responses.
    response_503 = Mock()
    response_503.status_code = 503

    response_200 = Mock()
    response_200.status_code = 200

    # Replace real HTTP requests and sleeping with mocks.
    with (
        patch("aegis_simulator.delivery.httpx.post") as mock_post,
        patch("aegis_simulator.delivery.time.sleep") as mock_sleep,
    ):
        # First request returns 503; second returns 200.
        mock_post.side_effect = [response_503, response_200]

        # ACT: Execute the real delivery function.
        result = send_incident_event(
            event=event,
            endpoint=endpoint,
            max_attempts=3,
        )

        # ASSERT: The second response was returned.
        assert result is response_200

        # The function sent exactly two HTTP requests.
        assert mock_post.call_count == 2

        # It waited once, for 0.5 seconds.
        mock_sleep.assert_called_once_with(0.5)

        # Both requests sent the same event payload.
        first_payload = mock_post.call_args_list[0].kwargs["content"]
        second_payload = mock_post.call_args_list[1].kwargs["content"]

        assert first_payload == second_payload
        assert first_payload == event.model_dump_json()


def test_non_retryable_422_stops_immediately():
    # ARRANGE: Create a valid event.
    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    endpoint = "http://127.0.0.1:8000/v1/events"

    # Construct a real HTTPX response, but don't send a real request.
    request = httpx.Request("POST", endpoint)
    response_422 = httpx.Response(
        status_code=422,
        request=request,
        json={"detail": "Invalid event data"},
    )

    with (
        patch("aegis_simulator.delivery.httpx.post") as mock_post,
        patch("aegis_simulator.delivery.time.sleep") as mock_sleep,
    ):
        mock_post.return_value = response_422

        # ACT + ASSERT: HTTP 422 must raise an exception.
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            send_incident_event(
                event=event,
                endpoint=endpoint,
                max_attempts=3,
            )

        # Only one request should have been attempted.
        assert mock_post.call_count == 1

        # No retry means no sleeping.
        mock_sleep.assert_not_called()

        # Verify the original HTTP status is preserved.
        assert exc_info.value.response.status_code == 422


def test_connection_failure_then_success():
    # ARRANGE
    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    endpoint = "http://127.0.0.1:8000/v1/events"

    request = httpx.Request("POST", endpoint)

    connection_error = httpx.ConnectError(
        "Connection refused",
        request=request,
    )

    response_200 = httpx.Response(
        status_code=200,
        request=request,
        json={"status": "received"},
    )

    with (
        patch("aegis_simulator.delivery.httpx.post") as mock_post,
        patch("aegis_simulator.delivery.time.sleep") as mock_sleep,
    ):
        # First call raises an exception.
        # Second call returns HTTP 200.
        mock_post.side_effect = [
            connection_error,
            response_200,
        ]

        # ACT
        result = send_incident_event(
            event=event,
            endpoint=endpoint,
            max_attempts=3,
        )

        # ASSERT
        assert result is response_200
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(0.5)


def test_retry_exhaustion_after_three_503_responses():
    # ARRANGE
    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    endpoint = "http://127.0.0.1:8000/v1/events"

    request = httpx.Request("POST", endpoint)

    response_503 = httpx.Response(
        status_code=503,
        request=request,
        json={"detail": "Service unavailable"},
    )

    with (
        patch("aegis_simulator.delivery.httpx.post") as mock_post,
        patch("aegis_simulator.delivery.time.sleep") as mock_sleep,
    ):
        # Every request receives HTTP 503.
        mock_post.return_value = response_503

        # ACT + ASSERT
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            send_incident_event(
                event=event,
                endpoint=endpoint,
                max_attempts=3,
            )

        # Exactly three HTTP requests.
        assert mock_post.call_count == 3

        # Sleep only between attempts, never after the last one.
        assert mock_sleep.call_count == 2
        assert [
            call.args[0] for call in mock_sleep.call_args_list
        ] == [0.5, 1.0]

        # Preserve the final HTTP failure.
        assert exc_info.value.response.status_code == 503


def test_connection_error_retry_exhaustion():
    # ARRANGE
    event = create_incident_event(
        incident_id=uuid4(),
        severity=IncidentSeverity.WARNING,
        source="checkout-service",
        title="Payment gateway timeout",
    )

    endpoint = "http://127.0.0.1:8000/v1/events"
    request = httpx.Request("POST", endpoint)

    connection_error = httpx.ConnectError(
        "Connection refused",
        request=request,
    )

    with (
        patch("aegis_simulator.delivery.httpx.post") as mock_post,
        patch("aegis_simulator.delivery.time.sleep") as mock_sleep,
    ):
        # Every attempt raises a connection error.
        mock_post.side_effect = connection_error

        # ACT + ASSERT
        with pytest.raises(httpx.ConnectError):
            send_incident_event(
                event=event,
                endpoint=endpoint,
                max_attempts=3,
            )

        # Exactly three attempts.
        assert mock_post.call_count == 3

        # No unnecessary sleep after the final failure.
        assert [
            call.args[0] for call in mock_sleep.call_args_list
        ] == [0.5, 1.0]
