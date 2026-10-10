"""Soft-attach Academy book knowledge into Knowledge Foundation (fill empties)."""

from __future__ import annotations

from typing import Any

from academy.books.flags import is_books_enabled
from academy.books.ingest import ensure_seeded
from academy.books.store import get_books_store


def attach_books_to_kf(*, limit: int = 40, kf_service: Any | None = None) -> dict[str, Any]:
    """
    Best-effort KF soft attach.
    Prefer upserting ThemeKnowledgeObject academies; never redesign KF.
    """
    if not is_books_enabled():
        return {"enabled": False, "attached": 0}
    ensure_seeded()
    store = get_books_store()
    academies = sorted({c.academy for c in store.concepts.values()})
    payload = {
        "enabled": True,
        "concepts": len(store.concepts),
        "academies": academies,
        "theme_payloads": [
            {
                "theme_id": f"academy_{a}",
                "label": a.replace("_", " ").title(),
                "definition": f"Structured AGI Academy knowledge domain: {a.replace('_', ' ')}.",
                "current_agi_view": "Institutional concepts, frameworks and formulas — not book verbatim text.",
                "concept_titles": [c.title for c in store.concepts.values() if c.academy == a][:12],
            }
            for a in academies[:24]
        ],
        "company_links": [
            {"ticker": co.upper(), "concept_id": c.concept_id, "title": c.title}
            for c in list(store.concepts.values())[:limit]
            for co in c.linked_companies
        ],
    }

    attached = 0
    svc = kf_service
    if svc is None:
        try:
            from app.kf.service import KfService

            svc = KfService()
        except Exception:
            svc = None
    if svc is None:
        return {**payload, "attached": 0, "reason": "kf_unavailable"}

    try:
        from app.kf.models import KnowledgeMeta, ThemeKnowledgeObject
    except Exception:
        return {**payload, "attached": 0, "reason": "kf_models_unavailable"}

    for theme in payload["theme_payloads"]:
        try:
            existing = svc.store.themes.get(theme["theme_id"].lower())
            if existing is not None:
                if not (existing.current_agi_view or "").strip():
                    existing.current_agi_view = theme["current_agi_view"]
                svc.store.upsert_theme(existing)
                attached += 1
                continue
            obj = ThemeKnowledgeObject(
                meta=KnowledgeMeta(kind="theme", key=theme["theme_id"]),
                theme_id=theme["theme_id"],
                label=theme["label"],
                definition=theme["definition"],
                current_agi_view=theme["current_agi_view"],
            )
            svc.store.upsert_theme(obj)
            attached += 1
        except Exception:
            continue

    return {**payload, "attached": attached}
