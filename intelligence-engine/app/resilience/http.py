"""Hard-timeout HTTP helpers with circuit breakers and smart retries."""

from __future__ import annotations

from typing import Any

import httpx

from app.resilience.circuit_breaker import get_provider_circuits
from app.resilience.policy import ProviderPolicy, classify_http_status, RetryDecision
from app.resilience.retry import (
    PermanentProviderError,
    TransientProviderError,
    retry_sync,
    status_to_error,
)


def _timeout(policy: ProviderPolicy) -> httpx.Timeout:
    return httpx.Timeout(
        connect=policy.connect_timeout_sec,
        read=policy.read_timeout_sec,
        write=policy.read_timeout_sec,
        pool=policy.connect_timeout_sec,
    )


def resilient_get_json(
    url: str,
    *,
    provider_id: str,
    headers: dict[str, str] | None = None,
    policy: ProviderPolicy | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """GET JSON with circuit breaker + permanent/transient classification.

    Returns ``None`` on permanent failure, open circuit, or exhausted retries —
    never raises into the Ask path.
    """
    pol = policy or ProviderPolicy()
    circuits = get_provider_circuits()
    if not circuits.allow(provider_id):
        return None

    def _once() -> dict[str, Any]:
        try:
            with httpx.Client(timeout=_timeout(pol), follow_redirects=True) as client:
                resp = client.get(url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise TransientProviderError(provider_id, f"timeout: {exc}", status=None) from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(provider_id, f"transport: {exc}", status=None) from exc

        if resp.status_code < 400:
            return resp.json() if resp.content else {}
        raise status_to_error(provider_id, resp.status_code, resp.text)

    try:
        data = retry_sync(
            _once,
            max_attempts=pol.max_attempts,
            base_s=pol.backoff_base_sec,
            max_s=pol.backoff_max_sec,
        )
        circuits.success(provider_id)
        return data
    except PermanentProviderError as exc:
        # Do not trip circuit on auth/config mistakes — skip provider, don't cool-down forever wrongly.
        # Still record so ops can see it; use threshold carefully.
        circuits.failure(provider_id, error=str(exc), status=exc.status)
        return None
    except TransientProviderError as exc:
        circuits.failure(provider_id, error=str(exc), status=exc.status)
        return None
    except Exception as exc:  # noqa: BLE001
        circuits.failure(provider_id, error=str(exc)[:200])
        return None


def should_retry_status(status: int) -> bool:
    return classify_http_status(status) is RetryDecision.TRANSIENT
