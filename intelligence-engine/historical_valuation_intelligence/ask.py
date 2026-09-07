"""Ask AGI helpers for historical valuation questions."""

from __future__ import annotations

import re
from typing import Any, Optional

from historical_valuation_intelligence.engine import (
    company_pack,
    regimes_for,
    rerating_for,
    statistics_for,
)
from historical_valuation_intelligence.models import ENGINE_CODE, VERSION

_EXPENSIVE = re.compile(r"\b(expensive|cheap|fairly\s+valued|overvalued|undervalued)\b", re.I)
_CHEAPEST = re.compile(r"\b(cheapest|lowest|when\s+was|least\s+expensive)\b", re.I)
_EVER_CHEAPER = re.compile(r"\b(ever\s+traded\s+cheaper|cheaper\s+than\s+today|own\s+history)\b", re.I)
_SIMILAR = re.compile(
    r"\b(similar\s+to\s+today|valuations?\s+similar|what\s+happened\s+afterwards|"
    r"unusual|versus\s+history|vs\.?\s+history|relative\s+to\s+its\s+own\s+history|"
    r"when\s+has)\b",
    re.I,
)


def is_historical_valuation_question(question: str) -> bool:
    text = str(question or "")
    if not text:
        return False
    low = text.lower()
    return bool(
        _EXPENSIVE.search(text)
        or _CHEAPEST.search(text)
        or _EVER_CHEAPER.search(text)
        or _SIMILAR.search(text)
        or ("historical" in low and ("pe" in low or "p/b" in low or "valuation" in low))
    )


def answer_for(
    symbol: str,
    question: str = "",
    *,
    metric: Optional[str] = None,
) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    q = str(question or "")
    pack = company_pack(ticker, metric=metric, window="10y")
    m = pack.get("metric") or metric or "pe"
    label = m.upper().replace("_", "/")

    if not pack.get("ok"):
        return {
            "ok": False,
            "symbol": ticker,
            "error": pack.get("reason") or pack.get("error") or "unavailable",
            "engine": ENGINE_CODE,
        }

    if _CHEAPEST.search(q):
        rr = rerating_for(ticker, metric=m, window="max")
        cheap = (rr or {}).get("cheapest") or {}
        prose = (
            f"Lowest {label}\n\n"
            f"{cheap.get('value')}\n\n"
            f"Observed\n{cheap.get('date')}\n\n"
            f"Coverage\n{(pack.get('coverage') or {}).get('coverage_label') or '—'}\n"
            f"Confidence\n{pack.get('confidence')}"
        )
    elif _EVER_CHEAPER.search(q) or "percentile" in q.lower():
        pct = pack.get("historical_percentile")
        prose = (
            f"Current {label}\n{pack.get('current')}\n\n"
            f"Historical Percentile\n{pct}%\n\n"
            f"The company traded below today's valuation during approximately "
            f"{pct}% of observed history.\n\n"
            f"Coverage\n{(pack.get('coverage') or {}).get('coverage_label') or '—'}\n"
            f"Confidence\n{pack.get('confidence')}"
        )
    else:
        # Default: "Is X expensive?"
        regime = pack.get("regime") or (regimes_for(ticker, metric=m).get("regime"))
        max_med = (pack.get("max_window") or {}).get("median")
        prose = (
            f"Current {label}\n{pack.get('current')}\n\n"
            f"10Y Median\n{pack.get('median')}\n\n"
            f"MAX Median\n{max_med}\n\n"
            f"Historical Percentile\n{pack.get('historical_percentile')}%\n\n"
            f"Valuation Regime\n{regime}\n\n"
            f"Premium to 10Y median\n{pack.get('premium_to_median_pct')}%\n\n"
            f"Coverage\n{(pack.get('coverage') or {}).get('coverage_label') or '—'}\n"
            f"Confidence\n{pack.get('confidence')}"
        )

    return {
        "ok": True,
        "symbol": ticker,
        "question": question,
        "answer": prose,
        "metric": m,
        "pack": {
            "current": pack.get("current"),
            "median": pack.get("median"),
            "historical_percentile": pack.get("historical_percentile"),
            "regime": pack.get("regime"),
            "confidence": pack.get("confidence"),
            "coverage": pack.get("coverage"),
        },
        "engine": ENGINE_CODE,
        "version": VERSION,
    }
