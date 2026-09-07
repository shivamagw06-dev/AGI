"""Structured failure diagnostics for Evaluation Lab runs."""

from __future__ import annotations

from typing import Any


def classify_failure(
    *,
    pack_present: bool,
    price_pkg: dict[str, Any] | None,
    cid: dict[str, Any] | None,
    company_analysis: dict[str, Any] | None,
    ide_pkg: dict[str, Any] | None,
    metrics: dict[str, Any] | None,
    errors: list[str] | None = None,
) -> dict[str, Any] | None:
    """Return a structured failure record, or None when the run is healthy enough."""
    errors = list(errors or [])
    price = price_pkg if isinstance(price_pkg, dict) else {}
    snap = price.get("snapshot") if isinstance(price.get("snapshot"), dict) else {}
    ide = ide_pkg if isinstance(ide_pkg, dict) else {}
    gate = ide.get("institutional_readiness_gate") if isinstance(ide.get("institutional_readiness_gate"), dict) else {}
    m = metrics if isinstance(metrics, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}

    # Hard pipeline failures first
    if any(e.startswith("decision_engine:") for e in errors) or ide.get("error"):
        return {
            "status": "FAILED",
            "reason": "DECISION_ENGINE_ERROR",
            "stage": "Decision Engine",
            "retryable": True,
            "detail": ide.get("error") or next((e for e in errors if e.startswith("decision_engine:")), None),
        }
    if any(e.startswith("price:") for e in errors) or price.get("error"):
        return {
            "status": "FAILED",
            "reason": "LIVE_PRICE_UNAVAILABLE",
            "stage": "Groww Live Price",
            "retryable": True,
            "detail": price.get("error") or price.get("reason"),
        }
    if snap and snap.get("ltp") is None and not pack_present:
        return {
            "status": "FAILED",
            "reason": "PRICE_AND_PACK_MISSING",
            "stage": "Market Snapshot",
            "retryable": True,
            "detail": "No LTP and no company pack",
        }

    # Evidence / gate failures (actionable for ingestion)
    missing = list(gate.get("missing") or [])
    missing_l = " ".join(str(x).lower() for x in missing)
    cards = gate.get("diagnostic_cards") or gate.get("checklist") or []
    for c in cards:
        if not isinstance(c, dict) or c.get("present"):
            continue
        key = str(c.get("key") or "").lower()
        label = str(c.get("label") or key)
        if key in {"ownership", "shareholding"} or "sharehold" in label.lower():
            return {
                "status": "FAILED",
                "reason": "SHAREHOLDING_MISSING",
                "stage": "Ownership Intelligence",
                "retryable": True,
                "detail": label,
            }
        if key in {"financials", "filings"} or "financial" in label.lower() or "filing" in label.lower():
            return {
                "status": "FAILED",
                "reason": "FINANCIALS_OR_FILING_MISSING",
                "stage": "Financial Intelligence",
                "retryable": True,
                "detail": label,
            }
        if key == "valuation" or "valuation" in label.lower():
            return {
                "status": "FAILED",
                "reason": "VALUATION_MISSING",
                "stage": "Valuation Intelligence",
                "retryable": True,
                "detail": label,
            }

    if "sharehold" in missing_l or "ownership" in missing_l:
        return {
            "status": "FAILED",
            "reason": "SHAREHOLDING_MISSING",
            "stage": "Ownership Intelligence",
            "retryable": True,
            "detail": missing[:4],
        }

    if m.get("gate") == "FAIL" or gate.get("status") == "FAILED":
        return {
            "status": "FAILED",
            "reason": "INSTITUTIONAL_GATE_FAILED",
            "stage": "Institutional Readiness Gate",
            "retryable": True,
            "detail": gate.get("reason") or gate.get("band") or m.get("readiness_band"),
        }

    if cid.get("error"):
        return {
            "status": "FAILED",
            "reason": "CID_BUILD_ERROR",
            "stage": "Company Intelligence Dossier",
            "retryable": True,
            "detail": cid.get("error"),
        }
    if ca.get("error"):
        return {
            "status": "FAILED",
            "reason": "COMPANY_ANALYSIS_ERROR",
            "stage": "Company Analysis",
            "retryable": True,
            "detail": ca.get("error"),
        }

    if errors:
        return {
            "status": "FAILED",
            "reason": "PIPELINE_ERROR",
            "stage": "Evaluation Pipeline",
            "retryable": True,
            "detail": errors[:3],
        }

    # Soft incomplete evidence without hard gate fail — not a failure for runner health
    return None
