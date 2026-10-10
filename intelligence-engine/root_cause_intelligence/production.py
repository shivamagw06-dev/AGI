"""Production façade for Root Cause Intelligence (RCI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from root_cause_intelligence.analyze import analyze_iel_run
from root_cause_intelligence.dashboard.board import build_board
from root_cause_intelligence.reports.builder import build_markdown
from root_cause_intelligence.schema import FREEZE_LOCKS, MODULE_CODE, PROGRAMME, QUALITY_TARGETS, RCI_VERSION
from root_cause_intelligence import store


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "version": RCI_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "quality_targets": QUALITY_TARGETS,
        "freeze_locks": dict(FREEZE_LOCKS),
        "api_prefix": "/v1/root-cause-intelligence",
        "role": "Engineering brain — failures → clusters → suggested fixes",
        "fabricated": False,
    }


def board() -> dict[str, Any]:
    return build_board()


def analyze(iel_summary: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
    return analyze_iel_run(iel_summary, persist=persist)


def analyze_from_iel_run(
    *,
    suite: str = "institutional_1000",
    mode: str = "soft",
    limit: int | None = None,
) -> dict[str, Any]:
    """Convenience: run IEL then RCI in one call (nightly)."""
    from institutional_evaluation_lab.production import run as iel_run

    iel = iel_run(suite=suite, mode=mode, limit=limit, persist_baseline=False)
    rci = analyze_iel_run(iel, persist=True)
    md = build_markdown(rci)
    out_path = Path(__file__).resolve().parent / "reports" / "latest.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    light = {k: v for k, v in rci.items() if k != "failures_sample"}
    light["report_path"] = str(out_path)
    light["iel_aggregate"] = iel.get("aggregate")
    return light


def nightly() -> dict[str, Any]:
    return analyze_from_iel_run(suite="institutional_1000", mode="soft")


def history(*, limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "rows": store.list_analyses(limit=limit), "fabricated": False}


def report() -> dict[str, Any]:
    latest = store.latest()
    if not latest:
        return {"markdown": "# No RCI analysis yet\n", "fabricated": False}
    # Rebuild rich markdown from stored compact if needed
    md_path = Path(__file__).resolve().parent / "reports" / "latest.md"
    if md_path.exists():
        return {"markdown": md_path.read_text(encoding="utf-8"), "analysis_id": latest.get("analysis_id")}
    return {"markdown": build_markdown(latest), "analysis_id": latest.get("analysis_id")}
