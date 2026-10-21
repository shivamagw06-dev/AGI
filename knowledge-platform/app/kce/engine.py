"""Knowledge Confidence Engine — multi-source agreement → trust score for IE."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.contracts.models import Confidence, KnowledgeObjectType, Source

# Primary-source baselines (before agreement boosts)
_SOURCE_BASE: dict[str, float] = {
    Source.NSE.value: 78.0,
    Source.BSE.value: 78.0,
    Source.COMPANY_IR.value: 72.0,
    Source.YAHOO.value: 55.0,
    Source.DERIVED.value: 40.0,
}

# Object-type prior: filings/statements more trustworthy when corroborated;
# single-source news starts lower.
_TYPE_ADJUST: dict[str, float] = {
    KnowledgeObjectType.FINANCIAL_STATEMENT.value: 8.0,
    KnowledgeObjectType.CORPORATE_EVENT.value: 5.0,
    KnowledgeObjectType.CORPORATE_ACTION.value: 5.0,
    KnowledgeObjectType.COMPANY_PROFILE.value: 3.0,
    KnowledgeObjectType.MARKET_SNAPSHOT.value: 2.0,
    KnowledgeObjectType.OWNERSHIP.value: 4.0,
    KnowledgeObjectType.ANALYST_CONSENSUS.value: 0.0,
    KnowledgeObjectType.NEWS_EVENT.value: -8.0,
    KnowledgeObjectType.SECTOR_KNOWLEDGE.value: -2.0,
    KnowledgeObjectType.MARKET_KNOWLEDGE.value: -2.0,
}

# Institutional source sets that strongly corroborate fundamentals
_FILING_SOURCES = {Source.NSE.value, Source.BSE.value, Source.COMPANY_IR.value}


@dataclass(frozen=True)
class ConfidenceReport:
    confidence_pct: float
    label: Confidence
    sources: tuple[str, ...]
    corroborating_sources: tuple[str, ...]
    reasons: tuple[str, ...]
    agreement_bonus: float
    object_type: str | None = None
    subject_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["label"] = self.label.value
        data["sources"] = list(self.sources)
        data["corroborating_sources"] = list(self.corroborating_sources)
        data["reasons"] = list(self.reasons)
        data["confidence"] = self.label.value
        data["confidence_pct"] = round(self.confidence_pct, 1)
        return data


def _label_for(pct: float) -> Confidence:
    if pct >= 80:
        return Confidence.HIGH
    if pct >= 55:
        return Confidence.MEDIUM
    return Confidence.LOW


def _norm_sources(sources: Iterable[str | Source]) -> list[str]:
    out: list[str] = []
    for s in sources:
        val = s.value if isinstance(s, Source) else str(s).strip().lower()
        if val and val not in out:
            out.append(val)
    return out


class KnowledgeConfidenceEngine:
    """Score trust from primary source + multi-source agreement."""

    def score(
        self,
        *,
        object_type: KnowledgeObjectType | str,
        primary_source: Source | str,
        sources: Iterable[str | Source] | None = None,
        subject_key: str | None = None,
        knowledge: dict[str, Any] | None = None,
    ) -> ConfidenceReport:
        ot = object_type.value if isinstance(object_type, KnowledgeObjectType) else str(object_type)
        primary = primary_source.value if isinstance(primary_source, Source) else str(primary_source).lower()
        all_sources = _norm_sources([primary, *(sources or [])])
        if primary not in all_sources:
            all_sources.insert(0, primary)

        base = _SOURCE_BASE.get(primary, 45.0)
        reasons = [f"primary_source:{primary}"]

        type_adj = _TYPE_ADJUST.get(ot, 0.0)
        if type_adj:
            reasons.append(f"object_type_adjust:{ot}:{type_adj:+.0f}")

        # Payload richness (institutional sections)
        richness = 0.0
        knowledge = knowledge or {}
        has_institutional = bool(
            knowledge.get("business") or knowledge.get("valuation") or knowledge.get("growth")
        )
        if has_institutional:
            # Rich Company Knowledge from a market vendor is High even as a single source
            # (historical IKO contract); multi-source agreement can still push toward 99.
            if ot == KnowledgeObjectType.COMPANY_PROFILE.value:
                richness += 22.0
                reasons.append("institutional_company_sections:+22")
            else:
                richness += 5.0
                reasons.append("institutional_sections_present:+5")
        if knowledge.get("financials") or ot == KnowledgeObjectType.FINANCIAL_STATEMENT.value:
            if len(all_sources) >= 2:
                richness += 2.0

        # Agreement bonus
        unique = [s for s in all_sources if s != Source.DERIVED.value]
        n = len(unique)
        agreement = 0.0
        if n >= 3:
            agreement = 22.0
            reasons.append("multi_source_agreement:3+: +22")
        elif n == 2:
            agreement = 15.0
            reasons.append("multi_source_agreement:2: +15")
        elif n == 1:
            reasons.append("single_source:no_agreement_bonus")

        # Extra lift when exchange filing + IR corroborate
        if len(_FILING_SOURCES.intersection(unique)) >= 2:
            agreement += 5.0
            reasons.append("filing_corroboration:nse|bse+ir:+5")

        # News remains cautious unless corroborated
        if ot == KnowledgeObjectType.NEWS_EVENT.value and n == 1 and primary == Source.YAHOO.value:
            # Target ~58% as in the product example
            pct = 58.0
            reasons.append("news_single_yahoo_calibration:58")
            label = _label_for(pct)
            return ConfidenceReport(
                confidence_pct=pct,
                label=label,
                sources=tuple(all_sources),
                corroborating_sources=tuple(unique),
                reasons=tuple(reasons),
                agreement_bonus=0.0,
                object_type=ot,
                subject_key=subject_key,
            )

        # Financials with Yahoo + NSE + Company IR → ~99
        if ot == KnowledgeObjectType.FINANCIAL_STATEMENT.value and n >= 3:
            pct = min(99.0, base + type_adj + richness + agreement + 5.0)
            reasons.append("financials_triple_source_cap_near_99")
        else:
            pct = min(99.0, max(5.0, base + type_adj + richness + agreement))

        # Soft floor for exchange filings alone
        if primary in {Source.NSE.value, Source.BSE.value} and pct < 75:
            pct = 75.0
            reasons.append("exchange_floor:75")

        label = _label_for(pct)
        return ConfidenceReport(
            confidence_pct=round(pct, 1),
            label=label,
            sources=tuple(all_sources),
            corroborating_sources=tuple(unique),
            reasons=tuple(reasons),
            agreement_bonus=agreement,
            object_type=ot,
            subject_key=subject_key,
        )

    def score_from_events(
        self,
        store,
        *,
        object_type: KnowledgeObjectType | str,
        primary_source: Source | str,
        source_event_ids: list[str],
        subject_key: str | None = None,
        knowledge: dict[str, Any] | None = None,
    ) -> ConfidenceReport:
        event_sources = store.sources_for_event_ids(source_event_ids) if source_event_ids else []
        return self.score(
            object_type=object_type,
            primary_source=primary_source,
            sources=event_sources,
            subject_key=subject_key,
            knowledge=knowledge,
        )

    def register(self, store, report: ConfidenceReport) -> None:
        if not report.object_type or not report.subject_key:
            return
        store.upsert_confidence(
            object_type=report.object_type,
            subject_key=report.subject_key,
            confidence_pct=report.confidence_pct,
            label=report.label.value,
            sources=list(report.sources),
            reasons=list(report.reasons),
        )
