"""Institutional Intelligence Certificate generator."""

from __future__ import annotations

from typing import Any

from academy.certification.grading.scale import band_for
from academy.certification.schema import ACS_VERSION, CERTIFICATION_PASS_SCORE, INSTITUTIONAL_READY_SCORE


def build_certificate(
    *,
    analyst_scores: dict[str, float],
    level_scores: dict[str, float],
    weak_areas: list[str],
    exam_stats: dict[str, Any],
) -> dict[str, Any]:
    # Weighted overall IQ
    weights = {
        "business": 1.0,
        "financial": 1.0,
        "valuation": 1.0,
        "risk": 0.9,
        "macro": 0.8,
        "sector": 0.8,
        "management": 0.7,
        "ownership": 0.7,
        "committee": 1.1,
        "cio": 1.1,
        "research_writer": 0.9,
        "portfolio": 0.8,
    }
    num = 0.0
    den = 0.0
    for a, s in analyst_scores.items():
        w = weights.get(a, 0.5)
        num += s * w
        den += w
    overall = round(num / den, 2) if den else 0.0
    band = band_for(overall)
    certified = overall >= CERTIFICATION_PASS_SCORE
    ready = overall >= INSTITUTIONAL_READY_SCORE

    lines = [
        "INSTITUTIONAL INTELLIGENCE CERTIFICATE",
        f"Version: {ACS_VERSION}",
        "",
    ]
    for a in sorted(analyst_scores.keys()):
        b = band_for(analyst_scores[a])
        lines.append(f"{a.replace('_', ' ').title():<22} {analyst_scores[a]:>6.1f}%  ({b['label']})")
    lines += [
        "",
        f"{'Overall Intelligence':<22} {overall:>6.1f}%",
        f"Grade: {band['label']} ({band['letter']})",
        f"Certification: {'PASS' if certified else 'FAIL'} (floor {CERTIFICATION_PASS_SCORE})",
        f"Institutional Ready: {'YES' if ready else 'NO'} (floor {INSTITUTIONAL_READY_SCORE})",
    ]

    return {
        "title": "Institutional Intelligence Certificate",
        "version": ACS_VERSION,
        "analyst_scores": analyst_scores,
        "level_scores": level_scores,
        "overall_intelligence": overall,
        "grade": band["label"],
        "letter": band["letter"],
        "certified": certified,
        "institutional_ready": ready,
        "weak_areas": weak_areas,
        "recommendations": _recommendations(weak_areas, analyst_scores),
        "regression": exam_stats.get("failed_exam_ids") or [],
        "improvement": _improvement(analyst_scores),
        "text": "\n".join(lines),
        "exam_stats": exam_stats,
    }


def _recommendations(weak: list[str], scores: dict[str, float]) -> list[str]:
    recs = []
    for a, s in sorted(scores.items(), key=lambda x: x[1]):
        if s < 85:
            recs.append(f"Strengthen {a} reasoning drills (score {s})")
    for w in weak[:8]:
        recs.append(f"Remediate weak area: {w}")
    if not recs:
        recs.append("Maintain institutional excellence drills across benchmark companies")
    return recs


def _improvement(scores: dict[str, float]) -> list[str]:
    return [
        "Track Overall Institutional IQ across releases",
        "Raise weakest analyst above Professional (85) before claiming Institutional Ready",
        "Expand case-history coverage for failure patterns",
    ]
