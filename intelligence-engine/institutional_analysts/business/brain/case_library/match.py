"""Match assembled evidence to success cases and counter-cases."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt
from institutional_analysts.business.brain.case_library.failures import FAILURE_CASES
from institutional_analysts.business.brain.case_library.successes import SUCCESS_CASES


def _score_case(case: dict[str, Any], blob: str) -> int:
    signals = case.get("signals") or ()
    return sum(1 for s in signals if s in blob)


def match_cases(
    evidence: dict[str, Any],
    frameworks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fw = frameworks or {}
    moat = fw.get("moat") or {}
    capital = fw.get("capital_allocation") or {}
    risks = fw.get("risks") or {}
    blob = blob_of(
        evidence.get("business_model"),
        evidence.get("advantages"),
        evidence.get("brand"),
        evidence.get("pricing_power"),
        evidence.get("capital_allocation"),
        evidence.get("business_risks"),
        evidence.get("growth_opportunities"),
        moat.get("sources"),
        capital.get("assessment"),
        risks.get("primary_risks"),
    )

    scored_success = sorted(
        ((c, _score_case(c, blob)) for c in SUCCESS_CASES),
        key=lambda x: x[1],
        reverse=True,
    )
    scored_fail = sorted(
        ((c, _score_case(c, blob)) for c in FAILURE_CASES),
        key=lambda x: x[1],
        reverse=True,
    )

    top_success = [
        {
            "id": c["id"],
            "name": c["name"],
            "drivers": list(c.get("drivers") or []),
            "chain": list(c.get("chain") or []),
            "outcome": c.get("outcome"),
            "lessons": list(c.get("lessons") or [])[:2],
            "match_score": score,
        }
        for c, score in scored_success
        if score > 0
    ][:3]
    top_fail = [
        {
            "id": c["id"],
            "name": c["name"],
            "drivers": list(c.get("drivers") or []),
            "chain": list(c.get("chain") or []),
            "outcome": c.get("outcome"),
            "lessons": list(c.get("lessons") or [])[:2],
            "match_score": score,
        }
        for c, score in scored_fail
        if score > 0
    ][:3]

    # Ensure at least one illustrative pair for institutional tone
    if not top_success:
        c = SUCCESS_CASES[0]
        top_success = [
            {
                "id": c["id"],
                "name": c["name"],
                "drivers": list(c["drivers"]),
                "chain": list(c["chain"]),
                "outcome": c["outcome"],
                "lessons": list(c["lessons"])[:2],
                "match_score": 0,
            }
        ]
    if not top_fail:
        c = FAILURE_CASES[0]
        top_fail = [
            {
                "id": c["id"],
                "name": c["name"],
                "drivers": list(c["drivers"]),
                "chain": list(c["chain"]),
                "outcome": c["outcome"],
                "lessons": list(c["lessons"])[:2],
                "match_score": 0,
            }
        ]

    best_success = top_success[0]
    best_fail = top_fail[0]
    durability = str(moat.get("durability") or "")
    capital_txt = txt(capital.get("assessment") or evidence.get("capital_allocation")).lower()

    if "disciplin" in capital_txt or "conservative" in capital_txt:
        resemblance = (
            f"Capital allocation discipline resembles {best_success['name']} more than "
            f"{'General Electric' if best_fail['id'] != 'general_electric' else best_fail['name']}."
        )
    elif durability in {"Weak", "Declining"} or any(
        k in blob for k in ("disrupt", "ecosystem", "market share")
    ):
        resemblance = (
            f"On present signals, competitive dynamics resemble {best_fail['name']} more than "
            f"{best_success['name']} — share or brand without reinforcing advantages is perishable."
        )
    else:
        resemblance = (
            f"Franchise characteristics currently resemble {best_success['name']} more than "
            f"{best_fail['name']}, provided capital discipline and advantage reinforcement continue."
        )

    lessons: list[str] = []
    for row in top_success[:2] + top_fail[:2]:
        for lesson in row.get("lessons") or []:
            if lesson not in lessons:
                lessons.append(lesson)
        if len(lessons) >= 6:
            break

    return {
        "success_cases": top_success,
        "counter_cases": top_fail,
        "resemblance": resemblance,
        "lessons_from_cases": lessons[:6],
        "primary_success_analogue": best_success["name"],
        "primary_failure_analogue": best_fail["name"],
    }
