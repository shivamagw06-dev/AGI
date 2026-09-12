"""Soft adapters — wrap IO-01 / CIO-01 packs into shared OfficeResponse."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from office_sdk.contracts import (
    confidence_summary,
    evidence_reference,
    flatten_blocks,
    normalize_sections,
    office_metadata,
    office_response,
    provenance_bundle,
)
from office_sdk.schema import DOMAIN_PORTFOLIO, DOMAIN_RESEARCH


def wrap_io_response(
    pack: Mapping[str, Any],
    *,
    request: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    irp = pack.get("irp") if isinstance(pack.get("irp"), dict) else dict(pack)
    sections = normalize_sections(irp.get("sections") or pack.get("sections") or [])
    conf_raw = irp.get("confidence") or pack.get("confidence") or {}
    if isinstance(conf_raw, dict) and "by_module" in conf_raw:
        conf = confidence_summary(
            mean_confidence=float(conf_raw.get("mean_confidence") or 0.0),
            by_module=list(conf_raw.get("by_module") or []),
            ok_count=int(conf_raw.get("modules_ok") or 0),
            total=int(conf_raw.get("modules_total") or 0),
        )
    else:
        conf = confidence_summary()

    refs = []
    for r in irp.get("evidence_references") or pack.get("evidence_references") or []:
        if not isinstance(r, Mapping):
            continue
        refs.append(
            evidence_reference(
                str(r.get("evidence_id") or r.get("id") or ""),
                module=str(r.get("module") or ""),
                confidence=float(r.get("confidence") or 0.0)
                if isinstance(r.get("confidence"), (int, float))
                else 0.0,
                reporting_period=r.get("reporting_period"),
                ticker=r.get("ticker") or irp.get("ticker") or pack.get("ticker"),
            )
        )

    modules_invoked = list(irp.get("modules_invoked") or pack.get("modules_invoked") or [])
    modules_ok = list(irp.get("modules_ok") or pack.get("modules_ok") or [])
    meta = office_metadata(
        office_id="io-01",
        workstream_id="IO-01",
        product="Investment Office",
        version=str(pack.get("version") or irp.get("version") or "io-01"),
        domain=DOMAIN_RESEARCH,
        role="single_company_research_orchestration",
        orchestrates_only=True,
        compares_only=False,
        buy_sell=False,
        valuation=False,
        recalculates=False,
        invents_conclusions=False,
    )
    return office_response(
        metadata=meta,
        request=request,
        report_type="institutional_research_package",
        sections=sections,
        confidence=conf,
        provenance=provenance_bundle(
            blocks=flatten_blocks(sections),
            references=refs,
            modules_invoked=modules_invoked,
            modules_ok=modules_ok,
        ),
        routing=irp.get("routing") or pack.get("routing") or {},
        assembly_ms=float(irp.get("assembly_ms") or pack.get("assembly_ms") or 0.0),
        payload={
            "ticker": irp.get("ticker") or pack.get("ticker"),
            "package_type": irp.get("package_type") or pack.get("package_type"),
            "native": {
                "ok": pack.get("ok"),
                "workstream_id": pack.get("workstream_id"),
                "guardrails": irp.get("guardrails") or pack.get("guardrails"),
            },
        },
        ok=bool(pack.get("ok", True)),
        error=pack.get("error"),
    )


def wrap_po_response(
    pack: Mapping[str, Any],
    *,
    request: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """If a native PO pack already is an OfficeResponse, pass through; else wrap lightly."""
    if isinstance(pack, Mapping) and pack.get("schema") == "office_sdk.office_response.v1":
        out = dict(pack)
        if request:
            out["request"] = dict(request)
        return out
    # Native get_portfolio shape
    if isinstance(pack.get("office_response"), Mapping):
        return wrap_po_response(pack["office_response"], request=request)
    return office_response(
        metadata=office_metadata(
            office_id="po-01",
            workstream_id="PO-01",
            product="Portfolio Office",
            version=str(pack.get("version") or "po-01"),
            domain=DOMAIN_PORTFOLIO,
            role="canonical_portfolio_state",
            buy_sell=False,
            valuation=False,
            recalculates=False,
        ),
        request=request,
        report_type="portfolio_state_report",
        payload=dict(pack),
        ok=bool(pack.get("ok", True)),
        error=pack.get("error"),
    )


def wrap_cio_response(
    pack: Mapping[str, Any],
    *,
    request: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    icr = pack.get("icr") if isinstance(pack.get("icr"), dict) else dict(pack)
    sections = normalize_sections(icr.get("sections") or pack.get("sections") or [])
    conf_raw = icr.get("confidence") or pack.get("confidence") or {}
    conf = confidence_summary(
        mean_confidence=float(conf_raw.get("mean_confidence") or 0.0),
        by_company_module=list(conf_raw.get("by_company_module") or []),
        ok_count=int(conf_raw.get("ok_count") or 0),
        total=int(conf_raw.get("total") or 0),
    )
    refs = []
    for r in icr.get("evidence_references") or pack.get("evidence_references") or []:
        if not isinstance(r, Mapping):
            continue
        refs.append(
            evidence_reference(
                str(r.get("evidence_id") or r.get("id") or ""),
                module=str(r.get("module") or ""),
                confidence=float(r.get("confidence") or 0.0)
                if isinstance(r.get("confidence"), (int, float))
                else 0.0,
                reporting_period=r.get("reporting_period"),
                ticker=r.get("ticker"),
            )
        )
    modules_invoked = list(icr.get("modules_invoked") or pack.get("modules_invoked") or [])
    meta = office_metadata(
        office_id="cio-01",
        workstream_id="CIO-01",
        product="Comparative Intelligence Office",
        version=str(pack.get("version") or icr.get("version") or "cio-01"),
        domain=DOMAIN_RESEARCH,
        role="cross_company_comparison_orchestration",
        orchestrates_only=True,
        compares_only=True,
        buy_sell=False,
        valuation=False,
        recalculates=False,
        invents_conclusions=False,
    )
    return office_response(
        metadata=meta,
        request=request,
        report_type="institutional_comparison_report",
        sections=sections,
        confidence=conf,
        provenance=provenance_bundle(
            blocks=flatten_blocks(sections),
            references=refs,
            modules_invoked=modules_invoked,
            modules_ok=modules_invoked,
        ),
        routing=icr.get("routing") or pack.get("routing") or {},
        assembly_ms=float(icr.get("assembly_ms") or pack.get("assembly_ms") or 0.0),
        payload={
            "tickers": icr.get("tickers") or pack.get("tickers"),
            "comparison_type": icr.get("comparison_type") or pack.get("comparison_type"),
            "key_differences": icr.get("key_differences") or pack.get("key_differences"),
            "native": {
                "ok": pack.get("ok"),
                "workstream_id": pack.get("workstream_id"),
                "guardrails": icr.get("guardrails") or pack.get("guardrails"),
            },
        },
        ok=bool(pack.get("ok", True)),
        error=pack.get("error"),
    )
