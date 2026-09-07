"""Daily / weekly / quarterly Knowledge Factory pipelines."""

from __future__ import annotations

from typing import Any

from knowledge_factory.collectors.bse.client import collect_filings as bse_filings
from knowledge_factory.collectors.fred.client import collect_macro as fred_macro
from knowledge_factory.collectors.groww.client import collect_portfolio
from knowledge_factory.collectors.nse.client import collect_filings as nse_filings
from knowledge_factory.collectors.rbi.client import collect_macro as rbi_macro
from knowledge_factory.collectors.world_bank.client import collect_macro as wb_macro
from knowledge_factory.collectors.yahoo.client import collect_company
from knowledge_factory.fixtures.seed import company_universe, sector_map
from knowledge_factory.normalizers.canonical import normalize_company, normalize_macro
from knowledge_factory.objects.compile import compile_company, compile_macro, compile_sector
from knowledge_factory.producers.accounting.metrics import produce_accounting, produce_business_quality
from knowledge_factory.producers.composite import (
    produce_macro,
    produce_peers,
    produce_portfolio,
    produce_sector,
    produce_timeline,
)
from knowledge_factory.producers.risk.metrics import produce_risk
from knowledge_factory.producers.valuation.metrics import produce_valuation
from knowledge_factory.store import repository as store
from knowledge_factory.validators.pipeline import dedupe_filings, validate_dataset

PIPELINE_VERSION = "kf-pipeline-v1.0.0"


def _publish_or_reject(kind: str, entity: str, dataset: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    verdict = validate_dataset(dataset, required_fields=required, allow_stale=True)
    if not verdict["ok"]:
        return {"published": False, **verdict}
    store.put_validated(kind, entity, {**dataset, "validation": verdict})
    return {"published": True, **verdict}


def run_daily(*, entities: list[str] | None = None, yahoo_live: bool = False) -> dict[str, Any]:
    entities = entities or company_universe()
    collection_failures: list[dict[str, Any]] = []
    validation_failures: list[dict[str, Any]] = []
    companies: list[dict[str, Any]] = []
    by_sector: dict[str, list[dict[str, Any]]] = {}

    # Macro collect
    macro_parts = [rbi_macro(), fred_macro(), wb_macro()]
    for part in macro_parts:
        v = _publish_or_reject("macro_raw", str(part.get("entity")), part)
        if not v["published"]:
            validation_failures.append({"kind": "macro", "entity": part.get("entity"), **v})
    macro_norm = normalize_macro(macro_parts)
    macro_obj = compile_macro(produce_macro(macro_norm.get("series") or {}))
    store.put_object("macro", "GLOBAL", macro_obj)

    # Portfolio / groww
    book = collect_portfolio()
    _publish_or_reject("portfolio", "BOOK", book)
    port = produce_portfolio(book.get("payload") or {})
    store.put_object("portfolio", "BOOK", port)

    for entity in entities:
        yahoo = collect_company(entity, live=yahoo_live)
        if yahoo.get("ok") is False or not yahoo.get("payload"):
            collection_failures.append({"source": "yahoo", "entity": entity, "reason": yahoo.get("reason")})
            # Keep existing validated object if present — do not crash
            existing = store.get_object("company", entity)
            if existing:
                companies.append(existing)
            continue

        verdict = _publish_or_reject("company_market", entity, yahoo, required=())
        if not verdict["published"]:
            validation_failures.append({"entity": entity, **verdict})
            continue

        profile = normalize_company(yahoo)
        prim = profile.get("primitives") or {}
        valuation = produce_valuation(entity, prim)
        accounting = produce_accounting(entity, prim)
        bq = produce_business_quality(entity, valuation)
        risk = produce_risk(entity)

        nse = nse_filings(entity)
        bse = bse_filings(entity)
        filings = dedupe_filings(list((nse.get("payload") or {}).get("filings") or []) + list((bse.get("payload") or {}).get("filings") or []))
        timeline = produce_timeline(entity, filings)

        sector = profile.get("sector") or sector_map().get(entity.upper(), "unknown")
        # peers filled after sector pass — provisional from map
        sector_members = [t for t, s in sector_map().items() if s == sector]
        peers = produce_peers(entity, sector_members)

        evidence_pack = {
            "entity": entity.upper(),
            "current_pe": None,
            "historical_pe": None,
            "risk_drivers": None,
            "coverage": 0.0,
            "quality": 0.0,
            "provenance": "knowledge_factory",
            "version": PIPELINE_VERSION,
        }
        pe_pts = ((valuation.get("metrics") or {}).get("PE") or {}).get("points") or {}
        if pe_pts:
            vals = list(pe_pts.values())
            evidence_pack["current_pe"] = vals[-1]
            evidence_pack["historical_pe"] = round(sum(vals) / len(vals), 4)
        if risk.get("found"):
            evidence_pack["risk_drivers"] = "market_beta,volatility"
            evidence_pack["downside_case"] = -(abs(float(risk.get("var_95_monthly_pct") or 0)) / 100.0)
        evidence_pack["coverage"] = 0.75 if evidence_pack["historical_pe"] is not None else 0.3
        evidence_pack["quality"] = 90.0 if evidence_pack["coverage"] >= 0.7 else 50.0
        evidence_pack["freshness"] = yahoo.get("timestamp")
        evidence_pack["missing_fields"] = valuation.get("insufficient") or []
        evidence_pack["entity_confidence"] = verdict.get("entity_confidence")
        store.put_pack(entity, evidence_pack)

        obj = compile_company(
            entity=entity,
            profile=profile,
            valuation=valuation,
            accounting=accounting,
            business_quality=bq,
            risk=risk,
            peers=peers,
            timeline=timeline,
            evidence_pack=evidence_pack,
        )
        store.put_object("company", entity, obj)
        companies.append(obj)
        by_sector.setdefault(sector, []).append(
            {"entity": entity.upper(), "valuation": valuation, "sector": sector}
        )

    sector_objects = {}
    for sector, rows in by_sector.items():
        sobj = compile_sector(produce_sector(sector, rows))
        store.put_object("sector", sector, sobj)
        sector_objects[sector] = sobj

    report = {
        "pipeline_version": PIPELINE_VERSION,
        "companies_covered": len(store.list_objects("company")),
        "sectors_covered": len(store.list_objects("sector")),
        "macro_covered": 1 if store.get_object("macro", "GLOBAL") else 0,
        "evidence_packs": len(list((store.store_root() / "packs").glob("*.json"))),
        "collection_failures": collection_failures,
        "validation_failures": validation_failures,
        "entities_requested": entities,
    }
    store.put_report("coverage", report)
    store.put_report("daily", {"ok": True, **report})
    return {"ok": True, "pipeline_version": PIPELINE_VERSION, **report, "sector_objects": list(sector_objects)}


def run_weekly() -> dict[str, Any]:
    # Weekly = daily + sector refresh emphasis
    return {"ok": True, "schedule": "weekly", **run_daily()}


def run_quarterly() -> dict[str, Any]:
    return {"ok": True, "schedule": "quarterly", **run_daily()}
