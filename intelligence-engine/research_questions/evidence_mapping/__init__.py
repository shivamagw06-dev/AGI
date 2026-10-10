"""Evidence mapping — every question knows which evidence answers it."""

from __future__ import annotations

from typing import Any


def map_evidence(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for q in questions:
        evidence = list(q.get("required_evidence") or [])
        if not evidence:
            # Infer light defaults from type
            t = str(q.get("type") or "")
            defaults = {
                "Historical": ["Historical"],
                "Peer": ["PIL"],
                "Valuation": ["PIL", "Valuation"],
                "Forecast": ["Forecast"],
                "Macro": ["Macro"],
                "Risk": ["Risk"],
                "Management": ["FIL", "Transcript"],
                "Accounting": ["Accounting", "FIL"],
                "Financial": ["FIL"],
                "Business": ["FIL", "Business"],
                "Portfolio": ["Portfolio"],
                "Contradiction": ["Risk", "FIL"],
                "Verification": ["FIL", "PIL"],
            }
            evidence = list(defaults.get(t, ["FIL"]))
        out.append(
            {
                **q,
                "required_evidence": evidence,
                "evidence_map": {
                    "sources": evidence,
                    "minimum_independent_sources": max(1, min(3, len(evidence))),
                },
            }
        )
    return out


def evidence_rollup(questions: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, int] = {}
    for q in questions:
        for e in q.get("required_evidence") or []:
            by_source[str(e)] = by_source.get(str(e), 0) + 1
    return {
        "by_source": dict(sorted(by_source.items(), key=lambda kv: -kv[1])),
        "unique_sources": sorted(by_source.keys()),
        "mapped_question_count": sum(1 for q in questions if q.get("required_evidence")),
    }
