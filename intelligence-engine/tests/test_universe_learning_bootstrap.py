"""Universe learning bootstrap — seed gather/learn from index + trading book."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_universe_priority_prefers_index_csvs():
    from knowledge_factory.historical_depth.universe_priority import (
        nifty_50,
        nifty_500,
        nifty_bank,
        priority_tier,
        supported_universe,
        universe_summary,
    )

    assert len(nifty_50()) == 50
    assert len(nifty_500()) == 500
    assert len(nifty_bank()) == 14
    assert "HDFCBANK" in nifty_50()
    assert priority_tier("HDFCBANK") == 1
    assert priority_tier("IDBI") == 5  # Nifty 500
    summary = universe_summary()
    assert summary["supported_unique"] >= 2300
    assert len(supported_universe()) == summary["supported_unique"]


def test_bootstrap_nifty500_seeds_queue_without_live_cgl():
    from universe_learning.bootstrap import bootstrap_universe_learning

    # PYTEST_CURRENT_TEST is set by pytest → CGL stays stubbed
    out = bootstrap_universe_learning(
        scope="nifty500",
        run_cgl=True,
        force_refresh_queue=True,
        icf_tick=False,
    )
    assert out["ok"] is True
    assert out["scoped_symbols"] >= 500
    assert out["queue"]["total_companies"] >= 500
    assert out["cgl"]["status"] in {"pytest_stub", "queued"}
    assert "HDFCBANK" in out["sample"] or out["scoped_symbols"] >= 500


def test_bootstrap_all_scope_covers_trading_book():
    from universe_learning.bootstrap import _scope_symbols

    all_syms = _scope_symbols("all")
    n500 = _scope_symbols("nifty500")
    assert len(all_syms) >= len(n500)
    assert "IDBI" in all_syms


def test_learning_status_shape():
    from universe_learning.production import health, learning_status

    h = health()
    assert h["ok"] is True
    st = learning_status()
    assert st["universe"]["nifty_500"] == 500
    assert "queue" in st
