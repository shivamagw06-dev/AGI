"""Research queue prioritisation — packaging only; never Buy/Sell."""

from __future__ import annotations

from typing import Any

from app.schemas.models import ResearchQueueItem

FORBIDDEN = ("buy", "sell", "execute", "purchase", "liquidate")


def build_research_queue(
    *,
    symbols: list[str],
    watchlist: list[str],
    prior_runs: list[dict[str, Any]] | None = None,
    portfolio_recs: list[dict[str, Any]] | None = None,
    sector_hints: dict[str, str] | None = None,
) -> list[ResearchQueueItem]:
    items: list[ResearchQueueItem] = []
    seen: set[str] = set()
    prior_runs = prior_runs or []
    portfolio_recs = portfolio_recs or []
    sector_hints = sector_hints or {}

    # High: symbols with prior low-confidence or forecast-like metadata flags
    for run in prior_runs:
        sym = None
        if run.get("symbols"):
            sym = str(run["symbols"][0]).upper()
        conf = None
        report = run.get("report") or {}
        if isinstance(report, dict):
            conf = (report.get("confidence") or {}).get("score")
        meta = run.get("metadata") or {}
        forecast_changed = bool(meta.get("forecast_changed") or meta.get("forecast_revision"))
        if sym and (forecast_changed or (isinstance(conf, int) and conf < 45)):
            key = f"high:{sym}"
            if key not in seen:
                seen.add(key)
                items.append(
                    ResearchQueueItem(
                        priority="high",
                        symbol=sym,
                        title=sym,
                        reason="Forecast changed" if forecast_changed else "Research confidence declined",
                        evidence=[
                            f"prior_run={run.get('run_id')}",
                            f"confidence={conf}",
                            f"forecast_changed={forecast_changed}",
                        ],
                        confidence=int(conf) if isinstance(conf, int) else 55,
                        supporting_research=[str(run.get("run_id") or "prior_research")],
                        related_reports=[str(run.get("desk") or "research")],
                    )
                )

    for rec in portfolio_recs:
        syms = rec.get("symbols") or []
        sym = str(syms[0]).upper() if syms else None
        title = rec.get("title") or (sym or "Portfolio item")
        key = f"port:{title}"
        if key in seen:
            continue
        seen.add(key)
        pri = rec.get("priority") or "medium"
        if pri not in {"high", "medium", "low"}:
            pri = "medium"
        items.append(
            ResearchQueueItem(
                priority=pri,  # type: ignore[arg-type]
                symbol=sym,
                title=str(title),
                reason=str(rec.get("reason") or "Portfolio Office flagged for review"),
                evidence=list(rec.get("evidence") or [])[:6],
                confidence=int(rec.get("confidence") or 55),
                supporting_research=list(rec.get("supporting_research") or ["Portfolio Office"]),
                related_reports=["portfolio_office"],
            )
        )

    # Medium: watchlist symbols without high items
    for raw in watchlist:
        sym = str(raw).strip().upper()
        if not sym or any(i.symbol == sym and i.priority == "high" for i in items):
            continue
        key = f"wl:{sym}"
        if key in seen:
            continue
        seen.add(key)
        sector = sector_hints.get(sym)
        reason = f"{sector} exposure under review" if sector else "Watchlist name — monitor for material changes"
        items.append(
            ResearchQueueItem(
                priority="medium",
                symbol=sym,
                title=sym,
                reason=reason,
                evidence=[f"watchlist:{sym}"],
                confidence=55,
                supporting_research=["Watchlist Intelligence"],
                related_reports=["watchlist"],
            )
        )

    # Low: remaining symbols — quarterly/update placeholder (not fabricated earnings)
    for raw in symbols:
        sym = str(raw).strip().upper()
        if not sym or any(i.symbol == sym for i in items):
            continue
        key = f"low:{sym}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            ResearchQueueItem(
                priority="low",
                symbol=sym,
                title=sym,
                reason="Quarterly update / coverage refresh available for review",
                evidence=[f"symbol_universe:{sym}"],
                confidence=50,
                supporting_research=["Equity Research Desk"],
                related_reports=["equity"],
            )
        )

    clean: list[ResearchQueueItem] = []
    for item in items:
        blob = f"{item.title} {item.reason}".lower()
        if any(w in blob for w in FORBIDDEN):
            continue
        clean.append(item)

    # Stable priority order
    order = {"high": 0, "medium": 1, "low": 2}
    clean.sort(key=lambda x: (order.get(x.priority, 9), x.title))
    return clean[:24]
