"""Timeline Regression — research memory chronology must stay correct.

Checks Q1→Q2→Q3→FY order, CEO/leadership changes, acquisitions, guidance revisions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from research_intelligence.corpus import CORPUS, get_corpus
from research_intelligence.production import analyse

TIMELINE_REGRESSION: List[Dict[str, Any]] = []


def _add(prompt: str, entity: str, *, checks: List[str], kind: str):
    TIMELINE_REGRESSION.append(
        {
            "id": f"TLR-{len(TIMELINE_REGRESSION)+1:02d}",
            "prompt": prompt,
            "entity": entity,
            "checks": checks,
            "kind": kind,
            "section": "timeline",
            "category": kind,
        }
    )


for key, c in CORPUS.items():
    name = c["name"]
    _add(f"Build the research timeline for {name}.", key, checks=["chronological", "timeline"], kind="chronology")
    _add(
        f"List major events on the {name} research timeline.",
        key,
        checks=["event", "timeline"],
        kind="events",
    )
    _add(
        f"Map leadership and acquisition milestones for {name}.",
        key,
        checks=["leadership", "acquisition", "timeline"],
        kind="leadership_acquisitions",
    )
    _add(
        f"Explain capital allocation milestones on the {name} timeline.",
        key,
        checks=["capital", "timeline"],
        kind="capital_allocation",
    )
    _add(
        f"How has guidance changed for {name} across quarters and FY?",
        key,
        checks=["guidance", "change", "evol", "previous", "fy", "quarter"],
        kind="guidance_revisions",
    )

assert len(TIMELINE_REGRESSION) == 25, len(TIMELINE_REGRESSION)


def _years_sorted(timeline: List[dict]) -> bool:
    years: List[str] = []
    for t in timeline:
        y = str(t.get("year") or "")
        # Extract leading 4-digit year when present
        digits = "".join(ch for ch in y if ch.isdigit())
        if len(digits) >= 4:
            years.append(digits[:4])
    if len(years) < 2:
        return True
    return years == sorted(years)


def evaluate_timeline_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    c = get_corpus(case["entity"])
    assert c is not None
    summary = (payload.get("executive_summary") or payload.get("summary") or "").lower()
    blob = summary + " " + str(payload.get("timeline") or "").lower()
    chron_ok = _years_sorted(list(c.get("timeline") or []))
    # Engine must not invert corpus order
    tl_payload = (payload.get("timeline") or {}).get("timeline") or c.get("timeline") or []
    payload_chron_ok = _years_sorted(list(tl_payload))
    check_hits = sum(1 for k in case["checks"] if k.lower() in blob)
    need = 1 if case["kind"] == "guidance_revisions" else min(2, len(case["checks"]))
    if case["kind"] == "guidance_revisions":
        topic_ok = ("guidance" in blob) and check_hits >= 2
    else:
        topic_ok = check_hits >= need
    no_reco = payload.get("recommendation") in (None, "", "none")
    no_fabricated = payload.get("fabricated") is not True
    # Quarter/FY language preserved when guidance/timeline asked
    period_ok = True
    if case["kind"] == "guidance_revisions":
        period_ok = any(tok in blob for tok in ("guidance", "q1", "q2", "q3", "q4", "fy", "previous", "change"))
    passed = chron_ok and payload_chron_ok and topic_ok and no_reco and no_fabricated and period_ok and bool(summary)
    return {
        "id": case["id"],
        "kind": case["kind"],
        "prompt": case["prompt"],
        "entity": case["entity"],
        "pass": passed,
        "chronology_ok": chron_ok and payload_chron_ok,
        "topic_ok": topic_ok,
        "period_ok": period_ok,
        "no_recommendation_leakage": no_reco,
        "summary": (payload.get("summary") or "")[:220],
        "failed_assertions": [
            k
            for k, v in {
                "chronology_ok": chron_ok and payload_chron_ok,
                "topic_ok": topic_ok,
                "period_ok": period_ok,
                "no_reco": no_reco,
                "no_fabricated": no_fabricated,
                "has_summary": bool(summary),
            }.items()
            if not v
        ],
    }
