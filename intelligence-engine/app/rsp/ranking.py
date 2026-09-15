"""Source ranking & deduplication for RSP."""

from __future__ import annotations

from typing import Any


SOURCE_RANK = {
    "agi_research": 1,
    "agi": 1,
    "house_view": 1,
    "engine_states": 2,
    "l4_opinion": 3,
    "l4": 3,
    "broker_research": 4,
    "broker": 4,
    "latest_news": 5,
    "news": 5,
    "company_filings": 6,
    "filings": 6,
    "general_knowledge": 7,
    "portfolio": 3,
}


def dedupe_documents(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("document_id") or item.get("title") or item.get("id") or "")
        if not key:
            key = str(hash(frozenset((k, str(v)) for k, v in sorted(item.items()) if k != "snippet")))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def rank_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(it: dict[str, Any]) -> tuple:
        cls = str(it.get("source_class") or it.get("type") or it.get("source") or "general_knowledge")
        # normalize
        cls_l = cls.lower()
        priority = 7
        for k, p in SOURCE_RANK.items():
            if k in cls_l:
                priority = min(priority, p)
                break
        freshness = float(it.get("freshness", 0.5) or 0.5)
        confidence = float(it.get("confidence", 0.5) or 0.5)
        score = float(it.get("score", 0.0) or 0.0)
        return (priority, -freshness, -confidence, -score)

    ranked = sorted(items, key=key)
    for i, it in enumerate(ranked):
        it = dict(it)
        it["rank"] = i + 1
        cls = str(it.get("source_class") or it.get("type") or it.get("source") or "")
        it["priority"] = next((p for k, p in SOURCE_RANK.items() if k in cls.lower()), 7)
        ranked[i] = it
    return ranked


def collect_kip_sources(kip_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not kip_context:
        return []
    items: list[dict[str, Any]] = []

    def add_list(rows: list | None, source_class: str) -> None:
        for r in rows or []:
            if isinstance(r, str):
                items.append({"document_id": r, "source_class": source_class, "title": r})
            elif isinstance(r, dict):
                row = dict(r)
                row.setdefault("source_class", source_class)
                items.append(row)

    add_list(kip_context.get("previous_agi_research") or kip_context.get("agi_research_used"), "agi_research")
    # agi_research_used may be ids only
    if kip_context.get("agi_research_used") and not kip_context.get("previous_agi_research"):
        add_list(
            [{"document_id": x, "title": x} for x in kip_context.get("agi_research_used", [])],
            "agi_research",
        )
    add_list(kip_context.get("broker_reports") or kip_context.get("broker_reports_used"), "broker_research")
    if kip_context.get("broker_reports_used") and isinstance(kip_context["broker_reports_used"], list):
        if kip_context["broker_reports_used"] and isinstance(kip_context["broker_reports_used"][0], str):
            add_list(
                [{"document_id": x, "title": x} for x in kip_context["broker_reports_used"]],
                "broker_research",
            )
    add_list(kip_context.get("news_used"), "latest_news")
    if kip_context.get("news_used") and kip_context["news_used"] and isinstance(kip_context["news_used"][0], str):
        add_list([{"document_id": x} for x in kip_context["news_used"]], "latest_news")
    add_list(kip_context.get("filings") or kip_context.get("filings_used"), "company_filings")
    if kip_context.get("filings_used") and kip_context["filings_used"] and isinstance(kip_context["filings_used"][0], str):
        add_list([{"document_id": x} for x in kip_context["filings_used"]], "company_filings")

    for s in kip_context.get("supporting_evidence") or []:
        if isinstance(s, dict):
            row = dict(s)
            row.setdefault("source_class", row.get("source_class") or "general_knowledge")
            items.append(row)
    for s in kip_context.get("conflicting_evidence") or []:
        if isinstance(s, dict):
            row = dict(s)
            row.setdefault("source_class", row.get("source_class") or "broker_research")
            row["is_conflict"] = True
            items.append(row)

    # attach pack-level freshness/confidence when missing
    pack_fresh = float(kip_context.get("freshness_score") or 0.6)
    pack_conf = float(kip_context.get("confidence_score") or 0.5)
    for it in items:
        it.setdefault("freshness", pack_fresh)
        it.setdefault("confidence", pack_conf)
    return items
