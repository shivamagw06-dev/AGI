"""Soft monitoring pipeline:

LEO → CID → Financial Intelligence → Company Analysis → House View hint
→ Prediction count → Knowledge timeline stamp → Ask AGI package

Never redesigns those systems; only orchestrates soft reads + change detection.
"""

from __future__ import annotations

from typing import Any

from company_monitor.detect import detect_changes
from company_monitor.flags import flag_auto_pipeline, is_enabled
from company_monitor.house_view_hint import maybe_suggest_review
from company_monitor.schema import DEFAULT_UNIVERSE
from company_monitor.significance import annotate
from company_monitor.snapshot import build_snapshot
from company_monitor import store as cms_store
from company_monitor.summary import build_change_summary


def _soft_load_layers(ticker: str, *, query: str = "") -> dict[str, Any]:
    t = ticker.upper()
    q = query or f"Monitor {t}"
    out: dict[str, Any] = {
        "leo_pkg": {},
        "cid": {},
        "company_analysis": {},
        "house_view": {},
        "predictions": [],
        "financial": {},
        "valuation": {},
    }

    try:
        from leo.production import package_for_query as leo_package

        out["leo_pkg"] = leo_package(q, ticker=t, engine="company_monitor") or {}
    except Exception:
        out["leo_pkg"] = {"ticker": t, "evidence_objects": []}

    try:
        from cid.production import get_or_build

        out["cid"] = (
            get_or_build(
                t,
                query=q,
                leo_pkg=out["leo_pkg"],
            )
            or {}
        )
    except Exception:
        try:
            from cid.production import get_dossier

            out["cid"] = get_dossier(t) or {"ticker": t}
        except Exception:
            out["cid"] = {"ticker": t}

    try:
        from company_analysis.production import analyse as ca_analyse

        ca = ca_analyse(
            q,
            ticker=t,
            cid=out["cid"],
            leo_pkg=out["leo_pkg"],
            record=False,
        ) or {}
        out["company_analysis"] = ca
        out["financial"] = ca.get("financial_intelligence") or {}
        out["valuation"] = ca.get("valuation_intelligence") or {}
    except Exception:
        out["company_analysis"] = {}

    try:
        from app.kip.service import KipService  # type: ignore

        # Prefer lightweight house view if available via production helper
        pass
    except Exception:
        pass

    # House view via KIP soft path if exposed
    try:
        from app.api import routes as api_routes  # noqa: F401
    except Exception:
        pass

    try:
        # Use cid-embedded or empty — never invent stance
        hv = (out["cid"] or {}).get("house_view") or {}
        out["house_view"] = hv if isinstance(hv, dict) else {}
    except Exception:
        out["house_view"] = {}

    return out


def monitor_company(
    ticker: str,
    *,
    query: str = "",
    force_pipeline: bool = False,
    layers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "bypassed": True, "ticker": (ticker or "").upper()}

    t = (ticker or "").upper()
    if not t:
        return {"enabled": True, "ok": False, "reason": "no_ticker"}

    if layers is None and (flag_auto_pipeline() or force_pipeline):
        layers = _soft_load_layers(t, query=query)
    layers = layers or {}

    snap = build_snapshot(
        t,
        cid=layers.get("cid"),
        leo_pkg=layers.get("leo_pkg"),
        financial=layers.get("financial"),
        valuation=layers.get("valuation"),
        company_analysis=layers.get("company_analysis"),
        house_view=layers.get("house_view"),
        predictions=layers.get("predictions"),
    )
    # Capture prior BEFORE put (put moves current → previous)
    previous = cms_store.get_snapshot(t)
    cms_store.put_snapshot(t, snap)

    raw_changes = detect_changes(snap, previous, ticker=t)
    changes = annotate(raw_changes)
    for ch in changes:
        cms_store.add_change(t, ch)

    summary = build_change_summary(changes, current=snap, previous=previous)
    review = maybe_suggest_review(
        t,
        changes=changes,
        summary=summary,
        house_view_label=snap.get("house_view_label"),
    )
    if review:
        cms_store.put_review(t, review)

    timeline_stamp = {
        "event": "company_monitor_cycle",
        "ticker": t,
        "at": snap.get("captured_at"),
        "changes": len(changes),
        "max_significance": summary.get("max_significance"),
    }

    return {
        "enabled": True,
        "ok": True,
        "ticker": t,
        "snapshot": snap,
        "previous_snapshot": previous,
        "changes": changes,
        "what_changed": summary,
        "house_view_review": review,
        "pipeline": {
            "leo": bool(layers.get("leo_pkg")),
            "cid": bool(layers.get("cid")),
            "financial_intelligence": bool(layers.get("financial")),
            "company_analysis": bool(layers.get("company_analysis")),
            "house_view_hint": bool(review),
            "prediction_tracker": int(snap.get("prediction_count") or 0),
            "knowledge_timeline": timeline_stamp,
        },
        "auto_house_view_changed": False,
    }


def monitor_universe(tickers: list[str] | None = None, *, limit: int | None = None) -> dict[str, Any]:
    universe = list(tickers or DEFAULT_UNIVERSE)
    if limit is not None:
        universe = universe[: int(limit)]
    reports = []
    for t in universe:
        try:
            reports.append(monitor_company(t, force_pipeline=True))
        except Exception as exc:
            reports.append({"ticker": t, "ok": False, "error": str(exc)[:200]})
    return {
        "enabled": is_enabled(),
        "attempted": len(universe),
        "succeeded": sum(1 for r in reports if r.get("ok")),
        "reports": reports,
    }
