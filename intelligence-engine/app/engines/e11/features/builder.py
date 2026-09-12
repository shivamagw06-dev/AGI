"""E11 Sentiment Feature Builder — news docs from FeatureSnapshot / PIT NEWS_* / SENT_*."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.engines.e11.entity_map import EntityMap, EntityRecord
from app.engines.e11.mapping import REGISTRY_SENT
from app.engines.e11.models.scoring import tone_from_text
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService


@dataclass
class NewsDoc:
    doc_id: str
    tone: float
    age_hours: float
    source_class: str
    entity_link: float
    headline: str | None = None


@dataclass
class SentimentPanel:
    symbol: str
    as_of: str
    entity: EntityRecord
    sector_id: str | None = None
    docs: list[NewsDoc] = field(default_factory=list)
    news_tone: float | None = None
    news_volume: float | None = None
    news_recency_hours: float | None = None
    news_source: str = "tier1_news"
    sent_meta: dict[str, float] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    discovery: str = "pit_news"


class SentimentFeatureBuilder:
    """Build news sentiment panels. Never MarketDataClient / provider payloads / raw APIs."""

    def __init__(self, registry: FeatureRegistryService, entity_map: EntityMap | None = None) -> None:
        self.registry = registry
        self.entity_map = entity_map or EntityMap()

    def build_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
    ) -> dict[str, SentimentPanel]:
        merged: dict[str, dict[str, Any]] = {
            k.upper(): dict(v) for k, v in (panels or {}).items()
        }
        if snapshots:
            for sym, snap in snapshots.items():
                s = sym.upper()
                meta = merged.setdefault(s, {})
                for fv in snap.values.values():
                    sid = (fv.metadata or {}).get("sector_id")
                    if sid:
                        meta.setdefault("sector_id", str(sid))
                    docs = (fv.metadata or {}).get("news_docs") or (fv.metadata or {}).get("docs")
                    if isinstance(docs, list) and docs:
                        meta.setdefault("news_docs", docs)
                    for k in ("NEWS_TONE", "news_tone", "NEWS_VOLUME", "news_volume", "NEWS_RECENCY", "news_recency_hours"):
                        if k in (fv.metadata or {}):
                            meta.setdefault(k, fv.metadata[k])

        out: dict[str, SentimentPanel] = {}
        for sym in sorted(merged.keys()):
            panel = merged[sym]
            entity = self.entity_map.from_panel(sym, panel)
            sent_meta = _sent_from_registry(self.registry, sym, as_of)
            stale: list[str] = []
            discovery = "pit_news"

            docs = _parse_docs(sym, panel.get("news_docs") or panel.get("docs"))
            news_tone = _f(panel.get("news_tone") or panel.get("NEWS_TONE"))
            news_volume = _f(panel.get("news_volume") or panel.get("NEWS_VOLUME"))
            news_recency = _f(
                panel.get("news_recency_hours")
                or panel.get("NEWS_RECENCY")
                or panel.get("news_age_hours")
            )
            news_source = str(panel.get("news_source") or panel.get("NEWS_SOURCE") or "tier1_news")

            if news_tone is None and "SENT_NEWS" in sent_meta:
                v = sent_meta["SENT_NEWS"]
                news_tone = ((v / 50.0) - 1.0) if v > 1.5 else v

            if not docs and news_tone is None:
                synth = _synthesize(sym, panel)
                news_tone = synth["news_tone"]
                news_volume = synth["news_volume"]
                news_recency = synth["news_recency_hours"]
                docs = [
                    NewsDoc(
                        doc_id=f"{sym}_synth_0",
                        tone=news_tone,
                        age_hours=news_recency,
                        source_class=news_source,
                        entity_link=0.95,
                        headline="synthetic_pit_news",
                    )
                ]
                stale.append("news_synthesized")
                discovery = "synthetic_news"

            if not docs and news_tone is not None:
                docs = [
                    NewsDoc(
                        doc_id=f"{sym}_meta_0",
                        tone=float(news_tone),
                        age_hours=float(news_recency or 12.0),
                        source_class=news_source,
                        entity_link=entity.confidence,
                    )
                ]

            if news_volume is None:
                news_volume = float(len(docs))
            if news_recency is None and docs:
                news_recency = min(d.age_hours for d in docs)
            if news_tone is None and docs:
                news_tone = sum(d.tone for d in docs) / len(docs)

            out[sym] = SentimentPanel(
                symbol=sym,
                as_of=as_of,
                entity=entity,
                sector_id=entity.sector_id,
                docs=docs,
                news_tone=news_tone,
                news_volume=news_volume,
                news_recency_hours=news_recency if news_recency is not None else 12.0,
                news_source=news_source,
                sent_meta=sent_meta,
                stale=stale,
                discovery=discovery,
            )
        return out


def _parse_docs(symbol: str, raw: Any) -> list[NewsDoc]:
    out: list[NewsDoc] = []
    if not isinstance(raw, list):
        return out
    for i, d in enumerate(raw):
        if not isinstance(d, dict):
            continue
        tone = _f(d.get("tone") or d.get("score"))
        if tone is None and d.get("headline"):
            tone = tone_from_text(str(d.get("headline")))
        if tone is None:
            continue
        if abs(tone) > 1.5:
            tone = (tone / 50.0) - 1.0
        age = _f(d.get("age_hours") or d.get("age_h") or d.get("freshness_hours")) or 12.0
        src = str(d.get("source_class") or d.get("source") or "tier1_news")
        if src.lower().startswith("social"):
            continue  # social disabled in P0
        out.append(
            NewsDoc(
                doc_id=str(d.get("doc_id") or f"{symbol}_doc_{i}"),
                tone=float(tone),
                age_hours=float(age),
                source_class=src,
                entity_link=float(d.get("entity_link") or d.get("entity_confidence") or 0.95),
                headline=str(d["headline"]) if d.get("headline") else None,
            )
        )
    return out


def _synthesize(symbol: str, panel: dict[str, Any]) -> dict[str, float]:
    h = 2166136261
    for ch in symbol.upper():
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    ret = float(panel.get("ret_3_0") or panel.get("ret_short") or 0.0)
    tone = max(-1.0, min(1.0, ((h % 21) - 10) / 20.0 + 0.5 * math.tanh(ret * 5)))
    return {
        "news_tone": round(tone, 6),
        "news_volume": float(5 + (h % 20)),
        "news_recency_hours": float(6 + (h % 36)),
    }


def _sent_from_registry(
    registry: FeatureRegistryService, symbol: str, as_of: str
) -> dict[str, float]:
    out: dict[str, float] = {}
    for fid in REGISTRY_SENT:
        fv = registry.get(fid, symbol=symbol, as_of=as_of, pit_mode=True)
        if fv is None:
            fv = registry.get(fid, symbol=None, as_of=as_of, pit_mode=True)
        if fv is not None and fv.value is not None:
            try:
                out[fid] = float(fv.value)
            except (TypeError, ValueError):
                continue
    return out


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
