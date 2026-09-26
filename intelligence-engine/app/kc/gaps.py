"""Knowledge gap detection and internal task list (Phase 9)."""

from __future__ import annotations

from typing import Any

from app.kc.models import GapTask
from app.kc.quality import score_company, score_macro, score_sector, score_theme
from app.kc.universes import nifty50_tickers


def detect_gaps(kf: Any, *, earnings_keys: set[str] | None = None) -> list[GapTask]:
    """Scan KF store for weak / stale / missing institutional coverage."""
    store = kf.store
    earnings_keys = earnings_keys or set()
    tasks: list[GapTask] = []
    n50 = nifty50_tickers()

    for t in sorted(n50):
        co = store.companies.get(t)
        if co is None:
            tasks.append(
                GapTask(
                    task_id=f"gap_company_missing_{t}",
                    kind="weak_company_coverage",
                    severity="critical",
                    object_kind="company",
                    object_key=t,
                    title=f"Missing Nifty 50 dossier: {t}",
                    detail="Company not yet present as a permanent knowledge object.",
                    suggested_action="Populate company dossier from AGI research / filings.",
                )
            )
            continue
        q = score_company(co)
        if q.overall_quality < 0.45 or q.completeness_score < 0.35:
            tasks.append(
                GapTask(
                    task_id=f"gap_company_weak_{t}",
                    kind="weak_company_coverage",
                    severity="high",
                    object_kind="company",
                    object_key=t,
                    title=f"Weak coverage: {t}",
                    detail=f"Overall quality {q.overall_quality}; completeness {q.completeness_score}.",
                    suggested_action="Extract business model, risks, catalysts and house view.",
                )
            )
        if float(co.meta.freshness or 0) < 0.45 or float(co.meta.confidence or 0) < 0.4:
            tasks.append(
                GapTask(
                    task_id=f"gap_company_stale_{t}",
                    kind="stale_research" if float(co.meta.freshness or 0) < 0.45 else "low_confidence",
                    severity="medium",
                    object_kind="company",
                    object_key=t,
                    title=f"Stale or low-confidence knowledge: {t}",
                    detail=f"Freshness {co.meta.freshness}; confidence {co.meta.confidence}.",
                    suggested_action="Ingest latest AGI note or earnings update.",
                )
            )
        if t not in earnings_keys and not any("earnings" in str(x).lower() for x in (co.related_research or [])):
            tasks.append(
                GapTask(
                    task_id=f"gap_earnings_{t}",
                    kind="missing_earnings",
                    severity="medium",
                    object_kind="company",
                    object_key=t,
                    title=f"Missing earnings memory: {t}",
                    detail="No structured quarterly earnings update linked yet.",
                    suggested_action="Ingest latest earnings transcript / result note.",
                )
            )
        if not co.related_research and not co.latest_thesis:
            tasks.append(
                GapTask(
                    task_id=f"gap_ar_{t}",
                    kind="missing_annual_report",
                    severity="low",
                    object_kind="company",
                    object_key=t,
                    title=f"No research timeline yet: {t}",
                    detail="Annual reports / investor presentations not structured into dossier.",
                    suggested_action="Ingest AR / investor presentation into KIP → KF.",
                )
            )

    for sid, sec in store.sectors.items():
        q = score_sector(sec)
        if not sec.current_agi_view or q.overall_quality < 0.45 or float(sec.meta.freshness or 0) < 0.4:
            tasks.append(
                GapTask(
                    task_id=f"gap_sector_{sid}",
                    kind="outdated_sector_dossier",
                    severity="high" if sid in {"banking", "it_services", "fmcg"} else "medium",
                    object_kind="sector",
                    object_key=sid,
                    title=f"Sector dossier needs refresh: {sec.label}",
                    detail=f"Quality {q.overall_quality}; view='{sec.current_agi_view or 'none'}'.",
                    suggested_action="Publish sector update and rebuild sector knowledge.",
                )
            )

    for tid, th in store.themes.items():
        q = score_theme(th)
        if not th.current_agi_view or q.completeness_score < 0.4:
            tasks.append(
                GapTask(
                    task_id=f"gap_theme_{tid}",
                    kind="missing_theme_view",
                    severity="medium",
                    object_kind="theme",
                    object_key=tid,
                    title=f"Theme view incomplete: {th.label}",
                    detail="Current AGI view or thesis coverage is thin.",
                    suggested_action="Link latest theme research and beneficiaries.",
                )
            )

    for mid, m in store.macros.items():
        q = score_macro(m)
        if not m.current_agi_view or q.completeness_score < 0.4:
            tasks.append(
                GapTask(
                    task_id=f"gap_macro_{mid}",
                    kind="missing_macro_view",
                    severity="medium",
                    object_kind="macro",
                    object_key=mid,
                    title=f"Macro outlook missing: {m.label}",
                    detail="Macro object lacks current AGI outlook.",
                    suggested_action="Update macro library from latest briefing.",
                )
            )

    # Conflicting knowledge — bull and bear both empty while thesis claims certainty, or opposite lists collide simply
    for t, co in store.companies.items():
        if co.bull_case and co.bear_case:
            overlap = {str(x).lower() for x in co.bull_case} & {str(x).lower() for x in co.bear_case}
            if overlap:
                tasks.append(
                    GapTask(
                        task_id=f"gap_conflict_{t}",
                        kind="conflicting_knowledge",
                        severity="high",
                        object_kind="company",
                        object_key=t,
                        title=f"Conflicting knowledge signals: {t}",
                        detail=f"Overlapping bull/bear points: {sorted(overlap)[:3]}",
                        suggested_action="Reconcile house view and version the change reason.",
                    )
                )

    # Deduplicate by task_id, severity order
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    uniq: dict[str, GapTask] = {}
    for task in tasks:
        uniq[task.task_id] = task
    return sorted(uniq.values(), key=lambda g: (severity_rank.get(g.severity, 9), g.object_key))
