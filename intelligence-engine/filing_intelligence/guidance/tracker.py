"""Guidance tracker — raised / maintained / reduced / withdrawn."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact


def extract_guidance(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("guidance") or parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    doc_id = str(parsed.get("doc_id") or "")
    ticker = str(parsed.get("ticker") or "")
    period = str(parsed.get("period") or "")
    tier = int(parsed.get("evidence_tier") or 5)

    status = "maintained"
    if "withdrawn" in lower or "withdraw" in lower:
        status = "withdrawn"
    elif "reduced" in lower or "cut guidance" in lower or "lowered guidance" in lower:
        status = "reduced"
    elif "raised" in lower or "upgraded guidance" in lower:
        status = "raised"
    elif "maintained" in lower or "reiterated" in lower or "guidance:" in lower:
        status = "maintained"

    if any(k in lower for k in ("guidance", "expect", "outlook", "medium-term")):
        facts.append(
            ExtractedFact(
                fact_id=f"{doc_id}:guidance:status",
                ticker=ticker,
                metric="Guidance_Status",
                value=status,
                unit="",
                period=period,
                doc_id=doc_id,
                section="guidance",
                evidence_tier=tier,
                confidence=0.8,
                validation_status="partially_verified",
                category="guidance",
            )
        )
        for metric, needles in [
            ("Revenue_Guidance", ("revenue guidance", "sales growth", "medium-term growth")),
            ("Margin_Guidance", ("nim", "margin")),
            ("Capex_Guidance", ("capex",)),
            ("Growth_Guidance", ("loan growth", "growth outlook", "medium-term growth")),
            ("Demand_Commentary", ("demand",)),
            ("Pricing_Commentary", ("pricing", "deposit-cost", "funding")),
            ("Currency_Commentary", ("currency", "fx")),
            ("Management_Confidence", ("reiterated", "confident", "prioritised")),
        ]:
            if any(n in lower for n in needles):
                facts.append(
                    ExtractedFact(
                        fact_id=f"{doc_id}:guidance:{metric}",
                        ticker=ticker,
                        metric=metric,
                        value=_clip(text, needles[0]),
                        unit="",
                        period=period,
                        doc_id=doc_id,
                        section="guidance",
                        evidence_tier=tier,
                        confidence=0.75,
                        validation_status="partially_verified",
                        category="guidance",
                        notes=f"status={status}",
                    )
                )
    return facts


def guidance_history(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [f for f in facts if f.get("metric") == "Guidance_Status"]
    rows.sort(key=lambda f: (f.get("period") or "", f.get("doc_id") or ""))
    return rows


def _clip(text: str, needle: str) -> str:
    lower = text.lower()
    idx = lower.find(needle)
    if idx < 0:
        return text[:160]
    return text[max(0, idx - 20) : idx + 120].strip()
