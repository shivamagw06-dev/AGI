"""Governed official-disclosure backfill for commercial-bank valuation KPIs."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from financials_valuation.banking import BANK_KPIS
from financials_valuation.persistence import _rest
from reasoning_providers import OpenAIProvider

CORE_BANKS = {
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "AXISBANK": "Axis Bank",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "SBIN": "State Bank of India",
}
METRICS = {item.key for item in BANK_KPIS} | {
    "rwa", "lcr", "nsfr", "book_value_per_share",
    "tangible_book_value_per_share", "normalized_eps", "fee_income", "dividend_payout",
}
RATIO_METRICS = {
    "loan_growth", "deposit_growth", "casa", "cost_of_deposits", "yield_on_advances",
    "nim", "nii_growth", "cost_to_income", "gnpa", "nnpa", "slippage", "credit_cost",
    "pcr", "roa", "roe", "cet1", "crar", "lcr", "nsfr", "dividend_payout",
}
_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _document_text(document: dict[str, Any]) -> str:
    return str(document.get("text") or document.get("content_text") or document.get("content") or "")


def validate_observation(row: dict[str, Any], *, symbol: str, document: dict[str, Any]) -> dict[str, Any]:
    metric = str(row.get("metric_key") or "").strip().lower()
    issues: list[str] = []
    if metric not in METRICS:
        issues.append("UNSUPPORTED_METRIC")
    try:
        value = float(row.get("value"))
    except (TypeError, ValueError):
        value = 0.0
        issues.append("INVALID_VALUE")
    unit = str(row.get("unit") or "").strip()
    if not unit:
        issues.append("UNIT_REQUIRED")
    if metric in RATIO_METRICS:
        if unit not in {"percent", "decimal"}:
            issues.append("RATIO_UNIT_REQUIRED")
        normalized = value / 100 if unit == "percent" else value
        if not -0.25 <= normalized <= 2.0:
            issues.append("RATIO_OUT_OF_RANGE")
    period_end = str(row.get("period_end") or "")[:10]
    try:
        datetime.fromisoformat(period_end)
    except ValueError:
        issues.append("PERIOD_END_REQUIRED")
    period = str(row.get("period") or "").strip()
    if not period:
        issues.append("PERIOD_REQUIRED")
    excerpt = str(row.get("source_excerpt") or "").strip()[:1000]
    text = _document_text(document)
    if not excerpt or excerpt.lower() not in text.lower():
        issues.append("EXCERPT_NOT_VERBATIM")
    source_url = str(document.get("url") or "").strip()
    if not source_url.startswith(("https://", "http://")):
        issues.append("PUBLIC_SOURCE_URL_REQUIRED")
    published = document.get("published_at") or (document.get("metadata") or {}).get("reporting_period")
    available_at = str(document.get("retrieved_at") or (document.get("metadata") or {}).get("faa_retrieved_at") or _now())
    status = "PROPOSED" if not issues else "QUARANTINED"
    confidence = min(float(row.get("confidence") or 0), 0.85 if status == "PROPOSED" else 0.35)
    return {
        "symbol": symbol,
        "company_name": CORE_BANKS.get(symbol),
        "metric_key": metric,
        "value": value,
        "unit": unit,
        "currency": row.get("currency"),
        "period": period,
        "period_end": period_end or "1900-01-01",
        "frequency": str(row.get("frequency") or "QUARTERLY").upper(),
        "basis": str(row.get("basis") or "REPORTED").upper(),
        "consolidation_scope": str(row.get("consolidation_scope") or "STANDALONE").upper(),
        "annualized": bool(row.get("annualized")),
        "source_id": str(document.get("document_id") or document.get("checksum") or source_url),
        "source_url": source_url,
        "source_title": str(document.get("title") or "")[:500],
        "source_published_at": published if isinstance(published, str) and published[:4].isdigit() else None,
        "available_at": available_at,
        "source_excerpt": excerpt,
        "source_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extraction_method": "OPENAI_STRUCTURED_EXTRACTION",
        "validation_status": status,
        "confidence": max(0.0, min(1.0, confidence)),
        "validation_notes": ";".join(issues) or "AI_EXTRACTED_REQUIRES_INDEPENDENT_VALIDATION",
    }


def extract_document(symbol: str, document: dict[str, Any], *, provider: OpenAIProvider | None = None) -> list[dict[str, Any]]:
    text = _document_text(document).strip()
    if len(text) < 200:
        return []
    model = provider or OpenAIProvider()
    if not model.available():
        raise RuntimeError("OPENAI_API_KEY_MISSING")
    instructions = """You extract reported commercial-bank KPIs from one primary-source document.
