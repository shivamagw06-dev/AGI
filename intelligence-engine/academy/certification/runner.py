"""ACS runner — execute certification exams and aggregate scores."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from academy.certification.business import exams as business_exams
from academy.certification.cio import exams as cio_exams
from academy.certification.committee import exams as committee_exams
from academy.certification.financial import exams as financial_exams
from academy.certification.grading.scorer import score_exam
from academy.certification.grading.scale import band_for
from academy.certification.levels.catalog import shared_exams
from academy.certification.macro import exams as macro_exams
from academy.certification.management import exams as management_exams
from academy.certification.ownership import exams as ownership_exams
from academy.certification.portfolio import exams as portfolio_exams
from academy.certification.reasoner import reason
from academy.certification.reports.certificate import build_certificate
from academy.certification.reports.institutional_iq import compute_institutional_iq
from academy.certification.research_writer import exams as irw_exams
from academy.certification.risk import exams as risk_exams
from academy.certification.schema import ACS_VERSION, ExamSpec
from academy.certification.sector import exams as sector_exams
from academy.certification.valuation import exams as valuation_exams


def all_exams() -> list[ExamSpec]:
    banks = [
        shared_exams(),
        business_exams.exams(),
        financial_exams.exams(),
        valuation_exams.exams(),
        sector_exams.exams(),
        macro_exams.exams(),
        risk_exams.exams(),
        management_exams.exams(),
        ownership_exams.exams(),
        committee_exams.exams(),
        cio_exams.exams(),
        portfolio_exams.exams(),
        irw_exams.exams(),
    ]
    out: list[ExamSpec] = []
    for b in banks:
        out.extend(b)
    return out


def exams_for_analyst(analyst: str) -> list[ExamSpec]:
    return [e for e in all_exams() if e.analyst == analyst]


def exams_for_level(level: int) -> list[ExamSpec]:
    return [e for e in all_exams() if e.level == level]


def run_exam(exam: ExamSpec) -> dict[str, Any]:
    reasoned = reason(exam)
    scored = score_exam(exam, reasoned)
    d = scored.to_dict()
    d["question"] = exam.question
    d["company"] = exam.company
    d["topic"] = exam.topic
    d["provenance"] = reasoned.get("provenance") or {}
    return d


def run_certification(
    *,
    analysts: list[str] | None = None,
    levels: list[int] | None = None,
    limit_per_analyst: int | None = None,
) -> dict[str, Any]:
    """Run ACS. For CI speed, limit_per_analyst may sample; full run uses all exams."""
    exams = all_exams()
    if analysts:
        allow_a = set(analysts)
        exams = [e for e in exams if e.analyst in allow_a or e.analyst == "general"]
    if levels:
        allow_l = set(levels)
        exams = [e for e in exams if e.level in allow_l]

    if limit_per_analyst:
        by_a: dict[str, list[ExamSpec]] = defaultdict(list)
        trimmed: list[ExamSpec] = []
        for e in exams:
            if len(by_a[e.analyst]) < limit_per_analyst:
                by_a[e.analyst].append(e)
                trimmed.append(e)
        # always keep shared critical levels fully if present and not analyst-limited oddly
        exams = trimmed

    results = [run_exam(e) for e in exams]

    by_analyst: dict[str, list[float]] = defaultdict(list)
    by_level: dict[str, list[float]] = defaultdict(list)
    weak: list[str] = []
    failed_ids: list[str] = []
    for r in results:
        by_analyst[r["analyst"]].append(r["score"])
        by_level[str(r["level"])].append(r["score"])
        if r["score"] < 80:
            weak.append(f"{r['exam_id']}:{r.get('topic') or r['analyst']}")
        if not r["passed"] or r["score"] < 70:
            failed_ids.append(r["exam_id"])

    analyst_scores = {a: round(sum(v) / len(v), 2) for a, v in sorted(by_analyst.items()) if v}
    level_scores = {lvl: round(sum(v) / len(v), 2) for lvl, v in sorted(by_level.items()) if v}

    iq = compute_institutional_iq(analyst_scores)
    # fold IQ overall into analyst map for certificate display completeness
    cert = build_certificate(
        analyst_scores=analyst_scores,
        level_scores=level_scores,
        weak_areas=weak[:20],
        exam_stats={
            "exams_run": len(results),
            "exams_available": len(all_exams()),
            "failed_exam_ids": failed_ids,
            "mean_score": round(sum(r["score"] for r in results) / max(1, len(results)), 2),
        },
    )
    # Prefer IQ overall if richer component set
    if iq.get("overall_agi_iq"):
        cert["overall_intelligence"] = iq["overall_agi_iq"]
        cert["grade"] = iq["grade"]
        cert["letter"] = iq["letter"]
        from academy.certification.schema import CERTIFICATION_PASS_SCORE, INSTITUTIONAL_READY_SCORE

        cert["certified"] = iq["overall_agi_iq"] >= CERTIFICATION_PASS_SCORE
        cert["institutional_ready"] = iq["overall_agi_iq"] >= INSTITUTIONAL_READY_SCORE

    return {
        "programme": "AGI_ACADEMY_CERTIFICATION_SUITE",
        "version": ACS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "metric": "reasoning_quality",
        "not_metric": ["book_ingest", "concept_existence_only"],
        "analyst_scores": analyst_scores,
        "level_scores": level_scores,
        "institutional_iq": iq,
        "certificate": cert,
        "results": results,
        "counts": _counts(),
    }


def _counts() -> dict[str, int]:
    return {
        "business": len(business_exams.exams()),
        "financial": len(financial_exams.exams()),
        "valuation": len(valuation_exams.exams()),
        "sector": len(sector_exams.exams()),
        "macro": len(macro_exams.exams()),
        "risk": len(risk_exams.exams()),
        "management": len(management_exams.exams()),
        "ownership": len(ownership_exams.exams()),
        "committee": len(committee_exams.exams()),
        "cio": len(cio_exams.exams()),
        "portfolio": len(portfolio_exams.exams()),
        "research_writer": len(irw_exams.exams()),
        "shared": len(shared_exams()),
        "total": len(all_exams()),
    }


def inventory() -> dict[str, Any]:
    return {
        "version": ACS_VERSION,
        "counts": _counts(),
        "bands": [band_for(s) for s in (97, 92, 87, 82, 75, 65, 40)],
        "analysts": sorted({e.analyst for e in all_exams()}),
        "levels": sorted({e.level for e in all_exams()}),
    }
