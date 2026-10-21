"""Ingest normalised Upstox fundamentals through the DQIV warehouse gateway."""

from __future__ import annotations

from typing import Any, Optional

from upstox_fundamentals.models import SOURCE
from upstox_fundamentals import normalize


def _is_capiq(row: dict[str, Any]) -> bool:
    source = str(row.get("source") or "").strip().lower()
    return source.startswith(("capital_iq", "capiq", "capital iq", "s&p capital iq"))


def _existing_for_symbol(tab: str, symbol: str) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    return store.all_rows(tab, entity=symbol, limit=200)


def _exclude_capiq_statement_collisions(
    tab: str, rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Never let a secondary Upstox refresh replace a CapIQ statement row."""
    keys = ("symbol", "statement_type", "fiscal_year") if tab == "financials_annual" else (
        "symbol", "statement_type", "fiscal_period",
    )
    protected: set[tuple[str, ...]] = set()
    for symbol in {str(row.get("symbol") or "").upper() for row in rows}:
        if not symbol:
            continue
        for existing in _existing_for_symbol(tab, symbol):
            if _is_capiq(existing):
                protected.add(tuple(str(existing.get(key) or "").upper() for key in keys))
    safe = [
        row for row in rows
        if tuple(str(row.get(key) or "").upper() for key in keys) not in protected
    ]
    return safe, len(rows) - len(safe)


def _split_annual_quarterly(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    annual: list[dict[str, Any]] = []
    quarterly: list[dict[str, Any]] = []
    for row in rows:
        freq = str(row.get("statement_frequency") or "").upper()
        if freq == "QUARTERLY" or row.get("quarter"):
            if not row.get("fiscal_period"):
                continue
            quarterly.append(row)
        else:
            if not row.get("fiscal_year"):
                continue
            annual.append(row)
    return annual, quarterly


def ingest_profile(row: dict[str, Any], *, actor: str = "uifi") -> dict[str, Any]:
    from institutional_warehouse import gateway

    if not row:
        return {"ok": False, "error": "empty_profile"}
    proposed_master = {k: v for k, v in row.items() if k not in {
        "as_of", "confidence", "dqiv_status", "validation_notes", "provider_version",
    }}
    existing = next(iter(_existing_for_symbol("company_master", str(row.get("symbol") or ""))), None)
    master = proposed_master
    if existing:
        # CapIQ and prior canonical imports remain authoritative for descriptive,
        # classification and valuation fields. Upstox may only fill missing identity.
        master = {
            "company_id": existing.get("company_id") or row.get("company_id"),
            "symbol": existing.get("symbol") or row.get("symbol"),
            "company_name": existing.get("company_name") or row.get("company_name"),
            "source": existing.get("source") or SOURCE,
        }
        for field in ("isin", "instrument_key"):
            master[field] = existing.get(field) or row.get(field)
    history = {
        k: row.get(k) for k in (
            "symbol", "as_of", "isin", "instrument_key", "company_name", "legal_name",
            "sector", "industry", "sub_industry", "business_description",
            "market_cap_inr", "market_cap_usd", "sector_market_cap_inr",
            "sector_market_cap_usd", "website", "city", "state", "country",
            "listing_date", "employee_count", "confidence", "dqiv_status",
            "validation_notes", "source",
        )
    }
    result = {
        "ok": True,
        "profile_history": gateway.write(
            "profile_history", [history], source=SOURCE, actor=actor, reason="uifi:profile_history",
        ),
    }
    # Avoid even touching the canonical row when Upstox has no missing identity to fill.
    if not existing or any(existing.get(field) in (None, "") and master.get(field) for field in ("isin", "instrument_key")):
        result["company_master"] = gateway.write(
            "company_master", [master], source=str(master.get("source") or SOURCE),
            actor=actor, reason="uifi:profile_identity_fill",
        )
    else:
        result["company_master"] = {"ok": True, "written": 0, "preserved_existing": True}
    return result


def ingest_statements(rows: list[dict[str, Any]], *, actor: str = "uifi") -> dict[str, Any]:
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_statement_rows"}
    annual, quarterly = _split_annual_quarterly(rows)
    annual, annual_protected = _exclude_capiq_statement_collisions("financials_annual", annual)
    quarterly, quarterly_protected = _exclude_capiq_statement_collisions("financials_quarterly", quarterly)
    out: dict[str, Any] = {
        "ok": True,
        "annual_rows": len(annual),
        "quarterly_rows": len(quarterly),
        "capiq_rows_preserved": annual_protected + quarterly_protected,
    }
    if annual:
        out["financials_annual"] = gateway.write(
            "financials_annual", annual, source=SOURCE, actor=actor,
            reason="uifi:statements", reported_unit=None,
        )
    if quarterly:
        out["financials_quarterly"] = gateway.write(
            "financials_quarterly", quarterly, source=SOURCE, actor=actor,
            reason="uifi:statements",
        )
    # Trigger HVIE forward rebuild for affected symbols (best-effort).
    try:
        from historical_valuation_intelligence.hooks import after_statements_written

        out["hvie_forward"] = after_statements_written(annual + quarterly)
    except Exception as exc:
        out["hvie_forward"] = {"ok": False, "error": str(exc)[:160]}
    return out


def ingest_shareholding(rows: list[dict[str, Any]], *, actor: str = "uifi") -> dict[str, Any]:
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_shareholding_rows"}
    return {
        "ok": True,
        "ownership": gateway.write(
            "ownership", rows, source=SOURCE, actor=actor, reason="uifi:shareholding",
        ),
    }


def ingest_corporate_actions(rows: list[dict[str, Any]], *, actor: str = "uifi") -> dict[str, Any]:
    """Secondary write — conflicts with NSE/LIDI are recorded by gateway conflict detection."""
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_ca_rows"}
    return {
        "ok": True,
        "corporate_actions": gateway.write(
            "corporate_actions", rows, source=SOURCE, actor=actor,
            reason="uifi:corporate_actions_secondary",
            detect_conflicts=True,
        ),
        "role": "secondary_validation",
    }


def ingest_competitors(rows: list[dict[str, Any]], *, actor: str = "uifi") -> dict[str, Any]:
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_peer_rows"}
    return {
        "ok": True,
        "peer_relationships": gateway.write(
            "peer_relationships", rows, source=SOURCE, actor=actor, reason="uifi:competitors",
        ),
    }


def ingest_bundle(body: dict[str, Any], *, actor: Optional[str] = None) -> dict[str, Any]:
    """Accept a multi-dataset payload from the Node connector and persist."""
    actor = actor or str(body.get("actor") or "uifi")
    dataset = str(body.get("dataset") or body.get("endpoint") or "").strip().lower()
    companies = body.get("companies") if isinstance(body.get("companies"), list) else [body]
    results: list[dict[str, Any]] = []
    totals = {"companies": 0, "rows": 0}

    for company in companies:
        if not isinstance(company, dict):
            continue
        totals["companies"] += 1
        ds = dataset or str(company.get("dataset") or "").strip().lower()
        if ds in {"profile", "company-profile"}:
            row = normalize.normalise_profile(company)
            res = ingest_profile(row, actor=actor)
            totals["rows"] += 1 if row else 0
            results.append({"symbol": company.get("symbol"), "dataset": "profile", **res})
        elif ds in {"income-statement", "balance-sheet", "cash-flow", "statements"}:
            if ds == "statements":
                merged: list[dict[str, Any]] = []
                for kind in ("income-statement", "balance-sheet", "cash-flow"):
                    part = company.get(kind) or company.get(kind.replace("-", "_"))
                    if part:
                        merged.extend(normalize.normalise_statements(
                            {**company, "data": part.get("data", part) if isinstance(part, dict) else part},
                            kind=kind,
                        ))
                rows = normalize.merge_statement_rows(merged)
            else:
                rows = normalize.normalise_statements(company, kind=ds)
                # Allow Node to send all three in one company blob for merge.
                extras = []
                for kind in ("income-statement", "balance-sheet", "cash-flow"):
                    if kind == ds:
                        continue
                    part = company.get(kind)
                    if part:
                        extras.extend(normalize.normalise_statements(
                            {**company, "data": part.get("data", part) if isinstance(part, dict) else part},
                            kind=kind,
                        ))
                if extras:
                    rows = normalize.merge_statement_rows(rows + extras)
            res = ingest_statements(rows, actor=actor)
            totals["rows"] += len(rows)
            results.append({"symbol": company.get("symbol"), "dataset": ds, **res})
        elif ds in {"share-holdings", "shareholding", "ownership"}:
            rows = normalize.normalise_shareholding(company)
            res = ingest_shareholding(rows, actor=actor)
            totals["rows"] += len(rows)
            results.append({"symbol": company.get("symbol"), "dataset": "shareholding", **res})
        elif ds in {"corporate-actions", "corporate_actions"}:
            rows = normalize.normalise_corporate_actions(company)
            res = ingest_corporate_actions(rows, actor=actor)
            totals["rows"] += len(rows)
            results.append({"symbol": company.get("symbol"), "dataset": "corporate-actions", **res})
        elif ds in {"competitors", "peers"}:
            rows = normalize.normalise_competitors(company)
            res = ingest_competitors(rows, actor=actor)
            totals["rows"] += len(rows)
            results.append({"symbol": company.get("symbol"), "dataset": "competitors", **res})
        else:
            results.append({
                "symbol": company.get("symbol"),
                "ok": False,
                "error": f"unknown_dataset:{ds}",
            })

    ok = any(r.get("ok") for r in results)
    return {"ok": ok, "engine": "UIFI", "totals": totals, "results": results[:200]}
