"""House View engine — AGI institutional view per company (KIP P1)."""

from __future__ import annotations

import datetime as _dt

from app.kip.models import (
    DocumentType,
    HistoricalView,
    HouseView,
    KipDocument,
    PredictionRecord,
    ResearchHistory,
    ResearchTimeline,
)


AGI_TYPES = {
    DocumentType.AGI_RESEARCH.value,
    DocumentType.AGI_NOTE.value,
    DocumentType.AGI_CIO_REPORT.value,
    DocumentType.AGI_DAILY_BRIEF.value,
    DocumentType.AGI_INVESTMENT_OFFICE.value,
    DocumentType.AGI_MODEL_PORTFOLIO.value,
}


def build_house_view(
    ticker: str,
    documents: list[KipDocument],
    *,
    predictions: list[PredictionRecord] | None = None,
) -> HouseView:
    t = ticker.upper()
    agi_docs = [
        d
        for d in documents
        if t in {x.upper() for x in d.investment.tickers}
        and d.document.document_type.value in AGI_TYPES
    ]
    return _assemble_house_view(t, agi_docs, predictions=predictions or [])


def build_sector_house_view(
    sector_key: str,
    documents: list[KipDocument],
    *,
    predictions: list[PredictionRecord] | None = None,
) -> HouseView | None:
    """Synthesize an institutional view for sector / theme questions (no single ticker)."""
    key = (sector_key or "").strip().upper() or "SECTOR"
    agi_docs = [d for d in documents if d.document.document_type.value in AGI_TYPES]
    if not agi_docs:
        agi_docs = list(documents)
    if not agi_docs:
        return None
    return _assemble_house_view(key, agi_docs, predictions=predictions or [])


def _assemble_house_view(
    subject: str,
    agi_docs: list[KipDocument],
    *,
    predictions: list[PredictionRecord],
) -> HouseView:
    agi_docs = sorted(agi_docs, key=lambda d: (d.document.date or _dt.date.min, d.document.version))
    history = [_to_hist(d) for d in agi_docs]
    current = history[-1] if history else None

    thesis_evolution: list[str] = []
    what_changed: list[str] = []
    remained: list[str] = []
    failed: list[str] = []
    catalysts_occurred: list[str] = []

    for i in range(1, len(agi_docs)):
        prev, cur = agi_docs[i - 1], agi_docs[i]
        thesis_evolution.append(
            f"{_fmt_date(prev.document.date)} → {_fmt_date(cur.document.date)}: "
            f"v{prev.document.version} → v{cur.document.version}"
        )
        if prev.research.investment_thesis.strip() != cur.research.investment_thesis.strip():
            what_changed.append(
                f"Thesis revised on {_fmt_date(cur.document.date)} "
                f"(from '{prev.research.investment_thesis[:120]}' "
                f"to '{cur.research.investment_thesis[:120]}')"
            )
        else:
            remained.append(f"Thesis stable through {_fmt_date(cur.document.date)}")
        prev_targets = set(prev.research.target_prices)
        cur_targets = set(cur.research.target_prices)
        if prev_targets and cur_targets and prev_targets != cur_targets:
            what_changed.append(
                f"Target price changed {_fmt_date(cur.document.date)}: "
                f"{sorted(prev_targets)} → {sorted(cur_targets)}"
            )
        lost = [a for a in prev.research.assumptions if a not in cur.research.assumptions]
        for a in lost[:5]:
            failed.append(f"Assumption retired {_fmt_date(cur.document.date)}: {a}")
        for c in prev.research.catalysts:
            if any(c.lower() in (x.cleaned_content or "").lower() for x in agi_docs[i:]):
                catalysts_occurred.append(c)

    for d in agi_docs[:-1]:
        for r in d.research.risks:
            later = " ".join((x.cleaned_content or "").lower() for x in agi_docs if x is not d)
            if any(tok in later for tok in ("materialised", "materialized", "hit", "realized", "realised")):
                if r.lower() in later:
                    failed.append(f"Risk materialized: {r}")

    conf = current.confidence if current else 0.0
    pred_acc = _prediction_accuracy(predictions, subject)

    return HouseView(
        ticker=subject,
        current_view=current,
        historical_views=list(reversed(history)),
        thesis_evolution=thesis_evolution,
        what_changed=_uniq(what_changed)[:20],
        what_remained_correct=_uniq(remained)[:20],
        failed_assumptions=_uniq(failed)[:20],
        catalysts_occurred=_uniq(catalysts_occurred)[:20],
        research_confidence=conf,
        prediction_accuracy=pred_acc,
        last_updated=_dt.datetime.now(_dt.timezone.utc),
    )


def build_research_history(
    ticker: str,
    documents: list[KipDocument],
    timeline: ResearchTimeline | None = None,
) -> ResearchHistory:
    t = ticker.upper()
    agi: list[HistoricalView] = []
    broker: list[HistoricalView] = []
    for d in documents:
        if t not in {x.upper() for x in d.investment.tickers}:
            continue
        hv = _to_hist(d)
        dtype = d.document.document_type.value
        if dtype in AGI_TYPES:
            agi.append(hv)
        elif "broker" in dtype or dtype in {"sell_side", "buy_side", "strategy_note", "newsletter"}:
            broker.append(hv)
    agi.sort(key=lambda h: h.date or _dt.date.min, reverse=True)
    broker.sort(key=lambda h: h.date or _dt.date.min, reverse=True)
    return ResearchHistory(ticker=t, agi_reports=agi, broker_reports=broker, timeline=timeline)


def _to_hist(d: KipDocument) -> HistoricalView:
    return HistoricalView(
        document_id=d.document_id,
        version=d.document.version,
        date=d.document.date,
        thesis=d.research.investment_thesis,
        bull_case=list(d.research.bull_case),
        bear_case=list(d.research.bear_case),
        valuation=d.research.valuation,
        target_prices=list(d.research.target_prices),
        confidence=d.knowledge.confidence,
        article_id=d.article_id,
    )


def _prediction_accuracy(preds: list[PredictionRecord], ticker: str) -> float | None:
    evaluated = [p for p in preds if p.ticker.upper() == ticker and p.hit is not None]
    if not evaluated:
        return None
    return round(sum(1 for p in evaluated if p.hit) / len(evaluated), 4)


def _fmt_date(d: _dt.date | None) -> str:
    return d.isoformat() if d else "undated"


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for i in items:
        k = i.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(i.strip())
    return out
