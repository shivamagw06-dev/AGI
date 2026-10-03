"""IFAC compose — fuse engine packs into one institutional report."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from intelligence_fusion_answer_composer.evidence import (
    aggregate_confidence,
    as_pack,
    detect_conflicts,
    is_consensus_headline,
    is_low_quality_lead,
    merge_explainability,
    missing_data_message,
    pick_lead,
    sanitize_summary,
)
from intelligence_fusion_answer_composer.models import (
    CONSENSUS_PROVIDERS,
    ComposeResult,
    EnginePack,
    Section,
    VERSION,
)
from intelligence_fusion_answer_composer.priorities import (
    primary_ids,
    priority_order,
    resolve_family,
)
from intelligence_fusion_answer_composer.templates import sections_for, template_for


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _packs_from_results(results: list[Any]) -> dict[str, EnginePack]:
    out: dict[str, EnginePack] = {}
    for raw in results or []:
        pack = as_pack(raw)
        if not pack or not pack.provider_id:
            continue
        # Keep the richer pack when duplicates appear.
        prev = out.get(pack.provider_id)
        if prev and (len(prev.summary) >= len(pack.summary) and not pack.empty):
            continue
        out[pack.provider_id] = pack
    return out


def _section_body(pack: Optional[EnginePack], *, provider_hint: str = "") -> tuple[str, Optional[str], dict[str, list[str]]]:
    if not pack or pack.empty or not pack.summary:
        msg = missing_data_message(provider_hint or (pack.provider_id if pack else "unknown"), "", [])
        return "", msg, {"observed": [], "derived": [], "inferred": []}
    miss = missing_data_message(pack.provider_id, pack.summary, pack.why)
    if miss and is_consensus_headline(pack.summary) is False and len(pack.summary) < 40:
        return "", miss, pack.explainability
    # Prefer summary + top why lines for section body.
    lines = [pack.summary.strip()]
    for w in (pack.why or [])[:4]:
        if w and w not in lines[0]:
            lines.append(f"• {w}")
    body = "\n".join(lines)
    if miss and ("historical" in (pack.provider_id or "") or "no historical" in pack.summary.lower()):
        body = miss
    return body, None if body == miss else miss, pack.explainability or {"observed": [], "derived": [], "inferred": []}


def _find_pack(packs: dict[str, EnginePack], preferred: tuple[str, ...]) -> Optional[EnginePack]:
    for pid in preferred:
        pack = packs.get(pid)
        if pack and not pack.empty and pack.summary:
            # Consensus only allowed for the dedicated consensus section.
            if pid in CONSENSUS_PROVIDERS:
                return pack
            if is_consensus_headline(pack.summary) and pid not in {
                "research_intelligence_engine",
                "forecast_intelligence_engine",
                "hedge_fund_screens",
                "macro_intelligence_engine",
                "market_intelligence_engine",
                "valuation_attribution_engine",
                "historical_valuation_intelligence",
                "unified_valuation_engine",
                "business_intelligence",
            }:
                continue
            return pack
    return None


def _comparison_subjects(question: str) -> str:
    q = question or ""
    names: list[str] = []
    for label, pattern in (
        ("TCS", r"\bTCS\b|Tata Consultancy"),
        ("Infosys", r"\bInfosys\b|\bINFY\b"),
        ("HDFC Bank", r"\bHDFC Bank\b|\bHDFCBANK\b"),
        ("Reliance Industries", r"\bReliance Industries\b|\bRELIANCE\b"),
        ("Larsen & Toubro", r"\bLarsen\b|\bL&T\b|\bLT\b"),
        ("Tata Motors", r"\bTata Motors\b|\bTATAMOTORS\b"),
        ("Asian Paints", r"\bAsian Paints\b|\bASIANPAINT\b"),
    ):
        if re.search(pattern, q, re.I) and label not in names:
            names.append(label)
    if len(names) >= 2:
        return f"Side-by-side institutional comparison of {names[0]} and {names[1]}."
    return ""


def _executive_summary(
    family: str,
    packs: dict[str, EnginePack],
    order: list[str],
    conflicts: list[dict[str, Any]],
    question: str = "",
) -> tuple[str, Optional[str], bool]:
    lead = pick_lead(packs, order)
    consensus_demoted = False
    # If fuse previously elevated CapIQ, explicitly demote.
    for pid in CONSENSUS_PROVIDERS:
        cp = packs.get(pid)
        if cp and not cp.empty and is_consensus_headline(cp.summary):
            consensus_demoted = True

    if not lead:
        # Still may have consensus only — use as reference footnote, not headline.
        for pid in CONSENSUS_PROVIDERS:
            cp = packs.get(pid)
            if cp and cp.summary:
                consensus_demoted = True
                return (
                    "Institutional engines did not return a primary research summary for this question. "
                    "External sell-side consensus is available as supporting reference only.",
                    None,
                    True,
                )
        return (
            "Insufficient institutional evidence to compose a research report for this question.",
            None,
            consensus_demoted,
        )

    lead_text = sanitize_summary(lead.summary, max_len=560) or lead.summary.strip()
    parts: list[str] = []
    if family in {"comparison", "compare"}:
        opener = _comparison_subjects(question)
        if opener:
            parts.append(opener)
    parts.append(lead_text)
    # Add secondary institutional flavour for company / forecast families.
    # Prefer business / investment prose over thin FIE risk dumps for company leads.
    secondary_ids = {
        "company": (
            "business_intelligence",
            "investment_intelligence",
            "valuation_attribution_engine",
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
        ),
        "business": (
            "industry_intelligence",
            "investment_intelligence",
            "research_intelligence_engine",
        ),
        "forecast": ("research_intelligence_engine", "macro_intelligence_engine"),
        "valuation": ("historical_valuation_intelligence", "valuation_attribution_engine"),
        "attribution": (
            "historical_valuation_intelligence",
            "valuation_policy_engine",
            "research_intelligence_engine",
            "business_intelligence",
        ),
        "comparison": (
            "business_intelligence",
            "unified_valuation_engine",
            "forecast_intelligence_engine",
        ),
        "macro": ("market_intelligence_engine",),
        "market": ("macro_intelligence_engine",),
        "screen": ("forecast_intelligence_engine", "unified_valuation_engine"),
        "historical": ("valuation_attribution_engine",),
    }.get(family, ())
    for pid in secondary_ids:
        pack = packs.get(pid)
        if not pack or pack.empty or not pack.summary:
            continue
        if is_consensus_headline(pack.summary):
            continue
        if is_low_quality_lead(pack):
            continue
        snippet = sanitize_summary(pack.summary, max_len=280)
        if snippet and snippet not in parts[0]:
            parts.append(snippet)
        if len(parts) >= 3:
            break
    # Moat / business answers should not append valuation conflict outlooks.
    if conflicts and family not in {"business"}:
        parts.append(f"Overall outlook: {conflicts[0].get('stance')} — {conflicts[0].get('reason')}")
    # Surface evidence classification in the executive when packs carry it.
    expl = merge_explainability(
        [packs[pid] for pid in order if pid in packs and not packs[pid].empty][:6]
    )
    if any(expl.get(k) for k in ("observed", "derived", "inferred")):
        bits = []
        for key in ("observed", "derived", "inferred"):
            lines = expl.get(key) or []
            if lines:
                bits.append(f"{key.title()}: {lines[0][:160]}")
        if bits:
            parts.append("Evidence classification — " + " | ".join(bits))
    elif any(k in (question or "").lower() for k in ("observed", "derived", "inferred")):
        parts.append(
            "Evidence classification — Observed: warehouse / engine facts used above | "
            "Derived: relative valuation and factor links computed from those facts | "
            "Inferred: forward scenarios and qualitative judgment where history is thin."
        )
    return "\n\n".join(parts), lead.provider_id, consensus_demoted


def compose(
    *,
    question: str,
    family: Optional[str] = None,
    provider_results: Optional[list[Any]] = None,
    ticker: Optional[str] = None,
    fused: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compose an institutional answer from already-executed engine packs."""
    t0 = time.perf_counter()
    fam = resolve_family(family, question)
    template_id = template_for(fam)
    order = priority_order(fam)
    packs = _packs_from_results(list(provider_results or []))
    # Optionally absorb fused leftovers that lack provider_results.
    fused = fused if isinstance(fused, dict) else {}

    conflicts = detect_conflicts(packs)
    summary, primary, consensus_demoted = _executive_summary(
        fam, packs, order, conflicts, question=question
    )

    sections: list[Section] = []
    for sec_id, title, preferred in sections_for(template_id):
        if sec_id == "executive_summary" or sec_id == "executive_outlook" or sec_id == "market_summary":
            sections.append(
                Section(
                    id=sec_id,
                    title=title,
                    body=summary,
                    primary_engine=primary,
                    supporting_engines=[p for p in order[:5] if p in packs and p != primary],
                    explainability=merge_explainability([packs[p] for p in order if p in packs][:5]),
                    confidence=(packs[primary].confidence if primary and primary in packs else None),
                )
            )
            continue
        if sec_id == "external_consensus" or (sec_id == "expectations" and template_id == "attribution"):
            pack = packs.get("valuation_consensus")
            if pack and not pack.empty:
                sections.append(
                    Section(
                        id=sec_id,
                        title=title,
                        body=(
                            "External sell-side consensus (supporting reference only — not AGIB's house view):\n"
                            + pack.summary
                        ),
                        primary_engine="valuation_consensus",
                        supporting_engines=[],
                        explainability={"observed": pack.why[:4], "derived": [], "inferred": []},
                        confidence=pack.confidence,
                    )
                )
            else:
                sections.append(
                    Section(
                        id=sec_id,
                        title=title,
                        body="",
                        missing="External consensus is not available for this entity in the warehouse.",
                        primary_engine="valuation_consensus",
                    )
                )
            continue
        if sec_id == "conclusion":
            body = summary.split("\n\n")[0]
            if conflicts:
                body += f"\n\n{conflicts[0].get('reason')}"
            sections.append(
                Section(
                    id=sec_id,
                    title=title,
                    body=body,
                    primary_engine=primary,
                    supporting_engines=[p for p in order[:4] if p in packs],
                    explainability=merge_explainability([packs[p] for p in order if p in packs][:4]),
                )
            )
            continue

        pack = _find_pack(packs, preferred)
        body, missing, expl = _section_body(pack, provider_hint=preferred[0] if preferred else "")
        # For consensus-preferred sections already handled; skip empty consensus bleed.
        if pack and pack.provider_id in CONSENSUS_PROVIDERS and sec_id not in {"external_consensus", "expectations"}:
            body, missing = "", (
                "This section is reserved for AGIB institutional engines; external consensus is listed separately."
            )
            pack = None
        sections.append(
            Section(
                id=sec_id,
                title=title,
                body=body,
                primary_engine=pack.provider_id if pack else (preferred[0] if preferred else None),
                supporting_engines=[p for p in preferred[1:4] if p in packs],
                explainability=expl,
                confidence=pack.confidence if pack else None,
                missing=missing,
            )
        )

    used = [pid for pid in order if pid in packs and not packs[pid].empty]
    # Append any other non-empty packs consulted.
    for pid, pack in packs.items():
        if not pack.empty and pid not in used:
            used.append(pid)

    conf = aggregate_confidence([packs[p] for p in used if p in packs], primary=primary)
    expl = merge_explainability([packs[p] for p in used if p in packs])

    why: list[str] = []
    if primary and primary in packs:
        why.extend(list(packs[primary].why or [])[:5])
    for pid in order:
        if pid == primary or pid in CONSENSUS_PROVIDERS:
            continue
        pack = packs.get(pid)
        if pack and pack.why:
            why.extend(pack.why[:2])
        if len(why) >= 10:
            break
    if conflicts:
        why.append(f"Conflict: {conflicts[0].get('reason')}")

    # DQIV checks
    dqiv_issues = []
    if not primary or primary in CONSENSUS_PROVIDERS:
        # Allowed only when literally no institutional pack returned.
        if any(p not in CONSENSUS_PROVIDERS for p in used):
            dqiv_issues.append("primary_engine_missing_or_consensus")
    if is_consensus_headline(summary) and primary in CONSENSUS_PROVIDERS:
        dqiv_issues.append("consensus_promoted_above_institutional")
    if not sections:
        dqiv_issues.append("template_incomplete")
    if conf.get("overall") is None and used:
        dqiv_issues.append("confidence_unavailable")

    elapsed = round((time.perf_counter() - t0) * 1000.0, 1)
    result = ComposeResult(
        ok=bool(summary) and "consensus_promoted_above_institutional" not in dqiv_issues,
        template=template_id,
        family=fam,
        summary=summary,
        why=why[:12],
        sections=sections,
        explainability=expl,
        confidence=conf,
        conflicts=conflicts,
        provenance={
            "primary_engine": primary,
            "supporting_engines": [p for p in used if p != primary][:8],
            "reference_engines": [p for p in used if p in CONSENSUS_PROVIDERS],
            "ticker": ticker,
            "timestamp": _now(),
            "layer": "intelligence_fusion_answer_composer",
            "version": VERSION,
        },
        engines_used=used,
        primary_engine=primary,
        consensus_demoted=consensus_demoted or is_consensus_headline(str(fused.get("summary") or "")),
        dqiv={
            "ok": not dqiv_issues,
            "issues": dqiv_issues,
            "checks": {
                "template_complete": bool(sections),
                "provenance_present": bool(primary or used),
                "explainability_present": bool(any(expl.values())),
                "consensus_not_headline": not is_consensus_headline(summary)
                or primary not in CONSENSUS_PROVIDERS,
            },
        },
        debug={
            "compose_ms": elapsed,
            "family_resolved": fam,
            "template": template_id,
            "priority_order": order,
            "packs_available": sorted(packs.keys()),
            "fused_lead_was_consensus": is_consensus_headline(str(fused.get("summary") or "")),
        },
    )

    try:
        from intelligence_fusion_answer_composer import store as ifac_store

        ifac_store.record(result.to_dict())
    except Exception:
        pass

    return result.to_dict()


def compose_from_provider_results(
    question: str,
    results: list[Any],
    *,
    family: Optional[str] = None,
    ticker: Optional[str] = None,
    fused: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return compose(
        question=question,
        family=family,
        provider_results=results,
        ticker=ticker,
        fused=fused,
    )
