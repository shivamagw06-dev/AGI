"""Sprint A — Ask path must never call faa.acquire."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ail.pipeline import AilPipeline
from app.faa.background import collector_enabled, run_collector_once
from app.fre.service import FreService
from app.fre.store import FreStore
from app.ui.timeouts import call_with_timeout


def test_fre_consult_never_acquires_faa():
    fre = FreService(store=FreStore())
    faa = MagicMock()
    fre.bind(faa=faa)
    pack = fre.consult("Should I buy Reliance?", limit=5)
    assert pack["live_faa_acquire"] is False
    assert pack["acquisition_mode"] == "index_only"
    assert "never_faa_acquire_on_ask" in pack["invariants"]
    faa.acquire.assert_not_called()


def test_ail_soft_pull_never_calls_faa_acquire():
    pipe = AilPipeline()
    faa = MagicMock()
    faa.store.snapshot.return_value = {
        "latest": [
            {
                "title": "Cached IR note",
                "url": "https://example.com/ir",
                "connector_id": "company_ir",
                "company": "Reliance",
                "document_id": "faadoc_1",
            }
        ]
    }
    fre = MagicMock()
    fre.search.return_value = {
        "evidence": [{"claim": "Seed claim", "source": "seed", "confidence": 0.7}]
    }
    pipe.bind(faa=faa, fre=fre)
    rows = pipe.soft_pull_upstream("Reliance outlook", "RELIANCE", pull_faa=True)
    faa.acquire.assert_not_called()
    fre.query.assert_not_called()
    fre.search.assert_called()
    assert rows


def test_call_with_timeout_returns_default():
    def _hang():
        import time

        time.sleep(2.0)
        return "late"

    result, timed_out = call_with_timeout(_hang, timeout_sec=0.2, default={"ok": False})
    assert timed_out is True
    assert result == {"ok": False}


def test_background_collector_uses_refresh_snapshots():
    faa = MagicMock()
    faa.refresh_snapshots.return_value = {"ok": True, "queries": 2, "runs": []}
    out = run_collector_once(faa)
    faa.refresh_snapshots.assert_called_once_with(
        limit_per_query=3,
        mode="nightly",
        max_runtime_sec=3600,
    )
    assert out["ok"] is True
    assert collector_enabled() in {True, False}  # env-dependent, just callable
