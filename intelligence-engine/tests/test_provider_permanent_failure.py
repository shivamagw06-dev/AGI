"""A permanently broken provider must leave the rotation.

Engine logs on 2026-08-19 showed the collection loop spending roughly 13
seconds per ticker, of which almost all was failure:

    financialmodelingprep  -> 403 Forbidden   (every call; key revoked)
    query2.finance.yahoo   -> 401 Unauthorized
    query1 .../getcrumb    -> 406 Not Acceptable
    fc.yahoo.com           -> 404
    stock.indianapi.in     -> 429 Too Many Requests

The providers classified these correctly as retryable=False. The client then
discarded that: it only called breaker.record_failure() when the error was
retryable, so a permanent failure could never open the circuit. A provider
with a revoked key therefore stayed in the rotation and was re-attempted for
every symbol in a ~2,700 ticker universe, indefinitely.
"""

from __future__ import annotations

import time

import pytest

from app.market_data.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from app.market_data.provider_base import ProviderError


class TestPermanentFailureOpensCircuit:
    def test_single_permanent_failure_opens_immediately(self):
        """A revoked key is known bad on the first response, not the third."""
        br = CircuitBreaker("fmp", failure_threshold=3)
        br.record_permanent_failure()
        assert br.state == CircuitState.OPEN

    def test_open_circuit_blocks_further_calls(self):
        """This is the saving: subsequent symbols never reach the provider."""
        br = CircuitBreaker("fmp")
        br.record_permanent_failure()
        with pytest.raises(CircuitOpenError):
            br.before_call()

    def test_permanent_cooldown_is_far_longer_than_transient(self):
        br = CircuitBreaker("fmp", recovery_timeout_s=30.0, permanent_recovery_timeout_s=900.0)
        br.record_permanent_failure()
        with pytest.raises(CircuitOpenError) as exc:
            br.before_call()
        # Must not come back in ~30s like a transient blip would.
        assert exc.value.retry_after_s > 30.0

    def test_explicit_cooldown_is_honoured(self):
        """A 429 resets on its own; it should not sit out as long as a 401."""
        br = CircuitBreaker("indianapi", permanent_recovery_timeout_s=900.0)
        br.record_permanent_failure(60.0)
        with pytest.raises(CircuitOpenError) as exc:
            br.before_call()
        assert exc.value.retry_after_s <= 60.0

    def test_transient_failures_still_need_the_threshold(self):
        """Permanent handling must not make ordinary blips trip instantly."""
        br = CircuitBreaker("yahoo", failure_threshold=3)
        br.record_failure()
        assert br.state == CircuitState.CLOSED
        br.record_failure()
        assert br.state == CircuitState.CLOSED
        br.record_failure()
        assert br.state == CircuitState.OPEN


class TestRecovery:
    def test_provider_recovers_after_cooldown(self):
        """Parking must not be permanent — a rotated key has to be picked up."""
        br = CircuitBreaker("fmp", permanent_recovery_timeout_s=0.05)
        br.record_permanent_failure()
        assert br.state == CircuitState.OPEN
        time.sleep(0.06)
        assert br.state == CircuitState.HALF_OPEN
        br.before_call()  # half-open must admit a probe
        br.record_success()
        assert br.state == CircuitState.CLOSED

    def test_success_restores_the_short_recovery_window(self):
        """After recovery a later blip should use the transient timeout again."""
        br = CircuitBreaker("fmp", recovery_timeout_s=30.0, permanent_recovery_timeout_s=0.05)
        br.record_permanent_failure()
        time.sleep(0.06)
        br.record_success()
        br.record_failure()
        br.record_failure()
        br.record_failure()
        with pytest.raises(CircuitOpenError) as exc:
            br.before_call()
        assert exc.value.retry_after_s <= 30.0


class TestProviderErrorCarriesCooldown:
    def test_default_cooldown_is_unset(self):
        assert ProviderError("fmp", "boom", retryable=False).cooldown_s is None

    def test_cooldown_round_trips(self):
        assert ProviderError("indianapi", "429", retryable=False, cooldown_s=60.0).cooldown_s == 60.0

    def test_retryable_default_preserved(self):
        assert ProviderError("x", "y").retryable is True
