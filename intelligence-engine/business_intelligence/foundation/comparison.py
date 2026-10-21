"""Competitive comparison across business axes — not ratio-only."""

from __future__ import annotations

from typing import Any

from business_intelligence.foundation.engines import (
    analyse_business_model,
    analyse_moat,
    analyse_growth,
    analyse_lifecycle,
    analyse_value_drivers,
)
from business_intelligence.foundation.evidence import assemble_evidence
from business_intelligence.foundation.named_pedagogy import (
    lookup_named_pedagogy,
    profitability_contrast_summary,
)
from business_intelligence.foundation.taxonomy import classify_industry


def compare_companies(question: str, names_or_tickers: list[str] | None = None) -> dict[str, Any]:
    ev0 = assemble_evidence(question)
    names = names_or_tickers or ev0.get("compare_names") or []
    companies_ev: list[dict[str, Any]] = []
    if ev0.get("compare_companies"):
        for i, c in enumerate(ev0["compare_companies"]):
            tk = c.get("ticker")
            asked = (names[i] if i < len(names) else None) or c.get("company_name") or tk
            if c.get("uncovered") or not tk:
                # Preserve uncovered name + industry template without CapIQ invent.
                cev = assemble_evidence(f"Explain {asked} business model")
                cev = dict(cev)
                cev["company"] = {
                    **(cev.get("company") or {}),
                    "company_name": asked,
                    "uncovered": True,
                }
                if c.get("industry") and not cev.get("industry_key"):
                    cev["industry_key"] = c.get("industry")
                companies_ev.append(cev)
            else:
                cev = assemble_evidence(f"Explain {asked}", ticker=tk)
                cev = dict(cev)
                # Keep the user-facing name (Indigo) alongside CapIQ legal name.
                co = dict(cev.get("company") or {})
                co["display_name"] = asked
                if not co.get("company_name"):
                    co["company_name"] = asked
                cev["company"] = co
                companies_ev.append(cev)
    elif names:
        for n in names[:2]:
            companies_ev.append(assemble_evidence(f"Explain {n}"))
    elif ev0.get("ticker"):
        companies_ev.append(ev0)

    if len(companies_ev) < 2:
        # Try to still answer with industry-level comparison frame.
        return {
            "ok": False,
            "companies": names,
            "summary": (
                "Competitive comparison requires two identifiable companies. "
                "Provide names or tickers (e.g. 'Compare TCS vs Infosys')."
            ),
            "axes": {},
            "confidence": 0.2,
            "fabricated": False,
        }

    axes: dict[str, dict[str, Any]] = {}
    labels = []
    for i, cev in enumerate(companies_ev[:2]):
        co = cev.get("company") or {}
        asked = names[i] if i < len(names) else None
        label = asked or co.get("display_name") or co.get("company_name") or cev.get("ticker") or "Company"
        labels.append(label)
        bm = analyse_business_model(cev)
        moat = analyse_moat(cev)
        growth = analyse_growth(cev)
        life = analyse_lifecycle(cev)
        vd = analyse_value_drivers(cev)
        axes[label] = {
            "ticker": cev.get("ticker"),
            "industry": cev.get("industry_key"),
            "business_type": bm.get("business_type"),
            "how_it_makes_money": (bm.get("how_it_makes_money") or "")[:220],
            "capital_intensity": bm.get("capital_intensity"),
            "operating_leverage": bm.get("operating_leverage"),
            "primary_moats": moat.get("primary_moats"),
            "moat_durability": moat.get("durability"),
            "growth_modes": growth.get("primary_modes"),
            "lifecycle": life.get("stage"),
            "value_drivers": vd.get("value_drivers"),
            "cash_conversion_lens": bm.get("working_capital_profile"),
            "management_note": "Compare capital allocation and execution only with filing-backed evidence.",
        }

    a, b = labels[0], labels[1]
    qlow = (question or "").lower()
    ped_a = lookup_named_pedagogy(name=a, question=question)
    ped_b = lookup_named_pedagogy(name=b, question=question)
    # Enrich axes from named pedagogy when CapIQ/industry templates are identical.
    for label, ped in ((a, ped_a), (b, ped_b)):
        if not ped:
            continue
        ax = axes.get(label) or {}
        if ped.get("how_it_makes_money"):
            ax["how_it_makes_money"] = ped["how_it_makes_money"][:220]
        if ped.get("business_type"):
            ax["business_type"] = ped["business_type"]
        if ped.get("moats"):
            ax["primary_moats"] = list(ped["moats"])[:4]
        if ped.get("archetype"):
            ax["archetype"] = ped["archetype"]
        axes[label] = ax

    if "capital allocat" in qlow:
        summary = (
            f"{a} vs {b}: compare capital allocation using business type "
            f"({axes[a].get('business_type')} vs {axes[b].get('business_type')}), "
            f"growth modes, capital intensity, leverage posture, and ROIC discipline — "
            f"evidence-gated, not ratios alone."
        )
    elif ped_a and ped_b and re_search_profitability(qlow):
        summary = profitability_contrast_summary(a, b, ped_a, ped_b)
    elif ped_a and ped_b and ped_a.get("archetype") != ped_b.get("archetype"):
        summary = (
            f"{a} ({ped_a.get('archetype', '').replace('_', ' ')}) vs "
            f"{b} ({ped_b.get('archetype', '').replace('_', ' ')}): "
            f"{(ped_a.get('how_it_makes_money') or '')[:160]} "
            f"By contrast, {(ped_b.get('how_it_makes_money') or '')[:160]}"
        )
    else:
        summary = (
            f"{a} vs {b}: compare business type ({axes[a].get('business_type')} vs {axes[b].get('business_type')}), "
            f"moat durability ({axes[a].get('moat_durability')} vs {axes[b].get('moat_durability')}), "
            f"growth modes, capital intensity, and industry value drivers — not ratios alone."
        )
    return {
        "ok": True,
        "companies": labels,
        "axes": axes,
        "summary": summary,
        "confidence": 0.8,
        "fabricated": False,
        "policy": "business_axes_not_ratios_only",
    }


def re_search_profitability(qlow: str) -> bool:
    return any(
        k in (qlow or "")
        for k in (
            "more profitable",
            "higher margins",
            "higher margin",
            "earn higher",
            "earns higher",
            "profitability",
        )
    )


def industry_for_question(question: str) -> str:
    return classify_industry(question=question)
