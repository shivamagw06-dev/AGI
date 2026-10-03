"""IUI pipeline — bootstrap registry → membership → incremental company compile."""

from __future__ import annotations

from typing import Any

from universe_intelligence.incremental import apply_incremental
from universe_intelligence.membership import bootstrap_membership_events
from universe_intelligence.registry import bootstrap_universes
from universe_intelligence.schema import IUI_VERSION, envelope
from universe_intelligence import store as iui_store


def run_universe_intelligence_pipeline(
    *,
    universe_id: str = "NIFTY_500",
    force_full: bool = False,
    ensure_kf: bool = True,
) -> dict[str, Any]:
    """Operational pipeline. Soft-wires KF; never touches Phases 1–7."""
    reg = bootstrap_universes()
    mem = bootstrap_membership_events()
    inc = apply_incremental(universe_id, force_full=force_full, ensure_kf=ensure_kf)
    report = envelope(
        kind="iui_pipeline",
        payload={
            "status": "operational",
            "universe_id": universe_id.upper(),
            "registry": {"n": reg.get("n")},
            "membership_events": mem.get("events"),
            "incremental": inc,
            "iui_version": IUI_VERSION,
        },
    )
    iui_store.put_report("pipeline", report)
    return report
