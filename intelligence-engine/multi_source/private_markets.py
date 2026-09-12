"""Private Markets adapter — PE firms, transactions, ownership, timeline."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multi_source.paths import intelligence_platform_dir
from multi_source.protocol import EvidenceItem

SOURCE_ID = "private_markets"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PrivateMarketsSource:
    source_id = SOURCE_ID

    def __init__(self) -> None:
        root = intelligence_platform_dir()
        self._entities = _load_json(root / "entities.json").get("entities") or []
        self._relationships = _load_json(root / "relationships.json").get("relationships") or []
        self._timeline = _load_json(root / "timeline.json").get("events") or []
        self._updated = (
            _load_json(root / "entities.json").get("updated_at")
            or _now()
        )

    def last_updated(self) -> str | None:
        return self._updated

    def search(self, query: str, *, ticker: str | None = None) -> list[EvidenceItem]:
        q = (query or "").strip().lower()
        if not q and not ticker:
            return []

        tokens = [t for t in re.split(r"[^a-z0-9]+", q) if len(t) >= 3]
        hits: list[EvidenceItem] = []

        # Entity matches
        for ent in self._entities:
            hay = " ".join(
                [
                    str(ent.get("name") or ""),
                    str(ent.get("slug") or ""),
                    str(ent.get("description") or ""),
                    " ".join(ent.get("tags") or []),
                    json.dumps(ent.get("metadata") or {}),
                ]
            ).lower()
            score = sum(1 for t in tokens if t in hay)
            if score <= 0:
                continue
            et = ent.get("entity_type") or "entity"
            meta = ent.get("metadata") or {}
            summary = ent.get("ai_summary") or ent.get("description") or ent.get("name")
            metrics = {
                "entity_type": et,
                "aum": meta.get("aum"),
                "hq": meta.get("hq"),
                "industry": meta.get("industry") or meta.get("sector"),
                "deal_value": meta.get("dealValue") or meta.get("enterpriseValue"),
                "status": meta.get("status") or ent.get("status"),
            }
            hits.append(
                EvidenceItem(
                    source=SOURCE_ID,
                    entity=str(ent.get("name") or ent.get("slug")),
                    summary=str(summary)[:500],
                    confidence=min(0.55 + 0.08 * score, 0.92),
                    timestamp=ent.get("updated_at") or self._updated,
                    score=float(score),
                    freshness="seeded",
                    reason=f"Matched Private Markets {et}",
                    metrics={k: v for k, v in metrics.items() if v},
                    path=f"/private-markets/entities/{ent.get('slug')}" if ent.get("slug") else "/private-markets",
                )
            )

        # Ownership / investment relationships
        for rel in self._relationships:
            hay = " ".join(
                [
                    str(rel.get("relation_type") or ""),
                    str(rel.get("source_label") or rel.get("from_label") or ""),
                    str(rel.get("target_label") or rel.get("to_label") or ""),
                    json.dumps(rel.get("metadata") or {}),
                ]
            ).lower()
            score = sum(1 for t in tokens if t in hay)
            if score <= 0:
                continue
            src = rel.get("source_label") or rel.get("from_label") or rel.get("source_id")
            tgt = rel.get("target_label") or rel.get("to_label") or rel.get("target_id")
            rtype = rel.get("relation_type") or "RELATED"
            hits.append(
                EvidenceItem(
                    source=SOURCE_ID,
                    entity=f"{src} → {tgt}",
                    summary=f"{rtype}: {src} → {tgt}",
                    confidence=min(0.5 + 0.08 * score, 0.88),
                    timestamp=rel.get("updated_at") or self._updated,
                    score=float(score) + 0.5,
                    freshness="seeded",
                    reason="Ownership / investment relationship",
                    metrics={"relation_type": rtype},
                    path="/private-markets",
                )
            )

        # Timeline
        for ev in self._timeline:
            hay = " ".join(
                [
                    str(ev.get("title") or ""),
                    str(ev.get("summary") or ""),
                    str(ev.get("event_type") or ""),
                    str(ev.get("entity_name") or ""),
                ]
            ).lower()
            score = sum(1 for t in tokens if t in hay)
            if score <= 0:
                continue
            hits.append(
                EvidenceItem(
                    source=SOURCE_ID,
                    entity=str(ev.get("entity_name") or ev.get("title") or "Timeline"),
                    summary=str(ev.get("summary") or ev.get("title") or "")[:420],
                    confidence=min(0.5 + 0.07 * score, 0.85),
                    timestamp=ev.get("occurred_at") or ev.get("date") or self._updated,
                    score=float(score),
                    freshness="timeline",
                    reason=f"Timeline {ev.get('event_type') or 'event'}",
                    metrics={"event_type": ev.get("event_type")},
                    path="/private-markets",
                )
            )

        hits.sort(key=lambda h: (h.score, h.confidence), reverse=True)
        return hits[:12]