Return JSON only: {\"observations\":[...]}. Never calculate, infer, annualize, convert units, or fill a missing value.
Each observation must contain metric_key, value, unit, currency, period, period_end (YYYY-MM-DD), frequency,
basis, consolidation_scope, annualized, source_excerpt, confidence. source_excerpt must be a short exact quote
that contains the value. Use metric keys supplied by the user. Distinguish period-end from average values in basis.
Omit every ambiguous observation. Percentages use unit=percent and the printed percentage number."""
    response = model.structured_generate(
        instructions=instructions,
        input_text=json.dumps({
            "symbol": symbol,
            "allowed_metrics": sorted(METRICS),
            "source_title": document.get("title"),
            "source_url": document.get("url"),
            "document_text": text[:45_000],
        }, ensure_ascii=True),
        model="gpt-5-mini", effort="low", max_output_tokens=5_000, timeout=90,
    )
    match = _JSON_RE.search(response.text or "")
    if not match:
        return []
    payload = json.loads(match.group(0))
    return [validate_observation(row, symbol=symbol, document=document)
            for row in (payload.get("observations") or []) if isinstance(row, dict)]


def persist_observations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"ok": True, "written": 0, "proposed": 0, "quarantined": 0}
    _rest("POST", "bank_kpi_observations",
          query="?on_conflict=symbol,metric_key,period_end,basis,consolidation_scope,source_id,available_at",
          body=rows, prefer="resolution=ignore-duplicates,return=minimal", timeout=45)
    return {
        "ok": True,
        "written": len(rows),
        "proposed": sum(row["validation_status"] == "PROPOSED" for row in rows),
        "quarantined": sum(row["validation_status"] == "QUARANTINED" for row in rows),
    }


def run_bank_backfill(faa: Any, *, symbols: list[str] | None = None, limit_per_bank: int = 5) -> dict[str, Any]:
    selected = [s.upper() for s in (symbols or list(CORE_BANKS)) if s.upper() in CORE_BANKS]
    report = {"started_at": _now(), "banks": {}, "documents": 0, "observations": 0, "errors": []}
    for symbol in selected:
        query = (f"{symbol} latest quarterly investor presentation results NIM CASA GNPA NNPA "
                 "slippages credit cost CET1 CRAR ROA ROE official")
        try:
            acquisition = faa.acquire(query, limit=max(1, min(limit_per_bank, 8)))
            docs = acquisition.get("documents") or []
            rows: list[dict[str, Any]] = []
            for document in docs[:limit_per_bank]:
                try:
                    rows.extend(extract_document(symbol, document))
                except Exception as exc:  # noqa: BLE001
                    report["errors"].append(f"{symbol}:{str(exc)[:160]}")
            persisted = persist_observations(rows)
            report["banks"][symbol] = {"documents": len(docs), **persisted}
            report["documents"] += len(docs)
            report["observations"] += len(rows)
        except Exception as exc:  # noqa: BLE001
            report["banks"][symbol] = {"ok": False, "error": str(exc)[:240]}
            report["errors"].append(f"{symbol}:{str(exc)[:160]}")
    report["ok"] = not report["errors"]
    report["finished_at"] = _now()
    return report


def coverage() -> dict[str, Any]:
    rows = _rest("GET", "bank_kpi_observations",
                 query="?select=symbol,metric_key,period_end,validation_status,confidence&order=period_end.desc&limit=10000") or []
    by_bank: dict[str, Any] = {}
    required = {item.key for item in BANK_KPIS}
    for symbol in CORE_BANKS:
        bank_rows = [row for row in rows if row.get("symbol") == symbol]
        observed = {str(row.get("metric_key")) for row in bank_rows
                    if row.get("validation_status") in {"VALIDATED", "TRUSTED"}}
        by_bank[symbol] = {
            "rows": len(bank_rows), "validated_metrics": sorted(observed),
            "missing_metrics": sorted(required - observed),
            "coverage_pct": round(100 * len(observed & required) / len(required), 2),
        }
    return {"banks": by_bank, "total_rows": len(rows), "required_metrics": sorted(required)}

