"""Render Reason objects → institutional report sections (IRE-02)."""

from __future__ import annotations

from typing import Any

from institutional_reporting.models import InstitutionalReportInput, ReportSection
from institutional_reporting.reasoning import Reason, ReasonGraph
from institutional_reporting.schema import REPORT_SECTIONS, SECTION_TITLES


def _bullets(rows: list[str] | tuple[str, ...], *, empty: str = "(none)") -> str:
    items = [str(r).strip() for r in rows if str(r).strip()]
    if not items:
        return f"- {empty}\n"
    return "".join(f"- {item}\n" for item in items)


def render_reason_paragraph(reason: Reason) -> str:
    """Deterministic paragraph from structured reasoning — every sentence maps to a field."""
    support = list(reason.supporting_points)
    contra = list(reason.contradicting_points)
    unknowns = list(reason.unknowns)

    lead_support = support[0] if support else "structured_inputs"
    lead_contra = contra[0] if contra else "offsetting_factors"
    lead_unknown = unknowns[0] if unknowns else "unverified_forward_path"

    # Fixed patterns only — no phrase bank / no variation.
    lines = [
        f"{reason.title} conclusion is {reason.conclusion} because {lead_support}.",
    ]
    if len(support) > 1:
        lines.append(f"Additional support: {'; '.join(support[1:3])}.")
    lines.append(f"However, {lead_contra} continues to create uncertainty.")
    lines.append(f"Looking ahead, {lead_unknown} remains an important unknown.")
    return " ".join(lines)


def render_section_from_reason(reason: Reason) -> str:
    """Full section contract body for one Reason."""
    title = reason.title
    body = (
        f"{title}\n\n"
        f"Conclusion\n\n"
        f"{reason.conclusion}\n\n"
        f"Supporting Reasons\n\n"
        f"{_bullets(reason.supporting_points)}"
        f"\n"
        f"Contradicting Reasons\n\n"
        f"{_bullets(reason.contradicting_points)}"
        f"\n"
        f"Unknowns\n\n"
        f"{_bullets(reason.unknowns)}"
        f"\n"
        f"Evidence\n\n"
        f"{_bullets(reason.supporting_evidence, empty='(none)')}"
        f"\n"
        f"Confidence\n\n"
        f"{reason.confidence:.2f}\n\n"
        f"Explanation\n\n"
        f"{render_reason_paragraph(reason)}\n"
    )
    return body


def render_sections_from_reasons(
    graph: ReasonGraph,
    inp: InstitutionalReportInput | None = None,
) -> list[ReportSection]:
    by_key = graph.by_section()
    sections: list[ReportSection] = []
    for key in REPORT_SECTIONS:
        reason = by_key.get(key)
        if reason is None:
            # Caller/validator should reject; still emit placeholder for diagnostics.
            reason = Reason(
                title=SECTION_TITLES[key],
                conclusion="",
                confidence=-1.0,
                section_key=key,
            )
        body = render_section_from_reason(reason)
        # Extract evidence ids (tokens that look like IDs / catalog ids)
        evidence_ids = [
            e
            for e in reason.supporting_evidence
            if e and (e.startswith("FIRE-") or e.startswith("AR-") or e.startswith("CC-") or e.startswith("QR-") or "-" in e or e.isupper())
        ]
        if not evidence_ids:
            evidence_ids = list(reason.supporting_evidence)
        sections.append(
            ReportSection(
                key=key,
                title=SECTION_TITLES[key],
                body=body if body.endswith("\n") else body + "\n",
                evidence_ids=list(evidence_ids),
                meta={
                    "reason": reason.to_dict(),
                    "conclusion": reason.conclusion,
                    "confidence": reason.confidence,
                    "supporting_points": list(reason.supporting_points),
                    "contradicting_points": list(reason.contradicting_points),
                    "unknowns": list(reason.unknowns),
                    "supporting_evidence": list(reason.supporting_evidence),
                },
                reason=reason,
            )
        )
    return sections


# Back-compat alias used by older IRE-01 call sites during transition.
def render_sections(inp: InstitutionalReportInput) -> list[ReportSection]:
    from institutional_reporting.reason_composer import compose_reasons

    return render_sections_from_reasons(compose_reasons(inp), inp)


def render_text(sections: list[ReportSection], *, ticker: str, company_name: str) -> str:
    parts = [
        "Institutional Report",
        "",
        f"{company_name} ({ticker})",
        "",
    ]
    for section in sections:
        parts.append(section.body.rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_reason_graph_text(graph: ReasonGraph) -> str:
    lines = ["Reason Graph", ""]
    for reason in graph.reasons:
        lines.append(f"## {reason.title} ({reason.section_key})")
        lines.append(f"Conclusion: {reason.conclusion}")
        lines.append(f"Confidence: {reason.confidence:.2f}")
        lines.append("Supporting:")
        lines.extend(f"  - {p}" for p in reason.supporting_points)
        lines.append("Contradicting:")
        lines.extend(f"  - {p}" for p in reason.contradicting_points)
        lines.append("Unknowns:")
        lines.extend(f"  - {u}" for u in reason.unknowns)
        lines.append("Evidence:")
        lines.extend(f"  - {e}" for e in reason.supporting_evidence)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_diagnostics_text(diagnostics: dict[str, Any]) -> str:
    lines = ["Diagnostics", ""]
    for key in (
        "generated_at",
        "report_version",
        "ire_version",
        "validator_version",
        "reason_object_count",
        "evidence_count",
        "quality_gate",
        "quality_gate_pass",
    ):
        if key in diagnostics:
            lines.append(f"{key}: {diagnostics[key]}")
    lines.append("")
    return "\n".join(lines)
