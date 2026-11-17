from aegis_contracts import IncidentEvent
import httpx
from aegis_simulator import create_incident_event
import uuid
import time

import time
import httpx

from aegis_contracts import IncidentEvent


def send_incident_event(
    event: IncidentEvent,
    endpoint: str,
    max_attempts: int = 3,
) -> httpx.Response:
    """
    Send an incident event to the investigator service.

    Retries transient HTTP failures and network errors using
    exponential backoff. Every attempt sends the same event.

    Args:
        event: The incident event to deliver.
        endpoint: The investigator's HTTP endpoint.
        max_attempts: Maximum number of HTTP requests, including
            the initial request.

    Returns:
        The successful HTTP response.

    Raises:
        ValueError: If max_attempts is less than 1.
        httpx.HTTPStatusError: If the server returns an unsuccessful
            HTTP status and delivery cannot continue.
        httpx.RequestError: If a network failure persists.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    # Serialize once so retries send exactly the same event.
    payload = event.model_dump_json()

    for attempt in range(max_attempts):
        try:
            response = httpx.post(
                endpoint,
                content=payload,
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )

            # Success: no retry required.
            if 200 <= response.status_code < 300:
                print(
                    f"Event {event.event_id} delivered successfully "
                    f"on attempt {attempt + 1}."
                )
                return response

            # Non-retryable response: stop immediately.
            if not is_retryable_status(response.status_code):
                print(
                    f"Non-retryable HTTP {response.status_code} "
                    f"for event {event.event_id}."
                )
                response.raise_for_status()
                raise RuntimeError(
                    f"Unexpected non-success HTTP status: "
                    f"{response.status_code}"
                )

            # Retryable response, but no attempts remain.
            if attempt == max_attempts - 1:
                print(
                    f"Delivery failed after {max_attempts} attempts. "
                    f"Last HTTP status: {response.status_code}."
                )
                response.raise_for_status()

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            print(
                f"Network failure on attempt {attempt + 1}: {exc}"
            )

            # Preserve the original exception when retries are exhausted.
            if attempt == max_attempts - 1:
                raise

        # This executes only when another attempt remains.
        delay = calculate_retry_delay(attempt)

        print(
            f"Retrying event {event.event_id} in {delay} seconds "
            f"(next attempt: {attempt + 2}/{max_attempts})."
        )

        time.sleep(delay)

    # Defensive safeguard: all normal paths return or raise above.
    raise RuntimeError("Incident event delivery ended unexpectedly")

def is_retryable_status(status_code: int) -> bool:
    """
    Check if the given HTTP status code is retryable.

    Args:
        status_code (int): The HTTP status code to check.
    """
    retryable_codes = (429, 500, 502, 503, 504)
    if status_code in retryable_codes:
        return True
    else:
        return False

def calculate_retry_delay(retries: int, base_delay: float = 0.5) -> float:
    """
    Calculate the delay before the next retry attempt using exponential backoff.

    Args:
        retries (int): The number of retry attempts made so far.
        base_delay (float): The base delay in seconds for the first retry.

    Returns:
        float: The calculated delay in seconds for the next retry attempt.
    """
    if retries < 0:
        raise ValueError("Retries must be a non-negative integer.")
    delay = (base_delay * (2 ** retries))
    return delay

if __name__ == "__main__":
    event1 = create_incident_event(
        incident_id=uuid.uuid4(),
        severity="WARNING",
        source="checkout-service",
        title="Payment gateway timeout",
        description="Payment requests exceeded the configured gateway timeout."
    )
    response = send_incident_event(event1, "http://127.0.0.1:8000/v1/events",3)
    print(type(response))
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")