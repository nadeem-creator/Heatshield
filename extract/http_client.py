"""Provide resilient JSON HTTP requests for external APIs."""

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests


LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After") if response is not None else None

    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(
                    0.0,
                    (retry_at - datetime.now(timezone.utc)).total_seconds(),
                )
            except (TypeError, ValueError):
                pass

    return 2 ** (attempt - 1)


def get_json_with_retry(
    url,
    *,
    source_name,
    headers=None,
    params=None,
    timeout=30,
    max_attempts=3,
):
    """Return JSON, retrying transient HTTP and network failures."""
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            response = error.response
            status_code = response.status_code if response is not None else None
            retryable = status_code is None or status_code in RETRYABLE_STATUS_CODES

            if not retryable or attempt == max_attempts:
                raise

            wait_seconds = _retry_delay(response, attempt)
            LOGGER.warning(
                "%s request failed on attempt %s/%s with status %s; "
                "retrying in %.1f seconds",
                source_name,
                attempt,
                max_attempts,
                status_code or "network error",
                wait_seconds,
            )
            time.sleep(wait_seconds)

    raise RuntimeError("HTTP retry loop ended unexpectedly.")
