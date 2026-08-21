"""The zero-defect checks, extracted from the 28-minute acceptance suite.

`core_platform_acceptance` scores 500 cases and gates on two separate things: an
overall score of at least 98%, and every defect counter at zero. The second is
what protects a release — a 98% score with a hallucination in it is still a
release block — and it is currently reachable only by paying 28.7 minutes for
the first.

This runs the defect-bearing cases and asserts the counters are zero. The score
threshold stays in the long suite, which moves to nightly.

Report-only
-----------
Nothing here blocks a merge or a deployment. It exists to be watched while the
underlying defects are remediated, and to be wired into a required gate later,
by a separate decision.

Provisional section mapping
---------------------------
The mapping below is read out of `core_platform_acceptance_v1.evaluate_case` and
is **provisional until an accountable product owner approves it**. It is
derived, not designed: it says where the flags are raised today, not where they
ought to be raised.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

#: Where each defect flag is actually raised in evaluate_case.
#:
#: hallucination      only in J_impossible - `no_honest_uncertainty` when the
#:                    answer carries no uncertainty marker, `fabricated_specifics`
#:                    when it invents numbers without hedging
#: metadata_error     only in A_company_identity and I_metadata
#: wrong_entity       section-independent: any case carrying a ticker whose
#:                    resolved identity disagrees with the claim
#: wrong_sector       section-independent, same path
#: cross_industry     section-independent, via validate_text
#:
#: PROVISIONAL — needs the suite owner's sign-off.
DEFECT_SECTIONS: Dict[str, Optional[List[str]]] = {
    "hallucination": ["J_impossible"],
    "metadata_error": ["A_company_identity", "I_metadata"],
    # None means "not confined to a section" - these fire wherever a case
    # resolves an identity, so they cannot be extracted by section filter.
    "wrong_entity": None,
    "wrong_sector": None,
    "cross_industry_leakage": None,
    "cross_engine_leakage": None,
    "recommendation_leakage": ["E_investment"],
}

#: The defects this extract is required to protect. Ordered by the register:
#: hallucinations are live at 4, entity correctness is the other P0.
REQUIRED_DEFECTS = ("hallucination", "wrong_entity")

MISSING_PROVIDER_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def provider_configured() -> bool:
    """Whether any editorial provider credential is present."""
    return any((os.environ.get(name) or "").strip() for name in MISSING_PROVIDER_ENV)


def sections_for(defects: Optional[List[str]] = None) -> Optional[List[str]]:
    """Sections needed to exercise these defects, or None if unconfinable.

    Returning None matters: wrong_entity is raised wherever a case resolves an
    identity, so a section-filtered run cannot claim to cover it. Saying so is
    the difference between an extract that protects the property and one that
    only looks like it does.
    """
    wanted = list(defects or REQUIRED_DEFECTS)
    sections: List[str] = []
    for defect in wanted:
        mapped = DEFECT_SECTIONS.get(defect, None)
        if mapped is None:
            return None
        sections.extend(mapped)
    return sorted(set(sections))


def select_cases(cases: List[Dict[str, Any]], defects: Optional[List[str]] = None,
                 per_section: Optional[int] = None) -> List[Dict[str, Any]]:
    """The cases that can raise the named defects.

    When a defect is not section-confined, every case that resolves an identity
    is kept - a filtered subset would under-report it.
    """
    sections = sections_for(defects)
    if sections is None:
        chosen = [c for c in cases if c.get("ticker")]
        confined = sections_for([d for d in (defects or REQUIRED_DEFECTS)
                                 if DEFECT_SECTIONS.get(d) is not None]) or []
        for case in cases:
            if case.get("section") in confined and case not in chosen:
                chosen.append(case)
    else:
        chosen = [c for c in cases if c.get("section") in sections]

    if per_section:
        capped: List[Dict[str, Any]] = []
        seen: Dict[str, int] = {}
        for case in chosen:
            section = str(case.get("section"))
            if seen.get(section, 0) >= per_section:
                continue
            seen[section] = seen.get(section, 0) + 1
            capped.append(case)
        return capped
    return chosen


def summarise(results: List[Dict[str, Any]], *,
              defects: Optional[List[str]] = None,
              provider_ok: Optional[bool] = None) -> Dict[str, Any]:
    """Counters only. No score, no threshold, no pass rate.

    A missing provider makes the outcome NOT_RUN rather than a score of zero.
    Reporting fallback output as a product result is how a configuration problem
    becomes a quality metric.
    """
    wanted = list(defects or REQUIRED_DEFECTS)
    provider_ok = provider_configured() if provider_ok is None else provider_ok

    counts = {d: 0 for d in wanted}
    offenders: Dict[str, List[Dict[str, Any]]] = {d: [] for d in wanted}
    for result in results:
        flags = result.get("flags") or {}
        # Labels are the second source. evaluate_case sets both, but a result
        # carrying labels and no flags would otherwise read as zero defects
        # while the category breakdown showed the defect - two views of one run
        # disagreeing, with the quieter one winning.
        from ask_product_test.routing_failure_taxonomy import categorise
        labelled = {categorise(l) for l in (result.get("failed") or [])}
        for defect in wanted:
            if flags.get(defect) or defect in labelled:
                counts[defect] += 1
                offenders[defect].append({
                    "id": result.get("id"),
                    "section": result.get("section"),
                    "question": result.get("question"),
                    "failed": result.get("failed"),
                    "answer_excerpt": str(result.get("answer") or "")[:500],
                })

    unconfinable = [d for d in wanted if DEFECT_SECTIONS.get(d) is None]
    if not provider_ok:
        decision = "NOT_RUN"
        reason = ("no editorial provider configured; answers are template "
                  "fallback and cannot be scored as product behaviour")
    elif not results:
        decision = "NOT_RUN"
        reason = "no cases evaluated"
    else:
        decision = "PASS" if all(v == 0 for v in counts.values()) else "FAIL"
        reason = None

    return {
        "suite": "zero_defect_extract",
        "report_only": True,
        "blocks_merge": False,
        "blocks_deployment": False,
        "section_mapping": "PROVISIONAL — awaiting product owner approval",
        "provider_configured": provider_ok,
        "decision": decision,
        "reason": reason,
        "cases_evaluated": len(results),
        "defects": counts,
        "offenders": {d: offenders[d][:20] for d in wanted},
        "not_section_confined": unconfinable,
        "coverage_note": (
            f"{unconfinable} are raised wherever a case resolves an identity, so "
            "this extract keeps every identity-bearing case rather than filtering "
            "by section" if unconfinable else None),
    }
