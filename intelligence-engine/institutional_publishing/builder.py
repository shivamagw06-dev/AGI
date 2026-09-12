"""PUB-01 Publication Builder — assemble immutable objects into a publication. Never analyzes."""

from __future__ import annotations

from typing import Any

from institutional_publishing.models import InstitutionalPublication, PublicationPlan
from institutional_publishing.publication_registry import get
from institutional_publishing.schema import LINEAGE_VIEW, TYPE_TO_CATEGORY
from institutional_publishing.sources import collect_sources
from institutional_publishing.template_engine import get_template, render_title
from institutional_publishing.versioning import build_manifest, publication_id

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _fact_line(label: str, value: Any) -> str:
    if value is None or value == "":
        return f"- **{label}:** _(source unavailable — not invented by PUB-01)_"
    return f"- **{label}:** {value}"


def _section(key: str, title: str, body: str, source_refs: list[str]) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "body": body,
        "source_refs": source_refs,
        "composed": True,
        "analyzed": False,
    }


def build_publication(plan: PublicationPlan) -> InstitutionalPublication:
    """Compose publication from plan. Templates control formatting; sources control facts."""
    reg = get(plan.publication_type)
    template_name = plan.template or (reg.template if reg else plan.publication_type)
    template = get_template(template_name)
    template_version = str(
        (reg.template_version if reg else None) or template.get("version") or "1.0.0"
    )

    ticker = str(plan.context.get("ticker") or "")
    portfolio_id = str(plan.context.get("portfolio_id") or "agi-core-equity")
    generated_at = now_iso()
    as_of_date = generated_at[:10]

    refs, evidence, payloads = collect_sources(
        plan.required_sources,
        ticker=ticker,
        portfolio_id=portfolio_id,
    )

    title = render_title(
        template_name,
        {
            "ticker": ticker or "—",
            "portfolio_id": portfolio_id,
            "as_of_date": as_of_date,
        },
    )

    sections: list[dict[str, Any]] = []
    md_parts = [
        f"# {title}",
        "",
        "_Composed by PUB-01 from institutional objects. No new analysis or recommendations._",
        "",
    ]

    order = tuple(template.get("section_order") or ("overview", "lineage"))
    for key in order:
        if key == "overview":
            body = (
                f"Publication type `{plan.publication_type}` composed at {generated_at}.\n"
                f"Context: ticker={ticker or '—'}, portfolio={portfolio_id}."
            )
            sections.append(_section(key, "Overview", body, [r.ref_key() for r in refs[:3]]))
            md_parts.extend(["## Overview", body, ""])
        elif key == "macro":
            macro = payloads.get("Macro") or {}
            body = "\n".join(
                [
                    _fact_line("Summary", macro.get("summary")),
                    _fact_line("Drivers", ", ".join(macro.get("drivers") or [])),
                    _fact_line("Available", macro.get("available")),
                ]
            )
            sections.append(_section(key, "Macro", body, ["Macro:" + str(macro.get("macro_id") or "")]))
            md_parts.extend(["## Macro", body, ""])
        elif key == "observations":
            obs = payloads.get("Observation") or {}
            body = "\n".join(
                [
                    _fact_line("Title", obs.get("title")),
                    _fact_line("Summary", obs.get("summary")),
                    _fact_line("Severity", obs.get("severity")),
                ]
            )
            sections.append(
                _section(key, "Observations", body, ["Observation:" + str(obs.get("observation_id") or "")])
            )
            md_parts.extend(["## Observations", body, ""])
        elif key == "decision":
            cd = payloads.get("CompanyDecision") or {}
            pd = payloads.get("PortfolioDecision") or {}
            lines = []
            if cd:
                lines.append("### Company decision (referential)")
                lines.append(_fact_line("Ticker", cd.get("ticker") or ticker))
                lines.append(_fact_line("Recommendation", cd.get("recommendation")))
                lines.append(_fact_line("Note", cd.get("note")))
            if pd:
                lines.append("### Portfolio decision (referential)")
                lines.append(_fact_line("Recommendation", pd.get("recommendation")))
                lines.append(_fact_line("Posture", pd.get("investment_posture")))
                lines.append(_fact_line("Rule path", pd.get("rule_path")))
            body = "\n".join(lines) or "_No decision objects in plan._"
            src = []
            if cd:
                src.append("CompanyDecision:" + str(cd.get("decision_id") or ""))
            if pd:
                src.append("PortfolioDecision:" + str(pd.get("decision_id") or ""))
            sections.append(_section(key, "Decisions", body, src))
            md_parts.extend(["## Decisions", body, ""])
        elif key == "risk":
            risk = payloads.get("PortfolioRisk") or {}
            conc = risk.get("concentration") or {}
            body = "\n".join(
                [
                    _fact_line("Overall risk", risk.get("overall_risk")),
                    _fact_line("Risk id", risk.get("risk_id")),
                    _fact_line("Concentration", conc.get("level") if isinstance(conc, dict) else conc),
                    _fact_line("Available", risk.get("available")),
                ]
            )
            sections.append(
                _section(key, "Risk", body, ["PortfolioRisk:" + str(risk.get("risk_id") or "")])
            )
            md_parts.extend(["## Risk", body, ""])
        elif key == "policy":
            policy = payloads.get("PolicyAssessment") or {}
            body = "\n".join(
                [
                    _fact_line("Status", policy.get("overall_status")),
                    _fact_line("Score", policy.get("compliance_score")),
                    _fact_line("Violations", len(policy.get("violations") or [])),
                    _fact_line("Available", policy.get("available")),
                ]
            )
            sections.append(
                _section(key, "Policy", body, ["PolicyAssessment:" + str(policy.get("policy_id") or "")])
            )
            md_parts.extend(["## Policy", body, ""])
        elif key == "committee":
            committee = payloads.get("CommitteeResolution") or {}
            body = "\n".join(
                [
                    _fact_line("Status", committee.get("status")),
                    _fact_line("Outcome", committee.get("outcome")),
                    _fact_line(
                        "Decision recommendation (referenced)",
                        committee.get("decision_recommendation"),
                    ),
                    _fact_line("Available", committee.get("available")),
                ]
            )
            sections.append(
                _section(
                    key,
                    "Committee",
                    body,
                    ["CommitteeResolution:" + str(committee.get("resolution_id") or "")],
                )
            )
            md_parts.extend(["## Committee", body, ""])
        elif key == "evidence":
            ev = payloads.get("Evidence") or {}
            body = "\n".join(
                [
                    _fact_line("Title", ev.get("title")),
                    _fact_line("Snippet", ev.get("snippet")),
                ]
            )
            # Also list composed evidence refs
            for e in evidence[:6]:
                body += f"\n- {e.label}: {e.snippet}"
            sections.append(_section(key, "Evidence", body, [e.object_ref for e in evidence[:6]]))
            md_parts.extend(["## Evidence", body, ""])
        elif key == "lineage":
            body = " → ".join(LINEAGE_VIEW)
            body += "\n\nSource objects:\n"
            body += "\n".join(f"- {r.ref_key()} ({r.provider})" for r in refs)
            sections.append(_section(key, "Evidence lineage", body, [r.ref_key() for r in refs]))
            md_parts.extend(["## Evidence lineage", body, ""])

    body_markdown = "\n".join(md_parts).strip() + "\n"
    source_keys = tuple(r.ref_key() for r in refs)
    # provisional id from lineage inputs
    from institutional_publishing.versioning import lineage_hash

    lh = lineage_hash(
        publication_type=plan.publication_type,
        template_version=template_version,
        source_refs=source_keys,
    )
    pid = publication_id(plan.publication_type, lh, version="1")
    manifest = build_manifest(
        publication_id=pid,
        publication_type=plan.publication_type,
        template=template_name,
        template_version=template_version,
        generated_at=generated_at,
        sources=refs,
        renderer="markdown",
    )

    return InstitutionalPublication(
        publication_id=pid,
        publication_type=plan.publication_type,
        title=title,
        generated_at=generated_at,
        template=template_name,
        source_objects=tuple(refs),
        evidence=tuple(evidence),
        lineage=LINEAGE_VIEW,
        diagnostics=None,
        sections=tuple(sections),
        manifest=manifest,
        body_markdown=body_markdown,
        status="generated",
        version="1",
        category=TYPE_TO_CATEGORY.get(plan.publication_type, ""),
        renderer_outputs=(),
        analyzes=False,
    )
