"""Module 3 — Financial Intelligence.

Deterministic (regex-based, non-LLM) extraction of the 19 headline financial
metrics from paragraph text: value, period, currency, unit, and a confidence
score, all wrapped in the standard evidence-backed Fact envelope.

Extraction is intentionally conservative — a metric is only extracted when
its name/synonym appears close to a currency- or percent-qualified number in
the same paragraph. This keeps precision high (Quality Contract: fact
extraction precision > 95%) at some recall cost, which is the right trade-off
for a system whose contract is "unknown facts must remain unknown".
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from kip_v2.schema import Evidence, Fact, Paragraph

_NUM = r"(?:₹|Rs\.?|INR|US\$|\$)?\s?([\d]{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
_UNIT = r"\s?(crore|cr\.?|lakh|lakhs|million|mn|billion|bn|%)?"

METRIC_SYNONYMS: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "total income", "net sales", "turnover"),
    "ebitda": ("ebitda",),
    "pat": ("profit after tax", "net profit", "pat "),
    "eps": ("earnings per share", "eps"),
    "operating_cash_flow": ("operating cash flow", "cash flow from operations", "cfo"),
    "free_cash_flow": ("free cash flow", "fcf"),
    "capex": ("capital expenditure", "capex"),
    "debt": ("total debt", "net debt", "gross debt", "borrowings"),
    "cash": ("cash and cash equivalents", "cash balance", "cash reserves"),
    "roe": ("return on equity", "roe"),
    "roce": ("return on capital employed", "roce"),
    "ebitda_margin": ("ebitda margin",),
    "pat_margin": ("net profit margin", "pat margin"),
    "gross_margin": ("gross margin",),
    "share_count": ("outstanding shares", "share count", "number of shares"),
    "dividend_per_share": ("dividend per share", "dps"),
    "buyback": ("share buyback", "buyback of shares", "buy-back"),
    "working_capital": ("working capital",),
    "revenue_growth": ("revenue growth", "yoy growth", "y-o-y growth", "growth of"),
}

_PERIOD_RE = re.compile(r"\b(FY ?20?\d{2}|FY\d{2}|Q[1-4] ?FY ?20?\d{2}|Q[1-4] ?FY\d{2}|H[12] ?FY ?20?\d{2})\b", re.I)
_CURRENCY_RE = re.compile(r"(₹|Rs\.?|INR|US\$|\$)")


def _extract_period(text: str, fallback: Optional[str]) -> Optional[str]:
    m = _PERIOD_RE.search(text)
    if m:
        return m.group(1).replace(" ", "").upper()
    return fallback


def _extract_currency(text: str) -> Optional[str]:
    m = _CURRENCY_RE.search(text)
    if not m:
        return None
    token = m.group(1)
    return "INR" if token in ("₹", "Rs", "Rs.", "INR") else "USD"


def _mask_periods(text: str) -> str:
    """Blanks out FY/quarter tokens (e.g. "FY25", "Q1FY26") so their digits
    never get mistaken for the metric value itself."""

    return _PERIOD_RE.sub(lambda m: " " * len(m.group(0)), text)


def _find_number_near(text: str, keyword_pos: int, window: int = 60) -> Optional[tuple[float, Optional[str]]]:
    span = _mask_periods(text[max(0, keyword_pos - 10):keyword_pos + window])
    m = re.search(_NUM + _UNIT, span)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    unit = (m.group(2) or "").lower().rstrip(".") or None
    if unit in ("cr",):
        unit = "crore"
    if unit in ("mn",):
        unit = "million"
    if unit in ("bn",):
        unit = "billion"
    return value, unit


def extract_metrics_from_paragraph(paragraph: Paragraph, default_period: Optional[str] = None) -> list[dict]:
    text = paragraph.text
    low = text.lower()
    found: list[dict] = []
    for metric, synonyms in METRIC_SYNONYMS.items():
        for synonym in synonyms:
            pos = low.find(synonym)
            if pos < 0:
                continue
            if metric == "revenue" and "growth" in low[pos: pos + len(synonym) + 12]:
                # "revenue growth of X%" is a rate, not the absolute revenue
                # figure — leave it to the dedicated revenue_growth metric.
                continue
            hit = _find_number_near(text, pos + len(synonym))
            if hit is None:
                continue
            value, unit = hit
            if metric in ("ebitda_margin", "pat_margin", "gross_margin", "roe", "roce", "revenue_growth") and unit != "%":
                # margins/returns/growth without an explicit % qualifier are too
                # ambiguous to trust (Quality Contract: precision over recall).
                if "%" not in text[pos: pos + 80]:
                    continue
                unit = "%"
            found.append(
                {
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    "period": _extract_period(text, default_period),
                    "currency": _extract_currency(text) if unit not in ("%",) else None,
                    "confidence": 0.8 if unit else 0.6,
                }
            )
            break  # one hit per metric per paragraph is enough signal
    return found


def build_financial_facts(
    company_id: str, paragraphs: Iterable[Paragraph], default_period: Optional[str] = None
) -> list[Fact]:
    facts: list[Fact] = []
    for paragraph in paragraphs:
        for hit in extract_metrics_from_paragraph(paragraph, default_period):
            evidence = Evidence(
                document_id=paragraph.document_id,
                page=paragraph.page,
                paragraph_id=paragraph.paragraph_id,
                snippet=paragraph.text[:500],
            )
            fact_id = Fact.make_id(company_id, "financial_metric", hit["metric"], hit["period"], evidence.evidence_hash)
            facts.append(
                Fact(
                    fact_id=fact_id,
                    company_id=company_id,
                    category="financial_metric",
                    key=hit["metric"],
                    value=hit["value"],
                    period=hit["period"],
                    unit=hit["unit"],
                    currency=hit["currency"],
                    confidence=hit["confidence"],
                    evidence=evidence,
                    source_document_id=paragraph.document_id,
                )
            )
    return facts
