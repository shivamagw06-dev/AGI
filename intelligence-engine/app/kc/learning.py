"""Daily learning digest — what AGI learned / what changed (Phase 8)."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.kc.models import LearningDigest


def build_learning_digest(kf: Any, *, as_of: _dt.date | None = None) -> LearningDigest:
    day = as_of or _dt.datetime.now(_dt.timezone.utc).date()
    day_s = day.isoformat()
    store = kf.store

    learned: list[str] = []
    changed: list[str] = []
    companies: list[str] = []
    sectors: list[str] = []
    themes: list[str] = []
    macros: list[str] = []
    preds_up: list[str] = []
    preds_down: list[str] = []
    research_update: list[str] = []
    docs = 0

    for ex in store.extracts.values():
        docs += 1
        updated = _meta_day(ex.meta)
        if updated == day_s:
            learned.append(f"Extracted research: {ex.title or ex.document_id}")
            if ex.companies:
                companies.extend(ex.companies)
            if ex.sectors:
                sectors.extend([str(s) for s in ex.sectors])
            if ex.themes:
                themes.extend([str(t) for t in ex.themes])
            if ex.macro_factors:
                macros.extend([str(m) for m in ex.macro_factors])
            if ex.prediction:
                preds_up.append(ex.prediction[:160])

    for co in store.companies.values():
        if _meta_day(co.meta) == day_s or _changelog_today(co.meta, day_s):
            companies.append(co.ticker)
            reason = (co.meta.change_log or ["updated"])[0]
            changed.append(f"{co.ticker}: {reason}")
            if float(co.meta.confidence or 0) < 0.45:
                research_update.append(f"Refresh thesis for {co.ticker}")
            if co.predictions:
                for p in co.predictions[:3]:
                    status = str((p or {}).get("status") or "").lower()
                    label = str((p or {}).get("thesis") or (p or {}).get("prediction_id") or co.ticker)
                    if status in {"hit", "improved", "success"}:
                        preds_up.append(label[:160])
                    elif status in {"miss", "weakened", "failed"}:
                        preds_down.append(label[:160])

    for sec in store.sectors.values():
        if _meta_day(sec.meta) == day_s or _changelog_today(sec.meta, day_s):
            sectors.append(sec.label)
            changed.append(f"Sector {sec.label}: {(sec.meta.change_log or ['refreshed'])[0]}")

    for th in store.themes.values():
        if _meta_day(th.meta) == day_s or _changelog_today(th.meta, day_s):
            themes.append(th.label)
            changed.append(f"Theme {th.label}: {(th.meta.change_log or ['refreshed'])[0]}")

    for m in store.macros.values():
        if _meta_day(m.meta) == day_s or _changelog_today(m.meta, day_s):
            macros.append(m.label)
            changed.append(f"Macro {m.label}: {(m.meta.change_log or ['refreshed'])[0]}")

    for p in store.predictions.values():
        if (p.actual_outcome or "").strip():
            if float(p.confidence or 0) >= 0.6:
                preds_up.append(p.prediction[:160] or p.prediction_id)
            else:
                preds_down.append(p.prediction[:160] or p.prediction_id)

    if not learned and docs:
        learned.append(f"Corpus holds {docs} structured research extracts; no new extracts dated {day_s}.")
    if not learned:
        learned.append("No new structured knowledge extracted today yet.")

    return LearningDigest(
        as_of=day_s,
        learned_today=_uniq(learned)[:20],
        what_changed=_uniq(changed)[:20],
        companies_changed=_uniq(companies)[:20],
        sectors_changed=_uniq(sectors)[:20],
        themes_changed=_uniq(themes)[:20],
        macro_changed=_uniq(macros)[:20],
        predictions_improved=_uniq(preds_up)[:12],
        predictions_weakened=_uniq(preds_down)[:12],
        research_to_update=_uniq(research_update)[:12],
        documents_processed=docs,
    )


def _meta_day(meta: Any) -> str | None:
    ts = getattr(meta, "updated_at", None)
    if ts is None and isinstance(meta, dict):
        ts = meta.get("updated_at")
    if ts is None:
        return None
    try:
        if isinstance(ts, _dt.datetime):
            return ts.date().isoformat()
        return _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return str(ts)[:10]


def _changelog_today(meta: Any, day_s: str) -> bool:
    log = getattr(meta, "change_log", None)
    if log is None and isinstance(meta, dict):
        log = meta.get("change_log")
    for item in log or []:
        if day_s in str(item):
            return True
    return False


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = str(item).strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        out.append(key)
    return out
