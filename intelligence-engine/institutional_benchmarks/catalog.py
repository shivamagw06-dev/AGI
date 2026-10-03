"""Permanent IBS case catalog — metadata only; corpora live in corpus.py."""

from __future__ import annotations

from typing import Any, Optional

from institutional_benchmarks.corpus import all_corpora, get_corpus
from institutional_benchmarks.schema import PASS_SCORE, SECTORS


def list_cases(*, sector: Optional[str] = None) -> list[dict[str, Any]]:
    sec = (sector or "").strip().upper() or None
    out = []
    for case_id, corpus in all_corpora().items():
        if sec and str(corpus.get("sector") or "").upper() != sec:
            continue
        out.append(
            {
                "case_id": case_id,
                "title": corpus.get("title"),
                "company": corpus.get("ticker"),
                "sector": corpus.get("sector"),
                "time_window": corpus.get("time_window"),
                "peers": list(corpus.get("peers") or []),
                "document_count": corpus.get("document_count"),
                "expected_evidence_coverage": list(corpus.get("expected_evidence_coverage") or []),
                "related_questions": list(corpus.get("related_questions") or []),
                "pass_threshold": PASS_SCORE,
                "raw_evidence_only": True,
                "fixture_answers": False,
            }
        )
    out.sort(key=lambda r: (str(r.get("sector") or ""), str(r.get("case_id") or "")))
    return out


def get_case(case_id: str, *, cutoff: Optional[str] = None) -> dict[str, Any]:
    corpus = get_corpus(case_id, cutoff=cutoff)
    return {
        "case_id": corpus.get("case_id"),
        "title": corpus.get("title"),
        "company": corpus.get("ticker"),
        "sector": corpus.get("sector"),
        "time_window": corpus.get("time_window"),
        "raw_evidence_corpus": {
            "document_count": corpus.get("document_count"),
            "historical_cutoff": corpus.get("historical_cutoff"),
            "hidden_after_cutoff": corpus.get("hidden_after_cutoff"),
            "evidence_types": _types(corpus),
        },
        "expected_evidence_coverage": list(corpus.get("expected_evidence_coverage") or []),
        "evaluation_rules": {
            "raw_evidence_only": True,
            "no_fixture_answers": True,
            "pass_threshold": PASS_SCORE,
            "require_counter_evidence": True,
            "require_unknowns": True,
            "require_monitoring": True,
            "require_peer_comparison": True,
            "require_counterfactuals": True,
            "require_provenance": True,
        },
        "pass_threshold": PASS_SCORE,
        "related_questions": list(corpus.get("related_questions") or []),
        "corpus": corpus,
    }


def sectors() -> list[dict[str, Any]]:
    cases = list_cases()
    out = []
    for s in SECTORS:
        rows = [c for c in cases if c.get("sector") == s]
        out.append({"sector": s, "case_count": len(rows), "cases": [c["case_id"] for c in rows]})
    return out


def _types(corpus: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in corpus.get("documents") or []:
        k = str(d.get("evidence_type") or "unknown")
        counts[k] = counts.get(k, 0) + 1
    return counts
