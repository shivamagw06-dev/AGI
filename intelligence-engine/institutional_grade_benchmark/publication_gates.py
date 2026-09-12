"""Research publication gates — buy-side PM bar for institutional notes.

Derived from the Reliance PM review (67/100 scaffold).
A note may be a good draft; it must not publish until these gates pass.
Target: 85+/100 publication-ready research.
"""

from __future__ import annotations

from typing import Any, Optional

GATE_SPEC_VERSION = "ib-pub-gates-v1.0.0"
PUBLICATION_READY_SCORE = 85
SCAFFOLD_FLOOR_SCORE = 60

# Seven requirements a buy-side PM would demand before publication
PUBLICATION_GATES = (
    {
        "id": "G1_investment_thesis",
        "name": "Investment Thesis",
        "requirement": "3–5 evidence-backed thesis bullets (buy/sell because…)",
        "blocks_publication": True,
    },
    {
        "id": "G2_key_financials",
        "name": "Key Financial Metrics",
        "requirement": "5-year history + TTM (revenue, EBITDA, ROCE/ROE, debt, FCF, margins)",
        "blocks_publication": True,
    },
    {
        "id": "G3_segment_economics",
        "name": "Segment Economics",
        "requirement": "Quantified segment mix/growth for material businesses",
        "blocks_publication": True,
    },
    {
        "id": "G4_valuation",
        "name": "Valuation",
        "requirement": "SOTP and/or peers + sensitivity; not stance-only",
        "blocks_publication": True,
    },
    {
        "id": "G5_decision_triggers",
        "name": "Decision Triggers",
        "requirement": "Explicit upgrade-to-BUY and downgrade-to-SELL conditions",
        "blocks_publication": True,
    },
    {
        "id": "G6_evidence_links",
        "name": "Evidence Links",
        "requirement": "Primary filings linked for every material claim (AR/QR/IR/exchange)",
        "blocks_publication": True,
    },
    {
        "id": "G7_contradiction_check",
        "name": "Contradiction Check",
        "requirement": "Single recommendation only; reject SELL vs Neutral conflicts",
        "blocks_publication": True,
    },
)

# Optional density enhancers (do not alone unblock publication)
ENHANCERS = (
    {
        "id": "E1_scenario_probabilities",
        "name": "Scenario Probabilities",
        "requirement": "Bull/Base/Bear with explicit probabilities summing ~100%",
    },
    {
        "id": "E2_numeric_density",
        "name": "Numeric Density",
        "requirement": "Material paragraphs contain quantified evidence",
    },
)


