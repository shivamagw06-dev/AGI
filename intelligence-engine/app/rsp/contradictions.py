"""Contradiction engine — broker/AGI/news/fundamentals/macro/valuation conflicts."""

from __future__ import annotations

import re
from typing import Any

from app.rsp.models import Contradiction, EvidenceStatement


_BEARISH = ("sell", "underweight", "downgrade", "bearish", "avoid", "short")
_BULLISH = ("buy", "overweight", "upgrade", "bullish", "accumulate", "long")
_TARGET_RE = re.compile(r"(?:rs\.?|₹|\$)?\s*([0-9]{2,6}(?:,[0-9]{3})*(?:\.\d+)?)", re.I)


def detect_contradictions(
    *,
    evidence: list[EvidenceStatement],
    kip_context: dict[str, Any] | None,
    house_view: dict[str, Any] | None,
    engines: dict[str, Any],
) -> list[Contradiction]:
    out: list[Contradiction] = []
    agi = [e for e in evidence if e.source.startswith("agi") or "agi" in e.source.lower()]
    broker = [e for e in evidence if "broker" in e.source.lower() or e.cluster == "broker"]
    news = [e for e in evidence if "news" in e.source.lower()]

    # AGI vs Broker stance
    agi_stance = _stance_from_statements(agi)
    broker_stance = _stance_from_statements(broker)
    if agi_stance and broker_stance and agi_stance != broker_stance and agi_stance != "neutral" and broker_stance != "neutral":
        out.append(
            Contradiction(
                kind="agi_vs_broker",
                summary=f"AGI stance ({agi_stance}) conflicts with broker consensus ({broker_stance})",
                left_source="agi",
                right_source="broker",
                left_claim=agi[0].statement if agi else "",
                right_claim=broker[0].statement if broker else "",
                severity=0.8,
                document_ids=_doc_ids(agi + broker),
            )
        )

    # Broker disagreement within brokers
    bull_b = [e for e in broker if _is_bullish(e.statement)]
    bear_b = [e for e in broker if _is_bearish(e.statement)]
    if bull_b and bear_b:
        out.append(
            Contradiction(
                kind="broker_disagreement",
                summary="Broker opinions disagree (bullish vs bearish)",
                left_source="broker_bull",
                right_source="broker_bear",
                left_claim=bull_b[0].statement,
                right_claim=bear_b[0].statement,
                severity=0.7,
                document_ids=_doc_ids(bull_b + bear_b),
            )
        )

    # Conflicting valuations / targets
    targets = _extract_targets(evidence)
    if len(set(targets.values())) >= 2:
        pairs = list(targets.items())
        out.append(
            Contradiction(
                kind="conflicting_targets",
                summary=f"Conflicting target prices: {pairs[0][1]} vs {pairs[1][1]}",
                left_source=pairs[0][0],
                right_source=pairs[1][0],
                left_claim=str(pairs[0][1]),
                right_claim=str(pairs[1][1]),
                severity=0.75,
            )
        )

    # News vs fundamentals (E13 / house thesis)
    fund = engines.get("e13") or {}
    if news and fund:
        side = str(fund.get("side") or fund.get("signal") or "").lower()
        if side in {"long", "buy", "bullish"} and any(_is_bearish(n.statement) for n in news):
            out.append(
                Contradiction(
                    kind="news_vs_fundamentals",
                    summary="Negative news tone vs constructive fundamental engine signal",
                    left_source="news",
                    right_source="e13",
                    left_claim=next(n.statement for n in news if _is_bearish(n.statement)),
                    right_claim=f"E13 side={side}",
                    severity=0.65,
                )
            )

    # Macro vs technicals (E01 vs E09)
    e01 = engines.get("e01") or {}
    e09 = engines.get("e09") or {}
    if e01 and e09:
        regime = str(e01.get("regime") or e01.get("label") or "").lower()
        trend = str(e09.get("side") or e09.get("trend") or e09.get("label") or "").lower()
        if ("risk_off" in regime or "deflation" in regime) and ("long" in trend or "up" in trend):
            out.append(
                Contradiction(
                    kind="macro_vs_technicals",
                    summary="Risk-off / adverse macro regime vs positive CTA/trend signal",
                    left_source="e01",
                    right_source="e09",
                    left_claim=str(regime),
                    right_claim=str(trend),
                    severity=0.6,
                )
            )

    # Events vs house view (E05)
    e05 = engines.get("e05") or {}
    hv_thesis = ""
    if house_view:
        cv = house_view.get("current_view") or {}
        hv_thesis = str(cv.get("thesis") or house_view.get("latest_thesis") or "")
    if e05 and hv_thesis:
        event_side = str(e05.get("side") or e05.get("label") or "").lower()
        if ("negative" in event_side or "bear" in event_side) and not any(
            w in hv_thesis.lower() for w in ("caution", "risk", "pressure", "weak")
        ):
            out.append(
                Contradiction(
                    kind="events_vs_house_view",
                    summary="Event-driven signal conflicts with constructive house thesis",
                    left_source="e05",
                    right_source="house_view",
                    left_claim=str(event_side),
                    right_claim=hv_thesis[:200],
                    severity=0.7,
                )
            )

    # Explicit KIP conflicting evidence (summaries only — never raw document bodies)
    for c in (kip_context or {}).get("conflicting_evidence") or []:
        if isinstance(c, dict):
            title = str(c.get("title") or "Conflicting retrieved opinion")
            snippet = str(c.get("snippet") or "")[:160]
            out.append(
                Contradiction(
                    kind="kip_conflict",
                    summary=f"{title}: {snippet}".strip(": "),
                    left_source="kip_supporting",
                    right_source=str(c.get("stance") or "conflict"),
                    left_claim="",
                    right_claim=snippet,
                    severity=0.55,
                    document_ids=[str(c["document_id"])] if c.get("document_id") else [],
                )
            )

    # Deduplicate by kind+summary
    uniq: list[Contradiction] = []
    seen: set[str] = set()
    for c in out:
        key = f"{c.kind}:{c.summary[:80]}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def _stance_from_statements(rows: list[EvidenceStatement]) -> str | None:
    if not rows:
        return None
    bull = sum(1 for e in rows if _is_bullish(e.statement) or e.cluster == "bull")
    bear = sum(1 for e in rows if _is_bearish(e.statement) or e.cluster == "bear")
    if bull == 0 and bear == 0:
        return "neutral"
    return "bullish" if bull >= bear else "bearish"


def _is_bullish(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in _BULLISH)


def _is_bearish(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in _BEARISH)


def _extract_targets(evidence: list[EvidenceStatement]) -> dict[str, str]:
    out: dict[str, str] = {}
    for e in evidence:
        if "target" not in e.statement.lower() and "tp" not in e.statement.lower():
            # still try
            pass
        m = _TARGET_RE.search(e.statement)
        if m and ("target" in e.statement.lower() or "rs" in e.statement.lower() or "₹" in e.statement):
            out[e.source or e.evidence_id] = m.group(1)
    return out


def _doc_ids(rows: list[EvidenceStatement]) -> list[str]:
    ids: list[str] = []
    for e in rows:
        for d in e.supporting_documents:
            if d not in ids:
                ids.append(d)
    return ids[:12]
