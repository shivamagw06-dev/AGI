"""Thesis Engine (TE) — bull/base/bear with explainable probability updates."""

from __future__ import annotations

from typing import Any

import re

from app.ail.catalog import COMPANIES
from app.ail.models import CorporateEvent, EvidenceRecord, ThesisCase, ThesisVersion
from app.ail.store import AilStore

_BULLISH = re.compile(
    r"\b(beat|raised guidance|margin expansion|order won|upgrade|buyback|strong growth|record revenue)\b",
    re.I,
)
_BEARISH = re.compile(
    r"\b(miss|cut guidance|guidance cut|resign|penalty|lawsuit|shutdown|downgrade|margin compression|loss)\b",
    re.I,
)


class ThesisEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def ensure(self, ticker: str, *, company: str | None = None) -> ThesisVersion:
        active = self.store.active_thesis(ticker)
        if active:
            return active
        profile = COMPANIES.get(ticker.upper()) or {}
        name = company or profile.get("company") or ticker
        bull = ThesisCase(
            case="bull",
            drivers=["Segment execution", "Margin resilience", "Capital allocation discipline"],
            catalysts=list(profile.get("segments") or [])[:3] or ["Earnings delivery"],
            probability=0.30,
            confidence=0.55,
            invalidation_conditions=["Sustained margin collapse", "Balance-sheet stress"],
            expected_timeline="12-24 months",
        )
        base = ThesisCase(
            case="base",
            drivers=["Franchise continuity", "Mid-cycle demand", "Policy stability"],
            catalysts=["Quarterly delivery in-line"],
            probability=0.45,
            confidence=0.60,
            invalidation_conditions=["Structural demand break"],
            expected_timeline="12-24 months",
        )
        bear = ThesisCase(
            case="bear",
            drivers=["Cyclical downturn", "Execution miss", "Regulatory shock"],
            catalysts=["Negative guidance revision"],
            probability=0.25,
            confidence=0.55,
            invalidation_conditions=["Sustained outperformance vs fears"],
            expected_timeline="12-24 months",
        )
        thesis = ThesisVersion(
            ticker=ticker.upper(),
            company=str(name),
            bull=bull,
            base=base,
            bear=bear,
            explanation=["Initial thesis prior — awaiting evidence updates."],
        )
        return self.store.put_thesis(thesis)

    def update_with_evidence(
        self,
        ticker: str,
        evidence: list[EvidenceRecord],
        events: list[CorporateEvent] | None = None,
    ) -> ThesisVersion:
        current = self.ensure(ticker)
        bull_p, base_p, bear_p = current.bull.probability, current.base.probability, current.bear.probability
        explanation: list[str] = []
        bull_sup = list(current.bull.supporting_evidence)
        bull_con = list(current.bull.contradicting_evidence)
        bear_sup = list(current.bear.supporting_evidence)
        bear_con = list(current.bear.contradicting_evidence)
        base_sup = list(current.base.supporting_evidence)

        for ev in evidence:
            text = ev.claim
            eid = ev.evidence_id
            if _BULLISH.search(text):
                bull_p += 0.04
                bear_p -= 0.02
                base_p -= 0.02
                bull_sup.append(eid)
                bear_con.append(eid)
                explanation.append(f"Bull ↑ from evidence {eid}: positive language detected.")
            elif _BEARISH.search(text):
                bear_p += 0.05
                bull_p -= 0.03
                base_p -= 0.02
                bear_sup.append(eid)
                bull_con.append(eid)
                explanation.append(f"Bear ↑ from evidence {eid}: negative language detected.")
            else:
                base_sup.append(eid)
                explanation.append(f"Base reinforced by evidence {eid}.")

        for evt in events or []:
            if evt.category in {"guidance_revised", "cfo_change", "ceo_change", "regulatory_penalty"}:
                # uncertainty rises — compress bull, lift bear slightly, cut base confidence
                bull_p -= 0.03
                bear_p += 0.03
                explanation.append(
                    f"Event {evt.event_id} ({evt.category}) reduced base confidence / lifted bear risk."
                )
            elif evt.category in {"order_win", "buyback", "dividend", "gov_approval"}:
                bull_p += 0.03
                bear_p -= 0.02
                explanation.append(f"Event {evt.event_id} ({evt.category}) supportive for bull case.")

        bull_p, base_p, bear_p = _normalize(bull_p, base_p, bear_p)
        # confidence adjustments
        base_conf = current.base.confidence
        if any((e.category in {"ceo_change", "cfo_change", "guidance_revised"}) for e in (events or [])):
            base_conf = max(0.35, base_conf - 0.08)
            explanation.append("Base-case confidence fell due to management/guidance event.")

        thesis = ThesisVersion(
            ticker=current.ticker,
            company=current.company,
            bull=ThesisCase(
                case="bull",
                drivers=current.bull.drivers,
                catalysts=current.bull.catalysts,
                supporting_evidence=_uniq(bull_sup)[-40:],
                contradicting_evidence=_uniq(bull_con)[-40:],
                probability=bull_p,
                confidence=min(0.9, current.bull.confidence + 0.02),
                invalidation_conditions=current.bull.invalidation_conditions,
                expected_timeline=current.bull.expected_timeline,
            ),
            base=ThesisCase(
                case="base",
                drivers=current.base.drivers,
                catalysts=current.base.catalysts,
                supporting_evidence=_uniq(base_sup)[-40:],
                contradicting_evidence=[],
                probability=base_p,
                confidence=base_conf,
                invalidation_conditions=current.base.invalidation_conditions,
                expected_timeline=current.base.expected_timeline,
            ),
            bear=ThesisCase(
                case="bear",
                drivers=current.bear.drivers,
                catalysts=current.bear.catalysts,
                supporting_evidence=_uniq(bear_sup)[-40:],
                contradicting_evidence=_uniq(bear_con)[-40:],
                probability=bear_p,
                confidence=min(0.9, current.bear.confidence + 0.02),
                invalidation_conditions=current.bear.invalidation_conditions,
                expected_timeline=current.bear.expected_timeline,
            ),
            explanation=(current.explanation + explanation)[-40:],
        )
        # Only version if probabilities or evidence sets changed
        if (
            abs(thesis.bull.probability - current.bull.probability) < 1e-9
            and abs(thesis.bear.probability - current.bear.probability) < 1e-9
            and thesis.bull.supporting_evidence == current.bull.supporting_evidence
            and thesis.bear.supporting_evidence == current.bear.supporting_evidence
            and abs(thesis.base.confidence - current.base.confidence) < 1e-9
        ):
            return current
        return self.store.put_thesis(thesis)

    def get(self, ticker: str) -> dict[str, Any]:
        t = self.ensure(ticker)
        return {
            "programme": "TE",
            **t.to_dict(),
            "history_versions": len(self.store.theses.get(ticker.upper(), [])),
        }


def _normalize(a: float, b: float, c: float) -> tuple[float, float, float]:
    a, b, c = max(0.05, a), max(0.05, b), max(0.05, c)
    s = a + b + c
    return round(a / s, 4), round(b / s, 4), round(c / s, 4)


def _uniq(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
