"""Valuation Monitor + Transactions CMS adapter (file-backed Intelligence CMS)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from multi_source.paths import intelligence_cms_records
from multi_source.protocol import EvidenceItem

SOURCE_ID = "valuation_monitor"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ValuationCmsSource:
    source_id = SOURCE_ID

    def __init__(self) -> None:
        path = intelligence_cms_records()
        payload = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        self._records = [
            r
            for r in (payload.get("records") or [])
            if r.get("status") == "published"
            and r.get("module") in {"valuation_monitor", "transactions"}
        ]
        self._updated = payload.get("updated_at") or _now()

    def last_updated(self) -> str | None:
        return self._updated

    def search(self, query: str, *, ticker: str | None = None) -> list[EvidenceItem]:
        q = (query or "").strip().lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", q) if len(t) >= 3]
        if not tokens:
            # Return top published valuation rows for generic valuation questions
            tokens = ["valuation", "market"]

        hits: list[EvidenceItem] = []
        for rec in self._records:
            data = rec.get("data") or {}
            module = rec.get("module")
            hay = " ".join(str(v) for v in data.values()).lower() + f" {module}"
            score = sum(1 for t in tokens if t in hay)
            # Always include valuation rows for valuation-language queries
            if score <= 0 and module == "valuation_monitor" and any(
                t in q for t in ("valuation", "multiple", "expensive", "cheap", "ebitda")
            ):
                score = 1
            if score <= 0:
                continue

            if module == "transactions":
                entity = str(data.get("target") or data.get("company") or "Transaction")
                summary = (
                    f"{data.get('buyer') or 'Buyer'} / {entity}: "
                    f"EV {data.get('enterprise_value') or data.get('deal_value') or '—'} · "
                    f"{data.get('industry') or '—'} · {data.get('status') or '—'}"
                )
                path = "/private-markets#recent-transactions"
                reason = "Published CMS transaction"
            else:
                entity = str(data.get("company") or "Valuation")
                summary = (
                    f"{entity} ({data.get('sector') or '—'}): "
                    f"EV/Rev {data.get('ev_revenue') or '—'}, "
                    f"EV/EBITDA {data.get('ev_ebitda') or '—'}, "
                    f"Growth {data.get('growth') or '—'}, "
                    f"AGI Rating {data.get('agi_rating') or '—'}"
                )
                path = "/private-markets#valuation-monitor"
                reason = "Published Valuation Monitor row"

            hits.append(
                EvidenceItem(
                    source=SOURCE_ID if module == "valuation_monitor" else "transactions_cms",
                    entity=entity,
                    summary=summary[:500],
                    confidence=min(0.6 + 0.07 * score, 0.93),
                    timestamp=rec.get("updated_at") or rec.get("published_at") or self._updated,
                    score=float(score),
                    freshness="cms_published",
                    reason=reason,
                    metrics=dict(data),
                    path=path,
                )
            )

        hits.sort(key=lambda h: (h.score, h.confidence), reverse=True)
        return hits[:10]
