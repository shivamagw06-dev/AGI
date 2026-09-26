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

DOCUMENT_METRICS = {
    "ANNUAL_REPORT": {"loans", "deposits", "casa", "nim", "gnpa", "nnpa", "roa", "roe", "crar", "cet1", "book_value", "eps"},
    "QUARTERLY_RESULTS": {"loans", "loan_growth", "deposits", "deposit_growth", "casa", "nim", "nii_growth", "cost_to_income", "gnpa", "nnpa", "slippage", "credit_cost", "pcr", "roa", "roe", "cet1", "crar", "eps"},
    "INVESTOR_PRESENTATION": {"loan_growth", "deposit_growth", "casa", "nim", "cost_of_deposits", "yield_on_advances", "gnpa", "nnpa", "slippage", "credit_cost", "pcr", "roa", "roe", "cet1", "crar"},
    "PILLAR_3_DISCLOSURE": {"cet1", "crar", "rwa", "lcr", "nsfr"},
    "EXCHANGE_FILING": METRICS,
    "OTHER": METRICS,
}

SYNONYMS = {
    "loans": ("gross advances", "total advances", "loans and advances", "advances to customers", "gross loans"),
    "deposits": ("total deposits", "deposits from customers"),
    "loan_growth": ("advance growth", "advances growth", "loan growth"),
    "deposit_growth": ("deposit growth", "deposits growth"),
    "casa": ("casa ratio", "casa deposits ratio", "current and savings account ratio"),
    "nim": ("net interest margin", "nim"),
    "nii_growth": ("net interest income growth", "nii growth"),
    "cost_to_income": ("cost to income", "cost-to-income"),
    "gnpa": ("gross npa ratio", "gross non-performing assets", "gnpa"),
    "nnpa": ("net npa ratio", "net non-performing assets", "nnpa"),
    "slippage": ("slippage ratio", "fresh slippages", "new npa additions"),
    "credit_cost": ("credit cost",),
    "pcr": ("provision coverage ratio", "pcr"),
    "roa": ("return on average assets", "return on assets", "roa"),
    "roe": ("return on average equity", "return on equity", "roe"),
    "cet1": ("common equity tier 1", "cet1", "cet 1"),
    "crar": ("capital adequacy ratio", "crar", "total capital adequacy"),
    "lcr": ("liquidity coverage ratio", "lcr"),
    "nsfr": ("net stable funding ratio", "nsfr"),
}

