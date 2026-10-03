"""Provider resilience — permanent failures never retry; circuits open."""

from __future__ import annotations

from app.resilience.circuit_breaker import ProviderCircuitRegistry
from app.resilience.policy import RetryDecision, classify_http_status, is_permanent_failure
from app.resilience.retry import PermanentProviderError, TransientProviderError, retry_sync


def test_classify_permanent_vs_transient():
    for code in (401, 402, 403, 404, 400, 422):
        assert classify_http_status(code) is RetryDecision.NEVER
        assert is_permanent_failure(code)
    for code in (429, 500, 502, 503, 504):
        assert classify_http_status(code) is RetryDecision.TRANSIENT


def test_retry_sync_never_retries_permanent():
    calls = {"n": 0}

    def _boom():
        calls["n"] += 1
        raise PermanentProviderError("yahoo", "HTTP 401", status=401)

    try:
        retry_sync(_boom, max_attempts=4)
        assert False, "expected PermanentProviderError"
    except PermanentProviderError:
        pass
    assert calls["n"] == 1


def test_retry_sync_retries_transient():
    calls = {"n": 0}

    def _flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TransientProviderError("agib_node", "HTTP 503", status=503)
        return {"ok": True}

    out = retry_sync(_flaky, max_attempts=3, base_s=0.01, max_s=0.02)
    assert out["ok"] is True
    assert calls["n"] == 2


def test_circuit_opens_after_threshold():
    reg = ProviderCircuitRegistry(fail_threshold=3, cooldown_sec=900)
    assert reg.allow("vendor_x")
    reg.failure("vendor_x", error="503", status=503)
    reg.failure("vendor_x", error="503", status=503)
    assert reg.allow("vendor_x")
    reg.failure("vendor_x", error="503", status=503)
    assert reg.allow("vendor_x") is False
    snap = reg.status()["vendor_x"]
    assert snap["state"] == "open"
    assert snap["last_status"] == 503


def test_leo_fetch_for_plan_marks_parallel():
    from leo.fetchers import fetch_for_plan

    out = fetch_for_plan(
        {"ticker": "RELIANCE"},
        [{"source_id": "internal_research", "via": "soft"}],
    )
    assert out.get("parallel") is True
    assert isinstance(out.get("api_calls"), list)