def evaluate_publication_readiness(note: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Evaluate a research-note payload against PM publication gates.

    Expected note keys (all optional — missing ⇒ fail):
      thesis_bullets: list[str]
      financial_metrics: dict | list
      segment_economics: dict | list
      valuation: dict (needs sotp and/or peers / multiples)
      decision_triggers: dict with upgrade_to_buy / downgrade_to_sell
      evidence_links: list[{claim, source_type, uri|filing_id}]
      primary_filings_count: int
      recommendations: list[str]  # all stance labels found in the pack
      recommendation: str         # canonical single stance
      scenario_probabilities: dict
      pm_area_scores: dict[str, float]  # optional external PM scores /10
      fabricated_numbers: bool
    """
    body = dict(note or {})
    results: list[dict[str, Any]] = []

    thesis = body.get("thesis_bullets") or []
    results.append(
        _gate(
            "G1_investment_thesis",
            isinstance(thesis, list) and 3 <= len(thesis) <= 8 and all(str(x).strip() for x in thesis),
            detail=f"thesis_bullets={len(thesis) if isinstance(thesis, list) else 0}",
        )
    )

    fins = body.get("financial_metrics")
    fin_ok = _nonempty_structured(fins) and bool(body.get("has_ttm") or body.get("has_5y_history"))
    # Also accept explicit metric keys
    if isinstance(fins, dict):
        needed = {"revenue", "ebitda", "net_debt", "fcf", "roce", "roe", "margins"}
        present = {k.lower() for k in fins.keys()}
        if len(needed & present) >= 4:
            fin_ok = True
    results.append(_gate("G2_key_financials", fin_ok, detail="financial_metrics density"))

    segs = body.get("segment_economics")
    seg_ok = _nonempty_structured(segs)
    if isinstance(segs, dict):
        seg_ok = seg_ok and any(
            isinstance(v, dict) and any(x in v for x in ("revenue", "ebitda", "growth", "margin"))
            for v in segs.values()
        )
    results.append(_gate("G3_segment_economics", seg_ok, detail="segment quantification"))

    val = body.get("valuation") if isinstance(body.get("valuation"), dict) else {}
    val_ok = bool(
        val.get("sotp")
        or val.get("peers")
        or val.get("ev_ebitda")
        or val.get("pe")
        or val.get("fcf_yield")
        or val.get("sensitivity")
    )
    # Stance-only fails
    if val.get("stance_only") is True:
        val_ok = False
    results.append(_gate("G4_valuation", val_ok, detail="sotp/peers/multiples required"))

    triggers = body.get("decision_triggers") if isinstance(body.get("decision_triggers"), dict) else {}
    trig_ok = bool(triggers.get("upgrade_to_buy")) and bool(triggers.get("downgrade_to_sell"))
    results.append(_gate("G5_decision_triggers", trig_ok, detail="upgrade/downgrade triggers"))

    links = body.get("evidence_links") or []
    primary = int(body.get("primary_filings_count") or 0)
    if isinstance(links, list):
        primary += sum(
            1
            for x in links
            if isinstance(x, dict)
            and str(x.get("source_type") or "").lower()
            in {"annual_report", "quarterly", "earnings", "exchange", "ir", "filing"}
        )
    ev_ok = primary >= 1 and isinstance(links, list) and len(links) >= 3
    results.append(
        _gate(
            "G6_evidence_links",
            ev_ok,
            detail=f"primary_filings≈{primary} links={len(links) if isinstance(links, list) else 0}",
        )
    )

    recs = []
    if body.get("recommendation"):
        recs.append(str(body.get("recommendation")).strip().upper())
    for r in body.get("recommendations") or []:
        recs.append(str(r).strip().upper())
    # Normalize aliases
    normed = {_norm_stance(r) for r in recs if r}
    # Conflict if both actionable sell and buy/neutral-own language collide as distinct actions
    actionable = {x for x in normed if x in {"BUY", "SELL", "HOLD", "NEUTRAL", "MONITOR"}}
    contradiction = len(actionable) > 1
    # Also explicit flag
    if body.get("has_recommendation_conflict"):
        contradiction = True
    results.append(
        _gate(
            "G7_contradiction_check",
            (not contradiction) and bool(actionable),
            detail=f"stances={sorted(actionable) or ['none']}",
        )
    )

    passed = sum(1 for g in results if g["passed"])
    failed = [g for g in results if not g["passed"]]
    blocking = [g for g in failed if g["blocks_publication"]]

    enhancers = []
    probs = body.get("scenario_probabilities") if isinstance(body.get("scenario_probabilities"), dict) else {}
    prob_sum = sum(float(v) for v in probs.values()) if probs else 0.0
    enhancers.append(
        {
            "id": "E1_scenario_probabilities",
            "passed": bool(probs) and 0.9 <= prob_sum <= 1.1,
            "detail": f"sum={prob_sum:.2f}" if probs else "missing",
        }
    )
    enhancers.append(
        {
            "id": "E2_numeric_density",
            "passed": bool(body.get("numeric_density_ok")),
            "detail": "paragraph-level quantification",
        }
    )

    # Optional PM scores — prefer explicit overall; else equal-weight /10 areas → /100
    pm_scores = body.get("pm_area_scores") if isinstance(body.get("pm_area_scores"), dict) else None
    pm_overall = body.get("pm_overall")
    if pm_overall is not None:
        pm_overall = round(float(pm_overall), 1)
    elif pm_scores:
        vals = [float(v) for v in pm_scores.values()]
        pm_overall = round(10.0 * sum(vals) / len(vals), 1) if vals else None

    publication_allowed = len(blocking) == 0 and not bool(body.get("fabricated_numbers"))
    scaffold_only = not publication_allowed

    return {
        "ok": True,
        "gate_spec_version": GATE_SPEC_VERSION,
        "publication_ready_score_target": PUBLICATION_READY_SCORE,
        "publication_allowed": publication_allowed,
        "scaffold_only": scaffold_only,
        "gates_passed": passed,
        "gates_total": len(PUBLICATION_GATES),
        "blocking_failures": [g["id"] for g in blocking],
        "gates": results,
        "enhancers": enhancers,
        "pm_overall_score": pm_overall,
        "pm_verdict": _pm_verdict(pm_overall, publication_allowed),
        "priority_for_v11": [
            "Evidence attachment gate",
            "Contradiction rejection before note assembly",
            "Financial + valuation density requirements",
            "Decision-trigger template",
            "Block publication until gates pass",
        ],
        "philosophy": (
            "Institutional investors trust 'I don't know' far more than fabricated certainty. "
            "Good first draft. Don't publish it yet — until gates pass."
        ),
    }


def evaluate_reliance_note_as_reviewed() -> dict[str, Any]:
    """Ground-truth evaluation of the Reliance productivity note (PM review)."""
    note = {
        "thesis_bullets": [],  # prose thesis, not 3–5 evidence bullets
        "financial_metrics": {},
        "has_ttm": False,
        "has_5y_history": False,
        "segment_economics": {
            # qualitative only — no revenue/ebitda/growth numbers
            "O2C": {"role": "cash engine"},
            "Retail": {"role": "growth"},
            "Jio": {"role": "platform"},
            "New Energy": {"role": "option"},
        },
        "valuation": {"stance_only": True, "stance": "Neutral"},
        "decision_triggers": {
            # incomplete vs required upgrade_to_buy / downgrade_to_sell lists
        },
        "evidence_links": [],
        "primary_filings_count": 0,
        "recommendations": ["SELL", "NEUTRAL", "MONITOR"],
        "recommendation": "NEUTRAL",
        "has_recommendation_conflict": True,
        "scenario_probabilities": {},
        "numeric_density_ok": False,
        "fabricated_numbers": False,
        "pm_overall": 67.0,
        "pm_area_scores": {
            "business_understanding": 9,
            "structure": 10,
            "institutional_tone": 9,
            "investment_reasoning": 6,
            "financial_analysis": 3,
            "valuation": 3,
            "evidence": 2,
            "actionability": 5,
        },
    }
    out = evaluate_publication_readiness(note)
    out["case_id"] = "IB-PROD-RELIANCE-001"
    out["artifact"] = "docs/research_notes/RELIANCE_INVESTMENT_NOTE.md"
    out["pm_review_doc"] = "docs/research_notes/RELIANCE_PM_REVIEW.md"
    out["expected_pm_overall"] = 67.0
    return out


def _gate(gate_id: str, passed: bool, *, detail: str = "") -> dict[str, Any]:
    meta = next(g for g in PUBLICATION_GATES if g["id"] == gate_id)
    return {
        "id": gate_id,
        "name": meta["name"],
        "requirement": meta["requirement"],
        "passed": bool(passed),
        "blocks_publication": bool(meta["blocks_publication"]),
        "detail": detail,
    }


def _nonempty_structured(value: Any) -> bool:
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, list):
        return len(value) > 0
    return False


def _norm_stance(raw: str) -> str:
    s = raw.upper().replace("-", " ").strip()
    if "BUY" in s and "SELL" not in s:
        return "BUY"
    if "SELL" in s:
        return "SELL"
    if "HOLD" in s:
        return "HOLD"
    if "NEUTRAL" in s:
        return "NEUTRAL"
    if "MONITOR" in s:
        return "MONITOR"
    return s.split()[0] if s else ""


def _pm_verdict(score: Optional[float], publication_allowed: bool) -> str:
    if publication_allowed and score is not None and score >= PUBLICATION_READY_SCORE:
        return "Publication-ready"
    if score is not None and score >= SCAFFOLD_FLOOR_SCORE:
        return "Good first draft. Don't publish it yet."
    if score is not None:
        return "Below institutional scaffold bar"
    return "Gates incomplete — do not publish"
