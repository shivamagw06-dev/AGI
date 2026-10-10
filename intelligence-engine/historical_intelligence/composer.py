"""Historical planner and answer composer.

Question in, grounded historical answer out:

    question -> historical intent -> coverage -> span guard -> module -> explain -> compose

The composer never invents connective tissue. Every sentence it emits traces to a
module conclusion, a coverage window or a guard disclosure.
"""

from __future__ import annotations

from typing import Any, Optional

from historical_intelligence import comparison, coverage as coverage_engine, events, intent, trend, valuation
from historical_intelligence.explain import explain
from institutional_warehouse.values import normalise_entity

ENGINE = "historical_intelligence"
VERSION = "hie-v1.0.0"


def plan(question: str, *, symbol: Optional[str] = None) -> dict[str, Any]:
    """What the engine intends to do, before it does it."""
    parsed = intent.classify(question or "")
    ticker = normalise_entity(symbol) if symbol else None
    if not ticker:
        candidates = parsed.get("symbols") or []
        ticker = candidates[0] if candidates else None
    return {
        "ok": True,
        "question": question,
        "historical": parsed["historical"],
        "module": parsed["module"],
        "metric": parsed["metric"],
        "period": parsed["period"],
        "symbol": ticker,
        "extra_symbols": [s for s in (parsed.get("symbols") or []) if s != ticker],
    }


def answer(question: str, *, symbol: Optional[str] = None,
           peers: Optional[list[str]] = None) -> dict[str, Any]:
    """The historical answer for a question, or an honest account of why there isn't one."""
    intended = plan(question, symbol=symbol)
    ticker = intended["symbol"]
    if not ticker:
        return {
            "ok": False,
            "engine": ENGINE,
            "error": "no_company_resolved",
            "detail": "A historical question needs a company to be about.",
            "plan": intended,
        }

    metric = intended["metric"]
    period = intended["period"]
    module_name = intended["module"]

    if module_name == "comparison":
        others = [s for s in (list(peers or []) or intended["extra_symbols"]) if s != ticker]
        if others:
            module = comparison.compare([ticker, *others], metric)
        elif metric in valuation.MULTIPLES:
            # Nothing to compare against: the question is about this company's own record.
            module = valuation.analyse(ticker, metric, period=period)
        else:
            module = trend.analyse(ticker, metric, period=period)
    elif module_name == "valuation_extreme":
        module = trend.extreme(ticker, metric, want=_extreme_direction(question), period=period)
    elif module_name == "trend_extreme":
        module = trend.extreme(ticker, metric, want=_extreme_direction(question), period=period)
    elif module_name == "events":
        module = events.timeline(ticker, period=period)
    elif period.get("kind") == "named":
        module = events.around(ticker, period)
    elif metric in valuation.MULTIPLES and _valuation_shaped(question):
        module = valuation.analyse(ticker, metric, period=period)
    else:
        module = trend.analyse(ticker, metric, period=period)

    if not module.get("ok"):
        return {"ok": False, "engine": ENGINE, "plan": intended, **module}

    closing = explain(module)
    return {
        "ok": True,
        "engine": ENGINE,
        "version": VERSION,
        "question": question,
        "symbol": ticker,
        "metric": metric,
        "module": module.get("module"),
        "plan": intended,
        "answer": compose(module, closing),
        "finding": module.get("finding"),
        "conclusions": module.get("conclusions") or [],
        "observation_window": closing["observation_window"],
        "confidence": closing["confidence"],
        "confidence_score": closing.get("confidence_score"),
        "coverage_limited": module.get("guard", {}).get("verdict") != "covered",
        "explain": closing,
        "detail": {k: v for k, v in module.items() if k not in ("coverage", "guard")},
        "coverage": module.get("coverage"),
        "guard": module.get("guard"),
    }


def _extreme_direction(question: str) -> str:
    text = (question or "").lower()
    if any(word in text for word in ("cheapest", "lowest", "trough", "worst", "least")):
        return "low"
    return "high" if any(word in text for word in
                         ("dearest", "highest", "most expensive", "peak", "best")) else "low"


def _valuation_shaped(question: str) -> bool:
    text = (question or "").lower()
    return any(word in text for word in (
        "valuation", "multiple", "expensive", "cheap", "rerat", "re-rat", "premium",
        "discount", "p/e", "pe ", "p/b", "pb ", "price to", "yield",
    ))


def compose(module: dict[str, Any], closing: dict[str, Any]) -> str:
    """The prose answer. Window first, because it frames everything after it."""
    lines: list[str] = []
    guard = module.get("guard") or {}

    if guard.get("disclosure") and not guard.get("may_conclude"):
        # Nothing may be concluded: the disclosure *is* the answer.
        return guard["disclosure"]

    window = closing.get("observation_window")
    if window:
        lines.append(f"Observed history: {window}.")

    for sentence in module.get("conclusions") or []:
        lines.append(sentence)

    if closing.get("why_it_mattered"):
        lines.append(closing["why_it_mattered"])

    for limit in closing.get("limits") or []:
        lines.append(limit)

    if closing.get("confidence_note"):
        lines.append(closing["confidence_note"])

    return " ".join(line.strip() for line in lines if line and line.strip())


def company_history(symbol: str, *, metrics: Optional[list[str]] = None) -> dict[str, Any]:
    """The timeline cards for one company: coverage, trend, valuation, events."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}

    cover = coverage_engine.company_coverage(ticker)
    wanted = metrics or ["price", "revenue", "pat", "roe"]
    cards: dict[str, Any] = {}
    for metric in wanted:
        card = trend.analyse(ticker, metric)
        if card.get("ok"):
            cards[metric] = {
                "finding": card.get("finding"),
                "conclusions": card.get("conclusions"),
                "window": card.get("observation_window"),
                "confidence": card.get("confidence"),
                "cagr_pct": card.get("cagr_pct"),
                "inflection_points": card.get("inflection_points"),
            }
    val = valuation.analyse(ticker, "pe")
    timeline = events.timeline(ticker, limit=12)

    return {
        "ok": True,
        "engine": ENGINE,
        "symbol": ticker,
        "coverage": cover,
        "trend_cards": cards,
        "valuation": {
            "finding": val.get("finding"),
            "conclusions": val.get("conclusions"),
            "window": val.get("observation_window"),
            "confidence": val.get("confidence"),
            "percentile": val.get("percentile"),
            "median": val.get("median"),
            "rerating": val.get("rerating"),
        },
        "events": {
            "finding": timeline.get("finding"),
            "conclusions": timeline.get("conclusions"),
            "recent": (timeline.get("events") or [])[:12],
            "window": timeline.get("observation_window"),
        },
        "deferred_modules": DEFERRED,
    }


# Stated in the output so a consumer knows what is absent by design rather than by bug.
DEFERRED = {
    "consensus_evolution": "needs more than one consensus snapshot; consensus now appends daily",
    "management_evolution": "needs structured CEO, chairman and CFO tenure history",
    "business_evolution": "needs historical segment, product and geography mix",
    "cycle_intelligence": "needs a macro regime series in the warehouse",
}
