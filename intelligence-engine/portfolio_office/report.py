"""Portfolio State Report (PSR) — Office SDK contracts only."""

from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional

from office_sdk.contracts import (
    confidence_summary,
    evidence_block,
    evidence_reference,
    flatten_blocks,
    office_metadata,
    office_request,
    office_response,
    office_section,
    provenance_bundle,
)
from office_sdk.schema import DOMAIN_PORTFOLIO
from portfolio_office.schema import (
    PO01_OFFICE_ID,
    PO01_PRODUCT,
    PO01_VERSION,
    PO01_WORKSTREAM_ID,
    PSR_SECTION_TITLES,
    PSR_SECTIONS,
)
from portfolio_office.service import compute_state


def build_psr(
    portfolio_id: str,
    *,
    question: Optional[str] = None,
    fire05_map: Optional[Dict[str, Dict[str, Any]]] = None,
    fire06_map: Optional[Dict[str, Dict[str, Any]]] = None,
    request: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    state = compute_state(portfolio_id, fire05_map=fire05_map, fire06_map=fire06_map)
    pf = state["portfolio"]
    meta_pf = pf.get("metadata") or {}
    exposures = state["exposures"]
    concentration = state["concentration"]
    quality = state["quality"]
    execution = state["execution"]
    conf = state["confidence"]

    def blk(text: str, module: str, eids=None, confidence=0.0, period=None, kind="state"):
        return evidence_block(
            text,
            module=module,
            evidence_ids=list(eids or []),
            confidence=float(confidence or 0.0),
            reporting_period=period,
            tickers=[],
            kind=kind,
        )

    sections = []
    section_map: dict[str, list] = {}

    totals = pf.get("totals") or {}
    section_map["portfolio_summary"] = [
        blk(
            (
                f"Portfolio {meta_pf.get('name')} ({pf.get('portfolio_id')}) "
                f"base={meta_pf.get('base_currency')} status={meta_pf.get('status')} "
                f"holdings={len(pf.get('holdings') or [])} "
                f"total_mv={totals.get('total_market_value')} "
                f"equity_mv={totals.get('equity_market_value')} cash={totals.get('cash_balance')}. "
                "PO-01 presents portfolio state only; no recommendations."
            ),
            "PO-01",
            confidence=float(conf.get("mean_confidence") or 0.0),
            kind="summary",
        )
    ]

    hold_blocks = []
    for h in pf.get("holdings") or []:
        hold_blocks.append(
            blk(
                (
                    f"{h.get('ticker')} ({h.get('company')}): qty={h.get('quantity')} "
                    f"mv={h.get('current_market_value')} weight={float(h.get('weight') or 0):.4f} "
                    f"sector={h.get('sector')} country={h.get('country')} mcap={h.get('market_cap_bucket')}"
                ),
                "PO-01",
                confidence=1.0,
                kind="holding",
            )
        )
    section_map["holdings"] = hold_blocks or [blk("No holdings.", "PO-01", confidence=0.0)]

    cash = pf.get("cash") or {}
    section_map["cash"] = [
        blk(
            f"Cash balance={cash.get('balance')} {cash.get('currency')} weight={float(cash.get('weight') or 0):.4f}",
            "PO-01",
            confidence=1.0,
            kind="cash",
        )
    ]

    def exposure_blocks(key: str):
        rows = exposures.get(key) or []
        if not rows:
            return [blk(f"No {key} exposure rows.", "PO-01", confidence=0.0)]
        return [
            blk(f"{r.get('name')}: weight={float(r.get('weight') or 0):.4f}", "PO-01", confidence=1.0, kind="exposure")
            for r in rows
        ]

    section_map["sector_exposure"] = exposure_blocks("sector")
    section_map["industry_exposure"] = exposure_blocks("industry")
    section_map["country_exposure"] = exposure_blocks("country")
    section_map["market_cap_distribution"] = exposure_blocks("market_cap")

    q_blocks = [
        blk(
            (
                f"Portfolio quality (FIRE-06 weight-average)="
                f"{quality.get('portfolio_quality_score')}; "
                f"coverage={quality.get('holdings_covered')}/{quality.get('holdings_total')}; "
                f"confidence={float(quality.get('confidence') or 0):.2f}"
            ),
            "FIRE-06",
            eids=[r["evidence_id"] for r in (quality.get("evidence_references") or [])[:8]],
            confidence=float(quality.get("confidence") or 0.0),
            kind="quality",
        )
    ]
    for p in quality.get("pillar_averages") or []:
        q_blocks.append(
            blk(
                f"Pillar {p.get('pillar')}: weight_avg={p.get('weight_average_score')} coverage={p.get('weight_coverage')}",
                "FIRE-06",
                confidence=float(quality.get("confidence") or 0.0),
                kind="quality",
            )
        )
    section_map["business_quality_distribution"] = q_blocks

    e_blocks = [
        blk(
            (
                f"Execution (FIRE-05): portfolio_score={execution.get('portfolio_execution_score')}; "
                f"delivered_weight={execution.get('delivered_weight')}; "
                f"outstanding_weight={execution.get('outstanding_weight')}; "
                f"coverage={execution.get('holdings_covered')}/{execution.get('holdings_total')}"
            ),
            "FIRE-05",
            eids=[r["evidence_id"] for r in (execution.get("evidence_references") or [])[:8]],
            confidence=float(execution.get("confidence") or 0.0),
            kind="execution",
        )
    ]
    for s in execution.get("status_weight_distribution") or []:
        e_blocks.append(
            blk(
                f"Status {s.get('status')}: weight={float(s.get('weight') or 0):.4f}",
                "FIRE-05",
                confidence=float(execution.get("confidence") or 0.0),
                kind="execution",
            )
        )
    section_map["management_execution_distribution"] = e_blocks

    largest = concentration.get("largest_position") or {}
    section_map["concentration"] = [
        blk(
            (
                f"Holdings={concentration.get('number_of_holdings')}; "
                f"largest={largest.get('ticker')} ({float(largest.get('weight') or 0):.4f}); "
                f"top5={float(concentration.get('top_5_weight') or 0):.4f}; "
                f"top10={float(concentration.get('top_10_weight') or 0):.4f}; "
                f"HHI={float(concentration.get('hhi') or 0):.6f}"
            ),
            "PO-01",
            confidence=1.0,
            kind="concentration",
        )
    ]

    section_map["confidence_summary"] = [
        blk(
            f"Mean confidence={float(conf.get('mean_confidence') or 0):.2f} "
            f"(quality={conf.get('quality_confidence')}, execution={conf.get('execution_confidence')})",
            "PO-01",
            confidence=float(conf.get("mean_confidence") or 0.0),
            kind="confidence",
        )
    ]

    refs = []
    for r in (quality.get("evidence_references") or []) + (execution.get("evidence_references") or []):
        refs.append(
            evidence_reference(
                str(r.get("evidence_id")),
                module=str(r.get("module") or ""),
                confidence=float(r.get("confidence") or 0.0)
                if isinstance(r.get("confidence"), (int, float))
                else 0.0,
                reporting_period=r.get("reporting_period"),
                ticker=r.get("ticker"),
            )
        )
    # dedupe
    seen = set()
    uniq_refs = []
    for r in refs:
        key = (r.get("ticker"), r.get("module"), r.get("evidence_id"))
        if key in seen:
            continue
        seen.add(key)
        uniq_refs.append(r)

    section_map["evidence_references"] = [
        blk(
            f"{r.get('ticker')}: {r.get('evidence_id')} ← {r.get('module')} confidence={float(r.get('confidence') or 0):.2f}",
            str(r.get("module") or "PO-01"),
            eids=[r.get("evidence_id")],
            confidence=float(r.get("confidence") or 0.0),
            period=r.get("reporting_period"),
            kind="reference",
        )
        for r in uniq_refs
    ] or [blk("No evidence references from FIRE-05/06 for this portfolio.", "PO-01", confidence=0.0)]

    for i, key in enumerate(PSR_SECTIONS, start=1):
        sections.append(
            office_section(
                key,
                title=PSR_SECTION_TITLES.get(key, key),
                order=i,
                blocks=section_map.get(key) or [],
            )
        )

    assembly_ms = (time.perf_counter() - t0) * 1000.0
    metadata = office_metadata(
        office_id=PO01_OFFICE_ID,
        workstream_id=PO01_WORKSTREAM_ID,
        product=PO01_PRODUCT,
        version=PO01_VERSION,
        domain=DOMAIN_PORTFOLIO,
        role="canonical_portfolio_state",
        orchestrates_only=True,
        compares_only=False,
        buy_sell=False,
        valuation=False,
        recalculates=False,
        invents_conclusions=False,
        extras={"optimises": False, "rebalances": False, "snapshots_immutable": True},
    )
    req = dict(request) if request else office_request(
        office_id=PO01_OFFICE_ID,
        intent="portfolio_state",
        question=question,
        options={"portfolio_id": portfolio_id},
    )
    conf_sum = confidence_summary(
        mean_confidence=float(conf.get("mean_confidence") or 0.0),
        by_module=[
            {"module": "FIRE-06", "confidence": float(quality.get("confidence") or 0.0)},
            {"module": "FIRE-05", "confidence": float(execution.get("confidence") or 0.0)},
        ],
        ok_count=int(quality.get("holdings_covered") or 0) + int(execution.get("holdings_covered") or 0),
        total=int(quality.get("holdings_total") or 0) + int(execution.get("holdings_total") or 0),
    )
    resp = office_response(
        metadata=metadata,
        request=req,
        report_type="portfolio_state_report",
        sections=sections,
        confidence=conf_sum,
        provenance=provenance_bundle(
            blocks=flatten_blocks(sections),
            references=uniq_refs,
            modules_invoked=["FIRE-05", "FIRE-06", "PO-01"],
            modules_ok=["FIRE-05", "FIRE-06", "PO-01"],
        ),
        routing={"intent": "portfolio_state", "portfolio_id": portfolio_id},
        assembly_ms=assembly_ms,
        payload={
            "portfolio_id": pf.get("portfolio_id"),
            "portfolio": pf,
            "exposures": exposures,
            "concentration": concentration,
            "quality": quality,
            "execution": execution,
            "psr": {
                "schema": "po01.portfolio_state_report.v1",
                "sections": sections,
            },
        },
        ok=True,
    )
    return resp