_PERCENT_RE = re.compile(r"(?<![\d.])(-?\d{1,3}(?:\.\d+)?)\s*%")
_FY_RE = re.compile(r"\b(?:FY\s*)?(20)?(\d{2})(?:\s*[-/]\s*(\d{2}))?\b", re.I)
_QFY_RE = re.compile(r"\bQ([1-4])\s*(?:FY\s*)?(20)?(\d{2})\b", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _document_text(document: dict[str, Any]) -> str:
    return str(document.get("raw_text") or document.get("text") or document.get("content_text") or document.get("content") or "")


def classify_document(document: dict[str, Any]) -> str:
    haystack = " ".join(str(document.get(key) or "") for key in ("document_type", "title", "url")).lower()
    if any(term in haystack for term in ("pillar 3", "pillar iii", "basel disclosure", "capital adequacy disclosure")):
        return "PILLAR_3_DISCLOSURE"
    if any(term in haystack for term in ("investor presentation", "earnings presentation", "analyst presentation")):
        return "INVESTOR_PRESENTATION"
    if any(term in haystack for term in ("quarterly", "financial results", "results")):
        return "QUARTERLY_RESULTS"
    if any(term in haystack for term in ("annual report", "integrated report")):
        return "ANNUAL_REPORT"
    if any(term in haystack for term in ("exchange", "nse", "bse", "filing")):
        return "EXCHANGE_FILING"
    return "OTHER"


def _period_details(document: dict[str, Any], text: str) -> tuple[str, str]:
    meta = document.get("metadata") or {}
    candidate = " ".join(str(value or "") for value in (
        document.get("quarter"), document.get("financial_year"), meta.get("reporting_period"),
        document.get("published_at"), document.get("title"), text[:500],
    ))
    quarter = _QFY_RE.search(candidate)
    if quarter:
        q, century, yy = int(quarter.group(1)), quarter.group(2), int(quarter.group(3))
        fy_end = int(f"{century or '20'}{yy:02d}")
        ends = {1: f"{fy_end - 1}-06-30", 2: f"{fy_end - 1}-09-30", 3: f"{fy_end - 1}-12-31", 4: f"{fy_end}-03-31"}
        return f"Q{q} FY{str(fy_end)[-2:]}", ends[q]
    iso = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", candidate)
    if iso:
        return iso.group(0), iso.group(0)
    fy = re.search(r"\bFY\s*(20)?(\d{2})\b", candidate, re.I)
    if fy:
        fy_end = int(f"{fy.group(1) or '20'}{int(fy.group(2)):02d}")
        return f"FY{str(fy_end)[-2:]}", f"{fy_end}-03-31"
    return "UNKNOWN", "1900-01-01"


def deterministic_extract(symbol: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only directly printed percentage KPIs with a synonym on the same line."""
    text = _document_text(document)
    doc_type = classify_document(document)
    allowed = DOCUMENT_METRICS[doc_type]
    period, period_end = _period_details(document, text)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str]] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not 5 <= len(line) <= 500:
            continue
        lower = line.lower()
        values = _PERCENT_RE.findall(line)
        if not values:
            continue
        for metric, aliases in SYNONYMS.items():
            if metric not in allowed or not any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lower) for alias in aliases):
                continue
            # Multiple percentages on one line are ambiguous without a table header.
            if len(values) != 1:
                continue
            value = float(values[0])
            key = (metric, value, period_end)
            if key in seen:
                continue
            seen.add(key)
            rows.append(validate_observation({
                "metric_key": metric, "value": value, "unit": "percent", "period": period,
                "period_end": period_end, "frequency": "QUARTERLY" if period.startswith("Q") else "ANNUAL",
                "basis": "REPORTED", "consolidation_scope": "STANDALONE", "annualized": False,
                "source_excerpt": line, "confidence": 0.8,
            }, symbol=symbol, document=document, extraction_method="DETERMINISTIC_TEXT"))
    return rows


def validate_observation(row: dict[str, Any], *, symbol: str, document: dict[str, Any],
                         extraction_method: str = "OPENAI_STRUCTURED_EXTRACTION") -> dict[str, Any]:
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
        bounds = {
            "nim": (0, 0.20), "gnpa": (0, 1), "nnpa": (0, 1), "casa": (0, 1),
            "cet1": (0, 1), "crar": (0, 1), "pcr": (0, 1.5), "roa": (-0.1, 0.2),
            "roe": (-0.5, 1), "credit_cost": (-0.1, 0.25), "cost_to_income": (0, 1.5),
        }.get(metric, (-0.25, 2.0))
        if not bounds[0] <= normalized <= bounds[1]:
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
        "extraction_method": extraction_method,
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
    doc_type = classify_document(document)
    target_metrics = sorted(DOCUMENT_METRICS[doc_type])
    instructions = f"""You extract reported commercial-bank KPIs from one primary-source {doc_type} document.
Return JSON only: {{"observations":[...]}}. Never calculate, infer, annualize, convert units, or fill a missing value.
Each observation must contain metric_key, value, unit, currency, period, period_end (YYYY-MM-DD), frequency,
basis, consolidation_scope, annualized, source_excerpt, confidence. source_excerpt must be a short exact quote
that contains the value. Use metric keys supplied by the user. Distinguish period-end from average values in basis.
Omit every ambiguous observation. Percentages use unit=percent and the printed percentage number."""
    response = model.structured_generate(
        instructions=instructions,
        input_text=json.dumps({
            "symbol": symbol,
            "allowed_metrics": target_metrics,
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


def extract_with_fallback(symbol: str, document: dict[str, Any], *, provider: OpenAIProvider | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deterministic = deterministic_extract(symbol, document)
    detected = {row["metric_key"] for row in deterministic}
    doc_type = classify_document(document)
    diagnostics = {"document_type": doc_type, "deterministic": len(deterministic), "ai": 0, "errors": []}
    try:
        ai_rows = extract_document(symbol, document, provider=provider)
    except Exception as exc:  # noqa: BLE001
        diagnostics["errors"].append(str(exc)[:200])
        ai_rows = []
    merged = list(deterministic)
    for row in ai_rows:
        if row["metric_key"] not in detected:
            merged.append(row)
            detected.add(row["metric_key"])
    diagnostics["ai"] = len(merged) - len(deterministic)
    return merged, diagnostics


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
    report = {"started_at": _now(), "mode": "ACQUIRE_AND_EXTRACT", "banks": {}, "documents": 0,
              "observations": 0, "diagnostics": [], "errors": []}
    for symbol in selected:
        query = (f"{symbol} latest quarterly investor presentation results NIM CASA GNPA NNPA "
                 "slippages credit cost CET1 CRAR ROA ROE official")
        try:
            acquisition = faa.acquire(query, limit=max(1, min(limit_per_bank, 8)))
            docs = acquisition.get("documents") or []
            rows: list[dict[str, Any]] = []
            for document in docs[:limit_per_bank]:
                extracted, diagnostics = extract_with_fallback(symbol, document)
                rows.extend(extracted)
                diagnostics.update({"symbol": symbol, "source_url": document.get("url")})
                report["diagnostics"].append(diagnostics)
                report["errors"].extend(f"{symbol}:{error}" for error in diagnostics["errors"])
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


def _indexed_documents(faa: Any, symbol: str, *, limit: int = 20) -> list[dict[str, Any]]:
    fre = getattr(faa, "fre", None)
    store = getattr(fre, "store", None)
    documents = list(getattr(store, "documents", {}).values()) if store is not None else []
    durable = getattr(getattr(faa, "store", None), "durable_documents", None)
    durable_docs = durable(symbol=symbol, limit=limit) if callable(durable) else []
    company = CORE_BANKS[symbol].lower()
    aliases = {symbol.lower(), company, company.replace(" bank", "")}
    matched = []
    for document in sorted(documents, key=lambda item: item.retrieved_at, reverse=True):
        haystack = " ".join(str(value or "") for value in (
            document.symbol, document.company, document.title, document.url, document.raw_text[:2000],
        )).lower()
        if any(alias in haystack for alias in aliases):
            matched.append(document.to_dict())
    seen = {str(item.get("checksum") or item.get("document_id") or item.get("url")) for item in matched}
    for document in durable_docs:
        key = str(document.get("checksum") or document.get("document_id") or document.get("url"))
        if key not in seen:
            matched.append(document)
            seen.add(key)
    return matched[:limit]


def reprocess_indexed_bank_documents(faa: Any, *, symbols: list[str] | None = None,
                                     limit_per_bank: int = 20) -> dict[str, Any]:
    """Re-run parsing/extraction over FRE documents without discovery or network acquisition."""
    selected = [s.upper() for s in (symbols or list(CORE_BANKS)) if s.upper() in CORE_BANKS]
    report = {"started_at": _now(), "mode": "REPROCESS_INDEXED_ONLY", "banks": {}, "documents": 0,
              "observations": 0, "diagnostics": [], "errors": []}
    for symbol in selected:
        docs = _indexed_documents(faa, symbol, limit=limit_per_bank)
        rows: list[dict[str, Any]] = []
        for document in docs:
            extracted, diagnostics = extract_with_fallback(symbol, document)
            rows.extend(extracted)
            diagnostics.update({"symbol": symbol, "source_url": document.get("url")})
            report["diagnostics"].append(diagnostics)
            report["errors"].extend(f"{symbol}:{error}" for error in diagnostics["errors"])
        persisted = persist_observations(rows)
        report["banks"][symbol] = {"documents": len(docs), **persisted}
        report["documents"] += len(docs)
        report["observations"] += len(rows)
    report["ok"] = bool(report["observations"]) and not report["errors"]
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
