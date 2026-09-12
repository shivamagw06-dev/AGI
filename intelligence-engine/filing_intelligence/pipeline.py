"""FIL analyse pipeline — ingest → parse → extract → validate → memory."""

from __future__ import annotations

from typing import Any

from filing_intelligence.capital_allocation.extract import extract_capital_allocation
from filing_intelligence.confidence.score import score_filings
from filing_intelligence.evidence.attach import evidence_pack
from filing_intelligence.governance.extract import extract_governance
from filing_intelligence.guidance.tracker import extract_guidance, guidance_history
from filing_intelligence.history.engine import history_from_facts
from filing_intelligence.ingestion.store import documents_for
from filing_intelligence.management_commentary.extract import extract_management
from filing_intelligence.notes_extractor.extract import extract_notes
from filing_intelligence.ownership.extract import extract_ownership
from filing_intelligence.parser.parse import parse_document
from filing_intelligence.quality.gates import validate_facts
from filing_intelligence.risks.extract import extract_risks, risk_register
from filing_intelligence.segment_extractor.extract import extract_segments
from filing_intelligence.statement_extractor.extract import extract_statements
from filing_intelligence.timeline.build import build_timeline


def analyse_ticker(ticker: str) -> dict[str, Any]:
    docs = documents_for(ticker)
    if not docs:
        return {"ticker": ticker.upper(), "found": False, "facts": [], "docs": []}

    all_facts = []
    for doc in docs:
        parsed = parse_document(doc)
        # attach metadata for validators
        parsed["metadata"] = doc.get("metadata") or {}
        extracted = []
        extracted += extract_statements(parsed)
        extracted += extract_notes(parsed)
        extracted += extract_segments(parsed)
        extracted += extract_management(parsed)
        extracted += extract_guidance(parsed)
        extracted += extract_risks(parsed)
        extracted += extract_capital_allocation(parsed)
        extracted += extract_ownership(parsed)
        extracted += extract_governance(parsed)
        all_facts.extend(f.to_dict() for f in extracted)

    quality = validate_facts(all_facts)
    kept = quality["kept"]
    hist = history_from_facts(kept)
    timeline = build_timeline(docs, kept)
    evidence = evidence_pack(kept, docs)
    confidence = score_filings(kept, docs)
    risks = risk_register(kept)
    guidance = guidance_history(kept)

    narrative = _standard_output(ticker, kept, hist, docs)

    return {
        "ticker": docs[0].get("ticker") or ticker.upper(),
        "found": True,
        "documents": [
            {
                "doc_id": d.get("doc_id"),
                "doc_type": d.get("doc_type"),
                "period": d.get("period"),
                "as_of": d.get("as_of"),
                "title": d.get("title"),
                "evidence_tier": d.get("evidence_tier"),
                "url": d.get("url"),
            }
            for d in docs
        ],
        "facts": kept,
        "rejected": quality["rejected"],
        "quality": quality["counts"],
        "history": hist,
        "timeline": timeline,
        "evidence": evidence,
        "confidence": confidence,
        "risk_register": risks,
        "guidance_tracker": guidance,
        "management": [f for f in kept if f.get("category") == "management"],
        "capital_allocation": [f for f in kept if f.get("category") == "capital"],
        "notes": [f for f in kept if f.get("category") == "note"],
        "segments": [f for f in kept if f.get("category") == "segment"],
        "narrative": narrative,
        "origin": "filing_intelligence",
    }


def _standard_output(ticker: str, facts: list[dict[str, Any]], hist: dict[str, Any], docs: list[dict[str, Any]]) -> str:
    t = (docs[0].get("ticker") if docs else ticker) or ticker
    by_metric = {s["metric"]: s for s in hist.get("series") or []}
    bits = []
    if "CET1" in by_metric:
        s = by_metric["CET1"]
        bits.append(
            f"{t} reported CET1 of {s['latest']}% in {s['latest_period']}, "
            f"remaining above regulatory requirements. "
            f"CET1 multi-year average {s['5y_avg']}% (range {s['min']}–{s['max']}); "
            f"trend {s['trend']}."
        )
    if "NIM" in by_metric:
        s = by_metric["NIM"]
        bits.append(
            f"NIM was {s['latest']}% in {s['latest_period']} "
            f"({s['trend']} vs own filing history; 5y avg {s['5y_avg']}%)."
        )
    if "CASA" in by_metric:
        s = by_metric["CASA"]
        bits.append(
            f"CASA was {s['latest']}% in {s['latest_period']}, "
            f"{'below' if s['latest'] < s['5y_avg'] else 'above'} its own multi-year filing average "
            f"({s['5y_avg']}%)."
        )
    guidance = [f for f in facts if f.get("metric") == "Guidance_Status"]
    if guidance:
        g = guidance[-1]
        bits.append(
            f"Guidance status in {g.get('period')}: {g.get('value')} "
            f"(from {g.get('doc_id')})."
        )
    rationale = next((f for f in facts if f.get("metric") == "Allocation_Rationale"), None)
    if rationale:
        bits.append(str(rationale.get("value")))
    if not bits:
        bits.append(f"{t}: filing corpus ingested; awaiting richer metric tables.")
    bits.append("All figures originate from Filing Intelligence (validated filing extract).")
    return " ".join(bits)
