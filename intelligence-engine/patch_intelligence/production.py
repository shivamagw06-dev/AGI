"""Patch Intelligence production façade — briefs only."""

from __future__ import annotations

from typing import Any

from patch_intelligence.briefs.builder import build_brief, build_queue
from patch_intelligence.schema import FREEZE_LOCKS, MODULE_CODE, PI_VERSION, PROGRAMME


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "version": PI_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "never_writes_code_automatically": True,
        "human_in_the_loop": True,
        "freeze_locks": dict(FREEZE_LOCKS),
        "api_prefix": "/v1/patch-intelligence",
        "fabricated": False,
    }


def from_rci(rci_analysis: dict[str, Any], *, top_n: int = 10) -> dict[str, Any]:
    return build_queue(rci_analysis, top_n=top_n)


def from_latest_rci(*, top_n: int = 10) -> dict[str, Any]:
    from root_cause_intelligence import store as rci_store
    from root_cause_intelligence.production import analyze_from_iel_run

    latest = rci_store.latest()
    if not latest or not latest.get("top_10_clusters"):
        # Run a fresh soft analysis (smoke-sized if needed — prefer full nightly context)
        latest = analyze_from_iel_run(suite="institutional_1000", mode="soft")
    return build_queue(latest, top_n=top_n)


def brief_for_cluster(cluster: dict[str, Any], *, rci_context: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_brief(cluster, rci_context=rci_context)
