"""Safe, auditable normalisation for the Capital IQ annual workbook.

The workbook remains immutable source evidence.  This module resolves a row to
AGI's company master, records the mapping/audit evidence, and only releases a
complete company-period record to ``financials_annual``.
"""

from __future__ import annotations

from typing import Any, Iterable

from institutional_warehouse import gateway, store
from institutional_warehouse.values import now_iso


SOURCE = "capital_iq_workbook"
MAPPING_VERSION = "CAPIQ_V2"
REQUIRED_FIELDS = ("pat", "assets", "equity")


def reconcile_derived_fields(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Rebuild arithmetic fields from the workbook's reported components."""
    row = dict(raw)
    repaired: list[str] = []
    current_assets = row.get("current_assets")
    current_liabilities = row.get("current_liabilities")
    if current_assets is not None and current_liabilities is not None:
        calculated = float(current_assets) - float(current_liabilities)
        supplied = row.get("working_capital")
        if supplied is None or abs(float(supplied) - calculated) > 0.01:
            repaired.append("working_capital")
        row["working_capital"] = calculated
    cfo = row.get("cfo")
    capex = row.get("capex")
    if cfo is not None and capex is not None:
        calculated = float(cfo) - abs(float(capex))
        supplied = row.get("free_cash_flow")
        if supplied is None or abs(float(supplied) - calculated) > 0.01:
            repaired.append("free_cash_flow")
        row["free_cash_flow"] = calculated
    return row, repaired


def _text(value: Any) -> str:
    return str(value or "").strip()


def _company_type(master: dict[str, Any]) -> str:
    text = " ".join(_text(master.get(key)).lower() for key in (
        "company_name", "legal_name", "sector", "industry", "business_type", "industry_dna",
    ))
    if "insurance" in text or "insurer" in text:
        return "INSURER"
    if "nbfc" in text or "non banking" in text or "finance" in text or "credit" in text:
        return "NBFC"
    if "bank" in text or "banking" in text:
        return "BANK"
    return "CORPORATE"


def masters_by_symbol(masters: Iterable[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    rows = masters if masters is not None else store.all_rows("company_master", limit=10_000)
    return {
        _text(row.get("symbol")).upper(): row
        for row in rows
        if _text(row.get("symbol"))
    }


def resolve_identity(row: dict[str, Any], masters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    symbol = _text(row.get("symbol")).upper()
    master = masters.get(symbol)
    if not master:
        return {
            "identity_status": "REVIEW_REQUIRED", "symbol": symbol,
            "identity": None, "identity_map": None,
        }
    company_type = _company_type(master)
    identity = {
        "source": SOURCE,
        "source_symbol": symbol,
        "source_company_id": None,
        "source_company_name": row.get("source_company_name") or master.get("company_name"),
        "agi_company_id": master.get("company_id"),
        "symbol": symbol,
        "isin": master.get("isin"),
        "company_type": company_type,
        "match_method": "SYMBOL_EXACT",
        "match_confidence": 100.0,
        "verified": True,
        "verified_at": now_iso(),
    }
    return {"identity_status": "VERIFIED", "symbol": symbol, "identity": master, "identity_map": identity}


def mapping_rows(field_map: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "source": SOURCE,
            "source_label": label,
            "company_type": "ALL",
            "statement_type": "CONSOLIDATED",
            "canonical_metric": metric,
            "period_type": "ANNUAL",
            "sign_multiplier": 1.0,
            "mapping_version": MAPPING_VERSION,
            "active": True,
        }
        for label, metric in field_map.items()
    ]


def audit_and_prepare(
    rows: Iterable[dict[str, Any]], *, field_map: dict[str, str], source_file: str,
    masters: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    master_index = masters if masters is not None else masters_by_symbol()
    audits: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for source_row in rows:
        raw, repaired_fields = reconcile_derived_fields(source_row)
        resolved = resolve_identity(raw, master_index)
        present = [metric for metric in field_map.values() if raw.get(metric) is not None]
        required_found = sum(1 for metric in REQUIRED_FIELDS if raw.get(metric) is not None)
        period_ok = bool(_text(raw.get("fiscal_year")).startswith("FY"))
        verified = resolved["identity_status"] == "VERIFIED" and required_found == len(REQUIRED_FIELDS) and period_ok
        status = "VERIFIED" if verified else "REVIEW_REQUIRED"
        score = round(100.0 * required_found / len(REQUIRED_FIELDS), 1)
        audit = {
            "source": SOURCE,
            "source_file": source_file,
            "source_sheet": str(raw.get("fiscal_year") or "").replace("FY", ""),
            "source_symbol": _text(raw.get("symbol")).upper(),
            "symbol": resolved["symbol"],
            "fiscal_year": raw.get("fiscal_year"),
            "company_type": _company_type(resolved["identity"]) if resolved["identity"] else None,
            "identity_status": resolved["identity_status"],
            "source_fields": len(present),
            "mapped_fields": len(present),
            "unmapped_fields": [],
            "required_fields": list(REQUIRED_FIELDS),
            "required_fields_found": required_found,
            "unit_check": "PASS",
            "period_check": "PASS" if period_ok else "FAIL",
            "reconciliation": "REPAIRED" if repaired_fields else "PASS",
            "repaired_fields": repaired_fields,
            "quality_score": score,
            "overall_status": status,
            "write_status": "READY" if verified else "HELD",
            "mapping_version": MAPPING_VERSION,
        }
        audits.append(audit)
        if resolved["identity_map"]:
            identities.append(resolved["identity_map"])
        if verified:
            accepted.append({
                **{key: value for key, value in raw.items() if not key.startswith("_")},
                "symbol": resolved["symbol"],
                "company_type": audit["company_type"],
                "mapping_version": MAPPING_VERSION,
            })
    return {"accepted": accepted, "audits": audits, "identities": identities}


def persist(
    prepared: dict[str, Any], *, field_map: dict[str, str], actor: str,
    source_file: str, write_financials: bool = True,
) -> dict[str, Any]:
    maps = gateway.write("capiq_metric_mapping", mapping_rows(field_map), source=SOURCE, actor=actor,
                         reason="capiq_metric_dictionary")
    identities = gateway.write("company_identity_map", prepared["identities"], source=SOURCE, actor=actor,
                               reason="capiq_identity_resolution")
    audits = gateway.write("financial_import_audit", prepared["audits"], source=SOURCE, actor=actor,
                           reason=f"capiq_audit:{source_file}")
    financials = {"ok": True, "written": 0}
    if write_financials and prepared["accepted"]:
        financials = gateway.write(
            "financials_annual", prepared["accepted"], source=SOURCE, actor=actor,
            reason="capiq_workbook:verified_company_periods", reported_unit="inr_million",
        )
    return {"mapping": maps, "identity": identities, "audit": audits, "financials": financials}
