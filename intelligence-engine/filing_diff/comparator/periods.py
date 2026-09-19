"""Select current vs previous filing periods from FIL output + FDI priors."""

from __future__ import annotations

from typing import Any

from filing_diff.priors import prior_for
from filing_intelligence.history.engine import _period_key
from filing_intelligence.pipeline import analyse_ticker


def load_comparison_context(ticker: str) -> dict[str, Any]:
    fil = analyse_ticker(ticker)
    if not fil.get("found"):
        return {"ticker": ticker.upper(), "found": False}

    period_metrics: dict[str, dict[str, Any]] = {}
    period_sources: dict[str, dict[str, str]] = {}
    for s in (fil.get("history") or {}).get("series") or []:
        metric = s["metric"]
        for period, value in (s.get("points") or {}).items():
            period_metrics.setdefault(period, {})[metric] = value
            period_sources.setdefault(period, {})[metric] = (s.get("sources") or {}).get(period) or ""

    qual_by_period: dict[str, dict[str, Any]] = {}
    for f in fil.get("facts") or []:
        p = f.get("period") or ""
        # skip multi-period compiled labels for qualitative bucketing
        if "-" in p and p.startswith("FY"):
            continue
        bucket = qual_by_period.setdefault(
            p,
            {
                "management": {},
                "risks": set(),
                "guidance_status": None,
                "notes": set(),
                "capital": set(),
                "segments": set(),
                "governance": set(),
                "ownership": set(),
                "docs": set(),
                "text_markers": {},
            },
        )
        bucket["docs"].add(f.get("doc_id") or "")
        cat = f.get("category")
        if cat == "management":
            bucket["management"][f.get("metric")] = f.get("value")
        elif cat == "risk":
            bucket["risks"].add(f.get("metric"))
        elif f.get("metric") == "Guidance_Status":
            bucket["guidance_status"] = f.get("value")
        elif cat == "note":
            bucket["notes"].add(f.get("metric"))
        elif cat == "capital":
            bucket["capital"].add(f.get("metric"))
        elif cat == "segment":
            bucket["segments"].add(str(f.get("value")))
        elif cat == "governance":
            bucket["governance"].add(f.get("metric"))
        elif cat == "ownership":
            bucket["ownership"].add(f.get("metric"))

    prior = prior_for(fil.get("ticker") or ticker)
    if prior:
        pp = prior["period"]
        # merge prior financials (do not overwrite FIL points)
        for m, v in (prior.get("financials") or {}).items():
            period_metrics.setdefault(pp, {}).setdefault(m, v)
            period_sources.setdefault(pp, {}).setdefault(m, prior.get("doc_id") or "fdi_prior")
        qual_by_period[pp] = {
            "management": dict(prior.get("management") or {}),
            "risks": set(prior.get("risks") or []),
            "guidance_status": prior.get("guidance_status"),
            "notes": set(prior.get("notes") or []),
            "capital": set(prior.get("capital") or []),
            "segments": set(prior.get("segments") or []),
            "governance": set(prior.get("governance") or []),
            "ownership": set(prior.get("ownership") or []),
            "docs": {prior.get("doc_id") or "fdi_prior"},
            "text_markers": prior.get("text_markers") or {},
            "as_of": prior.get("as_of"),
            "evidence_tier": prior.get("evidence_tier", 2),
        }

    periods = sorted(period_metrics.keys(), key=_period_key)
    current_period = periods[-1] if periods else None
    previous_period = periods[-2] if len(periods) >= 2 else None

    # Prefer immediate prior quarter snapshot when available (QoQ institutional compare)
    if prior and current_period and _period_key(prior["period"]) < _period_key(current_period):
        previous_period = prior["period"]

    qual_serial = {}
    for p, b in qual_by_period.items():
        qual_serial[p] = {
            **b,
            "risks": sorted(b["risks"]),
            "notes": sorted(b["notes"]),
            "capital": sorted(b["capital"]),
            "segments": sorted(b["segments"]),
            "governance": sorted(b["governance"]),
            "ownership": sorted(b["ownership"]),
            "docs": sorted(x for x in b["docs"] if x),
        }

    return {
        "ticker": fil.get("ticker") or ticker.upper(),
        "found": True,
        "fil": fil,
        "periods": periods,
        "current_period": current_period,
        "previous_period": previous_period,
        "period_metrics": period_metrics,
        "period_sources": period_sources,
        "qual_by_period": qual_serial,
        "documents": fil.get("documents") or [],
        "comparison_pair": {
            "current": current_period,
            "previous": previous_period,
            "mode": "quarter_on_quarter" if previous_period and previous_period.startswith("Q") else "period_on_period",
        },
    }
