"""A run that wrote data is not a failed run."""

from __future__ import annotations

import inspect

from valuation_ratios import sweep


def test_a_degraded_run_is_not_recorded_as_a_failed_job():
    """The reason this collector looked dead for months.

    finish_job was called with ok=(status == HEALTHY), so a batch that fetched
    253 companies at 90.68% coverage was recorded as a failed job. Every one of
    the twelve runs on 2026-08-21 read as `failed` while ten of them were
    DEGRADED and had written data.
    """
    src = inspect.getsource(sweep.run)
    assert "ok=status != FAILED" in src
    assert "ok=status == HEALTHY" not in src


def test_the_three_states_still_mean_what_they_say():
    assert sweep.HEALTHY_COVERAGE_PCT == 95.0
    assert sweep.FAILED == "FAILED"


def test_failed_is_still_reserved_for_a_run_that_wrote_nothing():
    """The status ladder itself was correct and is unchanged."""
    src = inspect.getsource(sweep.run)
    assert "FAILED if not successful" in src
