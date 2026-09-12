"""Institutional answer contract — Final View shape; never BUY/SELL as the answer."""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional, Sequence

from institutional_stress_tests.schema import FINAL_VIEW_KEYS, REQUIRED_QUESTIONS


_BUY_SELL_RE = re.compile(
    r"\b(buy|sell|strong\s+buy|strong\s+sell|accumulate|reduce)\b",
    re.IGNORECASE,
)
_BARE_BUY_KOTAK = re.compile(
    r"\bbuy\s+kotak\b|\bbuy\s+kotakbank\b|\bbuy\s+kotak\s+mahindra\b",
    re.IGNORECASE,
)


def empty_final_view() -> dict[str, Any]:
    return {
        "investment_thesis": "",
        "evidence_supporting": [],
        "evidence_against": [],
        "remaining_unknowns": [],
        "confidence": {"mean_confidence": None, "calibration_notes": ""},
        "evidence_references": [],
        "questions_requiring_monitoring": [],
        "collapsed_to_buy_sell": False,
        "recommendation": None,  # intentionally unused — view is not BUY/SELL
    }


def build_institutional_answer(
    case: Mapping[str, Any],
    probes: Mapping[str, Mapping[str, Any]],
    *,
    answers: Optional[Mapping[str, Any]] = None,
    final_view: Optional[Mapping[str, Any]] = None,
    allow_external: bool = False,
) -> dict[str, Any]:
    """
    Assemble the 12-question institutional package.

    When `answers` / `final_view` are provided (test fixtures or Ask AGI output),
    they are validated — never replaced with hallucinated facts.
    """
    provided = dict(answers or {})
    view = {**empty_final_view(), **dict(final_view or {})}
    if "final_institutional_view" in provided and isinstance(provided["final_institutional_view"], Mapping):
        view = {**view, **dict(provided["final_institutional_view"])}

    sections: dict[str, Any] = {}
    for q in REQUIRED_QUESTIONS:
        key = q["key"]
        if key == "final_institutional_view":
            sections[key] = view
        else:
            sections[key] = provided.get(key)
            if sections[key] is None:
                sections[key] = {
                    "status": "missing",
                    "text": "",
                    "evidence_ids": [],
                    "module_hints": _module_hints_for(key),
                }

    # Provenance from contributing probes
    provenance = []
    for mod, row in probes.items():
        if row.get("contributing"):
            provenance.append(
                {
                    "module": mod,
                    "source": (row.get("payload") or {}).get("source") or "probe",
                    "ok": bool(row.get("ok")),
                }
            )

    return {
        "case_id": case.get("case_id"),
        "question": case.get("question"),
        "ticker": case.get("primary_ticker"),
        "peers": list(case.get("peer_tickers") or []),
        "sections": sections,
        "final_institutional_view": view,
        "provenance": provenance,
        "allow_external": bool(allow_external),
        "internet_used": False,
        "style_target": (case.get("gold_standard") or {}).get("style") or [],
        "answer_policy": "institutional_view_not_buy_sell",
    }


def _module_hints_for(key: str) -> list[str]:
    mapping = {
        "what_happened": ["FIL", "FSE", "FIRE-01"],
        "what_caused_it": ["FIL", "FIRE-02", "FIRE-03"],
        "temporary_or_structural": ["FIRE-01", "FIRE-02", "FIRE-06"],
        "management_diagnosis": ["FIRE-03", "FIRE-04"],
        "execution_vs_promises": ["FIRE-05"],
        "financial_quality_evolution": ["FSE", "FIRE-01", "FIRE-06"],
        "competitor_performance": ["CIO-01"],
        "relative_business_quality": ["FIRE-06", "CIO-01"],
        "evidence_against": ["FIRE-04", "FIRE-05", "FIRE-06"],
        "evidence_supporting": ["FIRE-01", "FIRE-05", "FIRE-06"],
        "missing_evidence": ["CW-01", "AskAGI"],
    }
    return list(mapping.get(key) or [])


