"""Decision journal — record research evolution without inventing history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.models import DecisionJournalEntry


def build_decision_journal(
    *,
    prior_runs: list[dict[str, Any]] | None = None,
    portfolio_pack: dict[str, Any] | None = None,
    scenario_results: list[dict[str, Any]] | None = None,
    queue: list[Any] | None = None,
    seed: list[dict[str, Any]] | None = None,
) -> list[DecisionJournalEntry]:
    entries: list[DecisionJournalEntry] = []
    prior_runs = prior_runs or []
    seed = seed or []

    for raw in seed:
        try:
            entries.append(DecisionJournalEntry(**raw))
        except Exception:
            continue

    for run in prior_runs[:12]:
        desk = run.get("desk") or "research"
        thesis = (
            run.get("cio_thesis")
            or run.get("thesis")
            or (run.get("report") or {}).get("executive_summary")
            or ""
        )
        entries.append(
            DecisionJournalEntry(
                kind="research_completed",
                title=f"Research run ({desk})",
                detail=(thesis or run.get("query") or "Research package completed")[:400],
                ts=_ts(run.get("completed_at") or run.get("created_at")),
                evidence=[f"run_id={run.get('run_id')}"],
                confidence=((run.get("report") or {}).get("confidence") or {}).get("score"),
                related_run_id=run.get("run_id"),
            )
        )
        meta = run.get("metadata") or {}
        if meta.get("forecast_changed") or meta.get("forecast_revision"):
            entries.append(
                DecisionJournalEntry(
                    kind="forecast_revision",
                    title="Forecast revision noted",
                    detail=str(meta.get("forecast_revision") or meta.get("forecast_changed"))[:400],
                    ts=_ts(run.get("updated_at") or run.get("created_at")),
                    evidence=[f"run_id={run.get('run_id')}"],
                    related_run_id=run.get("run_id"),
                )
            )

    if portfolio_pack:
        entries.append(
            DecisionJournalEntry(
                kind="portfolio_review",
                title="Portfolio Office package attached",
                detail=(
                    f"Health={portfolio_pack.get('health_score')}; "
                    f"recommendations={len(portfolio_pack.get('recommendations') or [])}"
                ),
                evidence=["portfolio_office"],
                confidence=portfolio_pack.get("confidence"),
            )
        )

    for sc in scenario_results or []:
        entries.append(
            DecisionJournalEntry(
                kind="scenario_analysis",
                title=str(sc.get("question") or "Scenario")[:160],
                detail=str(sc.get("status") or "") + " — " + "; ".join(sc.get("assumptions") or [])[:300],
                evidence=["scenario_center"],
                confidence=sc.get("confidence"),
            )
        )

    high_q = [
        (i.model_dump() if hasattr(i, "model_dump") else i)
        for i in (queue or [])
        if (getattr(i, "priority", None) or (i.get("priority") if isinstance(i, dict) else None)) == "high"
    ]
    for item in high_q[:5]:
        entries.append(
            DecisionJournalEntry(
                kind="cio_recommendation",
                title=f"Research priority: {item.get('title')}",
                detail=str(item.get("reason") or ""),
                evidence=list(item.get("evidence") or [])[:4],
                confidence=item.get("confidence"),
            )
        )

    # Newest first
    entries.sort(key=lambda e: e.ts, reverse=True)
    return entries[:40]


def research_timeline_from_journal(entries: list[DecisionJournalEntry]) -> list[dict[str, Any]]:
    """Month-bucketed research timeline for workspace."""
    buckets: dict[str, list[str]] = {}
    for e in entries:
        key = e.ts.strftime("%Y-%m") if e.ts else "unknown"
        buckets.setdefault(key, []).append(f"{e.kind}: {e.title}")
    timeline = []
    for month in sorted(buckets.keys()):
        notes = buckets[month][:4]
        # Label is descriptive of packaged events — not a fabricated stance
        timeline.append(
            {
                "period": month,
                "label": notes[0].split(":", 1)[0].replace("_", " ").title() if notes else "Research",
                "events": notes,
                "note": "Timeline from Decision Journal / prior runs only — months without evidence are omitted.",
            }
        )
    return timeline


def _ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
