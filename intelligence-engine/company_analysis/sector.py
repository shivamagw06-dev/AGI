"""Step 5 — Sector-specific reasoning via SIF + Academy lenses."""

from __future__ import annotations

from typing import Any

from company_analysis.flags import flag_sector
from company_analysis.schema import SECTOR_CONCEPT_LENSES


def analyse_sector(
    *,
    identity: dict[str, Any],
    sif_pkg: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    academy_applied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not flag_sector():
        return {"enabled": False, "bypassed": True}

    sif = sif_pkg or {}
    cid = cid or {}
    sector_id = identity.get("sector_id") or sif.get("sector_id") or (cid.get("sector_framework") or {}).get("sector_id")
    sector_name = identity.get("sector") or sif.get("sector_name") or sector_id
    sk = str(
        sector_id
        or ((academy_applied or {}).get("sector_key") if academy_applied else None)
        or ""
    ).lower()

    priority = list(
        sif.get("priority_metrics")
        or ((cid.get("sector_kpis") or {}).get("priority_metrics") or [])
        or SECTOR_CONCEPT_LENSES.get(sk, ())
    )[:12]

    reasoning: list[str] = []
    if "bank" in sk:
        reasoning = [
            "Banking analysis prioritises CASA, NIM, credit cost, GNPA/NNPA, PCR, loan & deposit growth, liquidity and capital.",
            "ROE is an outcome — only durable if funding advantage and credit costs remain controlled.",
            "Liquidity and CET1 constrain growth optionality in stress.",
        ]
    elif "fmcg" in sk or "staple" in sk:
        reasoning = [
            "FMCG analysis prioritises volume growth, pricing, brand, market share, distribution, advertising and ROIC.",
            "Premium valuation requires evidence of pricing power and cash conversion, not just revenue growth.",
        ]
    elif "it" in sk:
        reasoning = [
            "IT services analysis prioritises utilisation, deal pipeline / TCV, pricing, attrition, AI revenue mix and margin trajectory.",
            "Large-deal ramps can depress near-term margins while supporting medium-term growth.",
        ]
    elif "pharma" in sk or "health" in sk:
        reasoning = [
            "Pharma analysis prioritises US exposure, ANDA pipeline, inspection outcomes, specialty mix and API/formulation balance.",
            "Margin durability depends on product concentration, price erosion and regulatory cadence.",
        ]
    elif "cement" in sk or "material" in sk:
        reasoning = [
            "Cement analysis prioritises capacity, utilisation, fuel/petcoke costs, realisations and regional pricing power.",
            "Volume recovery without pricing discipline rarely sustains ROCE through the cycle.",
        ]
    elif "power" in sk or "utilit" in sk:
        reasoning = [
            "Power analysis prioritises PLF, generation mix, regulated returns, capex cycle and receivable quality.",
            "Thermal vs renewable mix shapes fuel risk and long-term cash conversion.",
        ]
    elif "auto" in sk or "automob" in sk:
        reasoning = [
            "Auto analysis prioritises volumes, mix (PV/CV), EV trajectory, exports and dealer inventory.",
            "Margin resilience depends on commodity costs, model cadence and premium/EV mix shift.",
        ]
    elif "paint" in sk or "decor" in sk:
        reasoning = [
            "Paints analysis prioritises decorative volume, realisations, gross margin, distributor reach and rural mix.",
            "Premium brand strength must show up in pricing power and ROIC, not only top-line growth.",
        ]
    elif "defence" in sk or "defense" in sk or "aerospace" in sk:
        reasoning = [
            "Defence OEM analysis prioritises order book, execution, indigenisation content and government budget cadence.",
            "Working-capital and milestone billing drive cash conversion more than headline order wins.",
        ]
    elif "energy" in sk or "oil" in sk or "refin" in sk:
        reasoning = [
            "Integrated energy analysis prioritises refining cracks, petchem spreads, retail/Jio-style consumer cash flows and upstream linkages.",
            "Conglomerate valuation requires segment-level evidence rather than a single group multiple.",
        ]
    elif "internet" in sk or "consumer" in sk:
        reasoning = [
            "Consumer-internet analysis prioritises GMV, take rate, contribution margin, cohort retention and path to cash profits.",
            "Growth without unit-economic improvement is not an institutional compounding case.",
        ]
    else:
        reasoning = [
            f"Sector lens for {sector_name}: prioritise sector KPIs from SIF and apply Academy concepts to those KPIs.",
        ]

    observed = ((cid.get("sector_kpis") or {}).get("observed") or {}) if isinstance(cid.get("sector_kpis"), dict) else {}
    kpi_notes = []
    for m in priority[:8]:
        val = observed.get(m) if isinstance(observed, dict) else None
        kpi_notes.append({"metric": m, "observed": val, "status": "observed" if val is not None else "missing"})

    covered = sum(1 for k in kpi_notes if k["status"] == "observed")
    coverage = int(round(100 * covered / max(1, len(kpi_notes)))) if kpi_notes else int(bool(sector_id)) * 50

    return {
        "enabled": True,
        "sector_id": sector_id,
        "sector_name": sector_name,
        "priority_metrics": priority,
        "kpi_notes": kpi_notes,
        "reasoning": reasoning,
        "coverage_pct": coverage,
        "sources": ["sif", "cid.sector_framework", "cid.sector_kpis", "academy.sector_lens"],
    }
