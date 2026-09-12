"""Event Detection Engine (EDE) — detect meaningful corporate events from evidence."""

from __future__ import annotations

import re
from typing import Any

from app.ail.models import CorporateEvent, EvidenceRecord, utc_now
from app.ail.store import AilStore

EVENT_PATTERNS: list[tuple[str, re.Pattern[str], int, str]] = [
    ("ceo_change", re.compile(r"\b(ceo|chief executive)\b.*\b(appoint|resign|step down|named)\b", re.I), 9, "Management change may alter strategy execution"),
    ("cfo_change", re.compile(r"\b(cfo|chief financial)\b.*\b(appoint|resign|step down|named)\b", re.I), 8, "CFO change can affect capital allocation / guidance credibility"),
    ("dividend", re.compile(r"\bdividend\b.*\b(announc|declar|approv)\b|\b(announc|declar|approv)\b.*\bdividend\b", re.I), 6, "Capital return event"),
    ("buyback", re.compile(r"\bbuy[- ]?back\b", re.I), 7, "Share buyback affects equity supply / capital allocation"),
    ("share_split", re.compile(r"\b(stock|share)\s+split\b", re.I), 5, "Corporate action — share count change"),
    ("rights_issue", re.compile(r"\brights\s+issue\b", re.I), 8, "Dilutive capital raise"),
    ("qip", re.compile(r"\bQIP\b|\bqualified\s+institutional\s+placement\b", re.I), 8, "Equity capital raise"),
    ("capex", re.compile(r"\b(capex|capital expenditure)\b.*\b(announc|approv|plan)\b|\bfactory expansion\b|\bplant\s+(commission|shutdown|expand)", re.I), 7, "Capex / capacity event"),
    ("order_win", re.compile(r"\b(large order|major contract|order won|wins?\s+order)\b", re.I), 7, "Demand / backlog positive"),
    ("contract_loss", re.compile(r"\b(contract lost|loses?\s+contract|order cancell)\b", re.I), 8, "Demand / backlog negative"),
    ("acquisition", re.compile(r"\b(acqui(re|sition)|takeover)\b", re.I), 8, "M&A — inorganic growth / integration risk"),
    ("merger", re.compile(r"\bmerger\b|\bcombine with\b", re.I), 8, "M&A structural change"),
    ("rating_change", re.compile(r"\b(credit rating|rating)\b.*\b(upgrade|downgrade|affirm)\b", re.I), 7, "Credit perception change"),
    ("debt_raised", re.compile(r"\b(debt|bond|debenture)\b.*\b(rais|issu)\b", re.I), 6, "Leverage / funding event"),
    ("guidance_revised", re.compile(r"\bguidance\b.*\b(cut|lower|raise|revis|withdraw)\b|\b(margin guidance)\b", re.I), 9, "Outlook revision — thesis-relevant"),
    ("product_launch", re.compile(r"\b(product launch|launches?\s+new)\b", re.I), 5, "Product cycle update"),
    ("patent", re.compile(r"\bpatent\b.*\b(grant|approv)\b", re.I), 5, "IP event"),
    ("gov_approval", re.compile(r"\b(government|regulatory)\b.*\bapprov\b|\bapprov\b.*\b(licence|license|clearance)\b", re.I), 7, "Policy / permit catalyst"),
    ("regulatory_penalty", re.compile(r"\b(penalty|fine|sanction)\b.*\b(sebi|rbi|regulator|court)\b", re.I), 8, "Regulatory / legal risk"),
    ("lawsuit", re.compile(r"\b(lawsuit|litigation|court case)\b", re.I), 6, "Legal overhang"),
    ("esg_controversy", re.compile(r"\b(esg|environment|governance)\b.*\b(controvers|scandal|probe)\b", re.I), 6, "ESG reputational risk"),
    ("macro_policy", re.compile(r"\b(rbi|monetary policy|gst|budget|policy)\b.*\b(impact|affect)\b", re.I), 6, "Macro / policy transmission"),
    ("quarterly_results", re.compile(r"\b(q[1-4]|quarterly)\b.*\b(result|earnings|revenue|ebitda)\b", re.I), 7, "Earnings print"),
    ("annual_report", re.compile(r"\bannual report\b|\bfy\d{2,4}\b.*\bresults?\b", re.I), 7, "Annual disclosure"),
]


class EventDetectionEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def detect_from_evidence(self, evidence: EvidenceRecord) -> list[CorporateEvent]:
        text = f"{evidence.claim} {evidence.section or ''} {evidence.source or ''}"
        out: list[CorporateEvent] = []
        ticker = (evidence.ticker or "").upper()
        company = evidence.company or ticker
        if not ticker:
            return out
        for category, pattern, importance, impact in EVENT_PATTERNS:
            if not pattern.search(text):
                continue
            # de-dupe similar open events
            existing = self.store.events_for(ticker)
            if any(e.category == category and evidence.evidence_id in e.evidence_ids for e in existing):
                continue
            if any(e.category == category and e.new_value == evidence.claim[:180] for e in existing[-20:]):
                continue
            evt = CorporateEvent(
                company=company,
                ticker=ticker,
                timestamp=evidence.retrieved_at or utc_now(),
                category=category,
                importance=importance,
                evidence_ids=[evidence.evidence_id],
                confidence=min(0.95, float(evidence.confidence) + 0.05),
                previous_value=None,
                new_value=evidence.claim[:240],
                impact=impact,
                metadata={"source": evidence.source, "url": evidence.url},
            )
            self.store.put_event(evt)
            out.append(evt)
        return out

    def list_for(self, ticker: str, *, limit: int = 50) -> list[dict[str, Any]]:
        events = sorted(self.store.events_for(ticker), key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]

    def get(self, event_id: str) -> dict[str, Any] | None:
        e = self.store.events.get(event_id)
        return e.to_dict() if e else None