def detect_answer_failures(answer: Mapping[str, Any]) -> list[dict[str, str]]:
    """Automatic failure detectors (deterministic)."""
    failures: list[dict[str, str]] = []
    view = answer.get("final_institutional_view") or {}
    sections = answer.get("sections") or {}
    blob = str(answer)

    # Collapsed to BUY/SELL
    thesis = str(view.get("investment_thesis") or "")
    bare = _BARE_BUY_KOTAK.search(thesis) or _BARE_BUY_KOTAK.search(blob)
    supporting = view.get("evidence_supporting") or []
    against = view.get("evidence_against") or []
    if bare and not supporting:
        failures.append(
            {
                "code": "BUY_WITHOUT_EVIDENCE",
                "detail": "Answer collapses to Buy Kotak without supporting evidence.",
            }
        )
    if re.search(r"\bsell\s+kotak\b", thesis, re.I) and not against and not supporting:
        failures.append(
            {
                "code": "SELL_WITHOUT_EVIDENCE",
                "detail": "Answer collapses to Sell without evidence package.",
            }
        )

    # Explicit BUY/SELL as the institutional answer (forbidden shape)
    rec = view.get("recommendation") or view.get("verdict") or view.get("action")
    if isinstance(rec, str) and _BUY_SELL_RE.search(rec):
        failures.append(
            {
                "code": "COLLAPSED_TO_BUY_SELL",
                "detail": f"Final view uses recommendation/verdict={rec!r}; must use institutional view shape.",
            }
        )
        view_flag = True
    else:
        view_flag = bool(view.get("collapsed_to_buy_sell"))
    if view_flag:
        if not any(f["code"] == "COLLAPSED_TO_BUY_SELL" for f in failures):
            failures.append(
                {
                    "code": "COLLAPSED_TO_BUY_SELL",
                    "detail": "Final view marked as collapsed to BUY/SELL.",
                }
            )

    # Contradictory evidence ignored
    if supporting and not against:
        # Only fail if thesis claims certainty / buy without counterevidence section
        if re.search(r"\b(clearly|obviously|definitely)\s+buy\b", thesis, re.I) or bare:
            failures.append(
                {
                    "code": "IGNORES_CONTRADICTORY_EVIDENCE",
                    "detail": "Supporting evidence present but evidence_against is empty while urging action.",
                }
            )
    against_section = sections.get("evidence_against")
    if isinstance(against_section, Mapping) and against_section.get("status") == "missing":
        if supporting and (bare or view_flag):
            failures.append(
                {
                    "code": "IGNORES_CONTRADICTORY_EVIDENCE",
                    "detail": "Q9 evidence_against missing while promoting a directional call.",
                }
            )

    # Unknowns
    unknowns = view.get("remaining_unknowns") or []
    missing_q = sections.get("missing_evidence")
    if not unknowns and not (
        isinstance(missing_q, Mapping)
        and (missing_q.get("text") or missing_q.get("items") or missing_q.get("status") != "missing")
    ):
        failures.append(
            {
                "code": "NO_UNKNOWNS_IDENTIFIED",
                "detail": "Final view must identify remaining unknowns / missing evidence.",
            }
        )

    # Provenance
    prov = answer.get("provenance") or []
    refs = view.get("evidence_references") or []
    if not prov and not refs:
        failures.append(
            {
                "code": "LOST_PROVENANCE",
                "detail": "No module provenance and no evidence_references on final view.",
            }
        )

    # External info without attribution
    if answer.get("internet_used") or answer.get("allow_external"):
        if "external_attribution" not in answer and not answer.get("external_sources"):
            failures.append(
                {
                    "code": "UNATTRIBUTED_EXTERNAL_INFO",
                    "detail": "External/non-graph information used without identification.",
                }
            )

    # Opinion/fact mix heuristic
    if re.search(r"\bas\s+a\s+fact,?\s+(i|we)\s+(believe|feel|think)\b", blob, re.I):
        failures.append(
            {
                "code": "MIXES_OPINION_WITH_FACT",
                "detail": "Language mixes belief statements presented as facts.",
            }
        )

    # Hallucination marker (explicit test injection)
    if answer.get("hallucinated") is True or view.get("hallucinated") is True:
        failures.append(
            {
                "code": "HALLUCINATED_FACTS",
                "detail": "Answer flagged as containing hallucinated facts.",
            }
        )

    # Deduplicate by code
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for f in failures:
        if f["code"] in seen:
            continue
        seen.add(f["code"])
        unique.append(f)
    return unique


def final_view_completeness(view: Mapping[str, Any]) -> dict[str, Any]:
    present = []
    missing = []
    for key in FINAL_VIEW_KEYS:
        val = view.get(key)
        ok = val not in (None, "", [], {})
        if ok:
            present.append(key)
        else:
            missing.append(key)
    return {
        "present": present,
        "missing": missing,
        "ratio": round(len(present) / max(1, len(FINAL_VIEW_KEYS)), 4),
    }


def question_coverage(sections: Mapping[str, Any]) -> dict[str, Any]:
    present = []
    missing = []
    for q in REQUIRED_QUESTIONS:
        key = q["key"]
        val = sections.get(key)
        if key == "final_institutional_view":
            ok = isinstance(val, Mapping) and bool(val.get("investment_thesis"))
        elif isinstance(val, Mapping):
            ok = val.get("status") != "missing" and bool(val.get("text") or val.get("items") or val.get("points"))
        else:
            ok = val not in (None, "", [], {})
        if ok:
            present.append(key)
        else:
            missing.append(key)
    return {
        "present": present,
        "missing": missing,
        "ratio": round(len(present) / max(1, len(REQUIRED_QUESTIONS)), 4),
    }
