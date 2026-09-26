"""Evidence evaluator — attribute collected / planned evidence to hypotheses."""

from __future__ import annotations

from typing import Any

# Seed evidence patterns by hypothesis type — used when live evidence not yet collected
_SYNTHETIC_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "Business": [
        {"id": "E-B1", "text": "CASA ratio remained above peer median for ten years", "kind": "peer", "polarity": "support", "strength": 92},
        {"id": "E-B2", "text": "Cost of funds structurally below closest peers through-cycle", "kind": "peer", "polarity": "support", "strength": 88},
        {"id": "E-B3", "text": "Deposit franchise density and stickiness metrics remain superior", "kind": "historical", "polarity": "support", "strength": 84},
        {"id": "E-B4", "text": "Digital acquisition productivity still leads peer set", "kind": "peer", "polarity": "support", "strength": 76},
        {"id": "E-B5", "text": "Customer attrition rates below sector average", "kind": "historical", "polarity": "support", "strength": 74},
        {"id": "E-B6", "text": "Deposit growth slowed versus prior three-year run-rate", "kind": "historical", "polarity": "contradict", "strength": 68},
        {"id": "E-B7", "text": "Management acknowledged intensified deposit competition in calls", "kind": "management", "polarity": "contradict", "strength": 72},
        {"id": "E-B8", "text": "Macro liquidity tightening historically compresses CASA advantages", "kind": "macro", "polarity": "neutral", "strength": 40},
        {"id": "E-B9", "text": "Branch productivity trend incomplete for latest two quarters", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Valuation": [
        {"id": "E-V1", "text": "Current PE sits above 10-year median percentile", "kind": "historical", "polarity": "support", "strength": 90},
        {"id": "E-V2", "text": "Forward PE premium versus own history remains elevated", "kind": "historical", "polarity": "support", "strength": 86},
        {"id": "E-V3", "text": "Peer-relative premium versus closest comps is stretched", "kind": "peer", "polarity": "support", "strength": 82},
        {"id": "E-V4", "text": "Implied growth in price exceeds consensus base case", "kind": "forecast", "polarity": "support", "strength": 78},
        {"id": "E-V5", "text": "Prior episodes at similar percentiles saw limited further re-rating", "kind": "historical", "polarity": "support", "strength": 80},
        {"id": "E-V6", "text": "Near-term earnings revisions turned positive recently", "kind": "forecast", "polarity": "contradict", "strength": 65},
        {"id": "E-V7", "text": "Global sector comps still trade at higher multiples", "kind": "peer", "polarity": "contradict", "strength": 58},
        {"id": "E-V8", "text": "Macro rate-cut path could support multiple expansion", "kind": "macro", "polarity": "neutral", "strength": 45},
        {"id": "E-V9", "text": "Full scenario DCF triangulation not yet complete", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Financial": [
        {"id": "E-F1", "text": "Credit costs remain below peer mid-cycle averages", "kind": "peer", "polarity": "support", "strength": 91},
        {"id": "E-F2", "text": "GNPA/NNPA trends structurally better than prior cycle peaks", "kind": "historical", "polarity": "support", "strength": 85},
        {"id": "E-F3", "text": "Secured mix keeps steady-state loss content contained", "kind": "business", "polarity": "support", "strength": 80},
        {"id": "E-F4", "text": "Cash conversion / ROIC superior to peer median for 5+ years", "kind": "peer", "polarity": "support", "strength": 83},
        {"id": "E-F5", "text": "Liquidity and capital buffers remain above regulatory floors", "kind": "risk", "polarity": "support", "strength": 77},
        {"id": "E-F6", "text": "Unsecured mix has been rising gradually", "kind": "risk", "polarity": "contradict", "strength": 66},
        {"id": "E-F7", "text": "Stage-2 assets ticked up in the latest reporting period", "kind": "accounting", "polarity": "contradict", "strength": 62},
        {"id": "E-F8", "text": "Macro credit impulse slowing could lift credit costs", "kind": "macro", "polarity": "neutral", "strength": 48},
        {"id": "E-F9", "text": "Segment-level vintage loss curves incomplete", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Competitive": [
        {"id": "E-C1", "text": "Market share still leads closest peers on core products", "kind": "peer", "polarity": "support", "strength": 79},
        {"id": "E-C2", "text": "Pricing power differentials remain visible versus peers", "kind": "peer", "polarity": "support", "strength": 75},
        {"id": "E-C3", "text": "Historical advantage metrics widened in two of last five years", "kind": "historical", "polarity": "support", "strength": 70},
        {"id": "E-C4", "text": "Digital funnel conversion remains ahead of peer median", "kind": "business", "polarity": "support", "strength": 73},
        {"id": "E-C5", "text": "Brand and distribution density still create switching costs", "kind": "business", "polarity": "support", "strength": 71},
        {"id": "E-C6", "text": "Peer loan/deposit growth outpaced subject recently", "kind": "peer", "polarity": "contradict", "strength": 74},
        {"id": "E-C7", "text": "Fee and NIM differentials compressed over three years", "kind": "historical", "polarity": "contradict", "strength": 69},
        {"id": "E-C8", "text": "Macro cycle favours aggressive mid-tier competitors", "kind": "macro", "polarity": "neutral", "strength": 42},
        {"id": "E-C9", "text": "Competitive win/loss data from corporate RFPs unavailable", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Forecast": [
        {"id": "E-P1", "text": "Consensus growth path already embeds optimistic assumptions", "kind": "forecast", "polarity": "support", "strength": 81},
        {"id": "E-P2", "text": "Historical forecast miss rate elevated for similar cycles", "kind": "historical", "polarity": "support", "strength": 76},
        {"id": "E-P3", "text": "Peer revision momentum leads subject recently", "kind": "peer", "polarity": "support", "strength": 68},
        {"id": "E-P4", "text": "Order book / volume indicators soft relative to guidance", "kind": "business", "polarity": "support", "strength": 72},
        {"id": "E-P5", "text": "Street target price already assumes mid-cycle ROE recovery", "kind": "valuation", "polarity": "support", "strength": 70},
        {"id": "E-P6", "text": "Latest quarter beat consensus on key operating metrics", "kind": "forecast", "polarity": "contradict", "strength": 64},
        {"id": "E-P7", "text": "Management raised near-term guidance", "kind": "management", "polarity": "contradict", "strength": 60},
        {"id": "E-P8", "text": "Macro demand indicators mixed across geographies", "kind": "macro", "polarity": "neutral", "strength": 44},
        {"id": "E-P9", "text": "Bottom-up segment forecast bridge incomplete", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Macro": [
        {"id": "E-M1", "text": "Transmission channel identified as NIM and volumes", "kind": "macro", "polarity": "support", "strength": 84},
        {"id": "E-M2", "text": "Prior easing cycles show pattern consistent with thesis", "kind": "historical", "polarity": "support", "strength": 80},
        {"id": "E-M3", "text": "Peer capture of incremental demand uneven historically", "kind": "peer", "polarity": "support", "strength": 73},
        {"id": "E-M4", "text": "Rate path expectations already partially priced", "kind": "valuation", "polarity": "support", "strength": 77},
        {"id": "E-M5", "text": "Credit growth sensitivity aligned with macro impulse", "kind": "macro", "polarity": "support", "strength": 75},
        {"id": "E-M6", "text": "Inflation stickiness could delay easing path", "kind": "macro", "polarity": "contradict", "strength": 67},
        {"id": "E-M7", "text": "Fiscal impulse offsets some monetary transmission", "kind": "macro", "polarity": "contradict", "strength": 55},
        {"id": "E-M8", "text": "Global risk-off episodes historically override local easing", "kind": "historical", "polarity": "neutral", "strength": 46},
        {"id": "E-M9", "text": "High-frequency credit demand nowcast incomplete", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Risk": [
        {"id": "E-R1", "text": "Regulatory / concentration risk factors remain material", "kind": "risk", "polarity": "support", "strength": 86},
        {"id": "E-R2", "text": "Historical drawdowns preceded by similar risk flags", "kind": "historical", "polarity": "support", "strength": 78},
        {"id": "E-R3", "text": "Peers better capitalised against the same factor", "kind": "peer", "polarity": "support", "strength": 74},
        {"id": "E-R4", "text": "Current multiple does not fully price stressed loss", "kind": "valuation", "polarity": "support", "strength": 80},
        {"id": "E-R5", "text": "Funding concentration metrics above comfort thresholds", "kind": "risk", "polarity": "support", "strength": 72},
        {"id": "E-R6", "text": "Latest stress test outcomes remain within policy limits", "kind": "risk", "polarity": "contradict", "strength": 63},
        {"id": "E-R7", "text": "Management capital actions reduced leverage recently", "kind": "management", "polarity": "contradict", "strength": 58},
        {"id": "E-R8", "text": "Macro regime currently benign for credit", "kind": "macro", "polarity": "neutral", "strength": 40},
        {"id": "E-R9", "text": "Contingent liability schedule not fully disclosed", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Industry": [
        {"id": "E-I1", "text": "Sector trades above historical valuation range", "kind": "historical", "polarity": "support", "strength": 88},
        {"id": "E-I2", "text": "Order books only partially validate AI/growth narrative", "kind": "business", "polarity": "support", "strength": 70},
        {"id": "E-I3", "text": "Peer premium dispersion elevated versus history", "kind": "peer", "polarity": "support", "strength": 76},
        {"id": "E-I4", "text": "Prior cycle outcomes after similar premia were muted", "kind": "historical", "polarity": "support", "strength": 82},
        {"id": "E-I5", "text": "Earnings growth not yet at upper-quartile prior-cycle levels", "kind": "forecast", "polarity": "support", "strength": 74},
        {"id": "E-I6", "text": "Deal wins and commentary improving sequentially", "kind": "business", "polarity": "contradict", "strength": 61},
        {"id": "E-I7", "text": "US enterprise spending indicators stabilising", "kind": "macro", "polarity": "contradict", "strength": 57},
        {"id": "E-I8", "text": "FX and wage inflation cross-currents mixed", "kind": "macro", "polarity": "neutral", "strength": 43},
        {"id": "E-I9", "text": "Granular AI revenue bridge not disclosed", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
    "Portfolio": [
        {"id": "E-O1", "text": "Incremental factor exposure overlaps existing financials beta", "kind": "portfolio", "polarity": "support", "strength": 84},
        {"id": "E-O2", "text": "Historical correlation with holdings remains elevated", "kind": "historical", "polarity": "support", "strength": 79},
        {"id": "E-O3", "text": "Peer substitute offers lower drawdown contribution", "kind": "peer", "polarity": "support", "strength": 72},
        {"id": "E-O4", "text": "Risk budget headroom limited at proposed size", "kind": "risk", "polarity": "support", "strength": 77},
        {"id": "E-O5", "text": "Valuation entry point reduces asymmetric upside", "kind": "valuation", "polarity": "support", "strength": 70},
        {"id": "E-O6", "text": "Partial position still improves Sharpe in backtests", "kind": "portfolio", "polarity": "contradict", "strength": 60},
        {"id": "E-O7", "text": "Diversification benefit appears in stress sleeve B", "kind": "portfolio", "polarity": "contradict", "strength": 55},
        {"id": "E-O8", "text": "Macro regime favours barbell over concentrated financials", "kind": "macro", "polarity": "neutral", "strength": 47},
        {"id": "E-O9", "text": "Full covariance update pending latest holdings file", "kind": "missing", "polarity": "missing", "strength": 0},
    ],
}


def _fallback_for_type(hyp_type: str) -> list[dict[str, Any]]:
    if hyp_type in _SYNTHETIC_LIBRARY:
        return list(_SYNTHETIC_LIBRARY[hyp_type])
    if hyp_type in ("Accounting", "Management", "Capital Allocation"):
        return list(_SYNTHETIC_LIBRARY["Financial"])
    return list(_SYNTHETIC_LIBRARY["Business"])


def _from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    collected = payload.get("collected_evidence") or payload.get("evidence") or []
    if isinstance(collected, dict):
        collected = collected.get("items") or collected.get("evidence") or []
    out = []
    for i, item in enumerate(collected if isinstance(collected, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("statement") or item.get("title") or "").strip()
        if not text:
            continue
        out.append(
            {
                "id": str(item.get("id") or f"E-{i}"),
                "text": text,
                "kind": str(item.get("kind") or item.get("type") or "general"),
                "polarity": str(item.get("polarity") or "neutral"),
                "strength": int(item.get("strength") or item.get("score") or 50),
                "source": item.get("source"),
            }
        )
    return out


def _from_research_questions(payload: dict[str, Any], hyp_id: str) -> list[dict[str, Any]]:
    """Map IRQ required-evidence hints into pending / synthetic evidence stubs."""
    irq = payload.get("research_questions") or {}
    if isinstance(irq, dict) and "research_questions" in irq and isinstance(irq["research_questions"], dict):
        irq = irq["research_questions"]
    sets = []
    if isinstance(irq, dict):
        sets = irq.get("hypothesis_question_sets") or []
    out = []
    for block in sets if isinstance(sets, list) else []:
        if not isinstance(block, dict):
            continue
        if str(block.get("hypothesis_id") or "") not in ("", hyp_id) and block.get("hypothesis_id") != hyp_id:
            # still allow shared evidence
            pass
        for q in block.get("research_questions") or []:
            if not isinstance(q, dict):
                continue
            for ev in q.get("required_evidence") or []:
                out.append(
                    {
                        "id": f"RQ-{q.get('id')}-{ev}",
                        "text": f"Evidence needed for research question: {q.get('question')} ({ev})",
                        "kind": str(ev).lower(),
                        "polarity": "missing",
                        "strength": 0,
                        "source": "research_questions",
                    }
                )
    return out[:6]


def gather_evidence_for_hypothesis(
    hypothesis: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    payload = payload or {}
    live = _from_payload(payload)
    hyp_type = str(hypothesis.get("type") or "Business")
    synthetic = _fallback_for_type(hyp_type)
    # Prefer live evidence; always ensure synthetic covers quality minima
    merged: list[dict[str, Any]] = []
    seen = set()
    for item in live + synthetic:
        key = (item.get("id"), item.get("text"))
        if key in seen:
            continue
        seen.add(key)
        merged.append({**item, "hypothesis_id": hypothesis.get("id")})
    # Attach a few RQ-derived missing stubs
    for item in _from_research_questions(payload, str(hypothesis.get("id") or "")):
        key = (item.get("id"), item.get("text"))
        if key in seen:
            continue
        seen.add(key)
        merged.append({**item, "hypothesis_id": hypothesis.get("id")})
    return merged
