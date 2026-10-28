"""Entity detection with Concept Mode — never invent Infosys."""

from __future__ import annotations

import re
from typing import Any

from ask_pipeline.intent_resolution.schema import ENTITY_BIND_THRESHOLD

_KNOWN: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bhdfc\s*bank\b", re.I), "HDFCBANK", "HDFC Bank"),
    (re.compile(r"\bidbi(?:\s*bank)?\b", re.I), "IDBI", "IDBI Bank"),
    (re.compile(r"\binfosys\b|\binfy\b", re.I), "INFY", "Infosys"),
    (re.compile(r"\btcs\b|\btata consultancy\b", re.I), "TCS", "Tata Consultancy Services"),
    (re.compile(r"\bwipro\b", re.I), "WIPRO", "Wipro"),
    (re.compile(r"\breliance(?:\s+industries)?\b", re.I), "RELIANCE", "Reliance Industries"),
    (re.compile(r"\btitan\b", re.I), "TITAN", "Titan Company"),
    (re.compile(r"\basian\s*paints\b", re.I), "ASIANPAINT", "Asian Paints"),
    (re.compile(r"\bindigo\b|\binterglobe\b", re.I), "INDIGO", "InterGlobe Aviation"),
    (re.compile(r"\bmaruti\b", re.I), "MARUTI", "Maruti Suzuki"),
    (re.compile(r"\bicici\s*bank\b", re.I), "ICICIBANK", "ICICI Bank"),
    (re.compile(r"\bmeta(?:\s+platforms)?\b|\bfacebook\b|\bfb\b", re.I), "META", "Meta Platforms"),
    (re.compile(r"\bapple\b|\baapl\b", re.I), "AAPL", "Apple"),
    (re.compile(r"\bmicrosoft\b|\bmsft\b", re.I), "MSFT", "Microsoft"),
]


def detect_entities(
    question: str,
    *,
    ticker_hint: str | None = None,
    language_cues: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = str(question or "")
    found: list[dict[str, Any]] = []
    for pattern, eid, name in _KNOWN:
        m = pattern.search(q)
        if not m:
            continue
        found.append(
            {
                "type": "company",
                "id": eid,
                "name": name,
                "confidence": 0.99,
                "source": "irl_deterministic_map",
                "span_start": m.start(),
            }
        )
    found.sort(key=lambda e: int(e.get("span_start") or 0))

    # Deduplicate
    seen: set[str] = set()
    entities: list[dict[str, Any]] = []
    for e in found:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        entities.append(e)

    hint = str(ticker_hint or "").upper().strip() or None
    cues = language_cues or {}
    concept_shape = bool(
        cues.get("explain")
        or cues.get("education")
        or cues.get("why_question")
        or cues.get("how_would_you")
        or cues.get("list_request")
    )
    # Hint only binds when the question itself mentions that company (or no concept shape)
    hint_mentioned = False
    if hint:
        hint_mentioned = any(e["id"] == hint for e in entities) or hint.lower() in q.lower()

    if hint and hint_mentioned and hint not in seen:
        entities.insert(
            0,
            {
                "type": "company",
                "id": hint,
                "name": hint,
                "confidence": 0.8,
                "source": "ticker_hint_confirmed",
            },
        )
    elif hint and not entities and not concept_shape:
        # Non-concept question with explicit API ticker hint — soft bind at lower confidence
        entities.append(
            {
                "type": "company",
                "id": hint,
                "name": hint,
                "confidence": 0.7,
                "source": "ticker_hint_soft",
            }
        )

    bindable = [e for e in entities if float(e.get("confidence") or 0) >= ENTITY_BIND_THRESHOLD]
    concept_mode = not bindable

    # Sector/industry soft tags (not companies)
    soft_tags: list[dict[str, Any]] = []
    low = q.lower()
    if any(k in low for k in ("sector", "industry", "cement", "steel", "fmcg", "hospitals", "banks")):
        soft_tags.append({"type": "industry", "soft": True})
    if any(k in low for k in ("rbi", "sebi", "gst", "budget", "pli", "duty", "government")):
        soft_tags.append({"type": "government_policy", "soft": True})
    if any(k in low for k in ("inflation", "gdp", "repo", "macro", "crude", "rupee")):
        soft_tags.append({"type": "macro_variable", "soft": True})

    primary = None
    if not concept_mode and bindable:
        primary = {
            "entity_id": bindable[0]["id"],
            "entity_name": bindable[0]["name"],
            "entity_type": "company",
            "confidence": bindable[0]["confidence"],
            "source": bindable[0]["source"],
        }

    return {
        "entities": [] if concept_mode else bindable,
        "raw_mentions": entities,
        "primary": primary,
        "soft_tags": soft_tags,
        "concept_mode": concept_mode,
        "entity_pollution_blocked": bool(concept_mode and hint and not hint_mentioned),
        "ignored_ticker_hint": hint if (concept_mode and hint and not hint_mentioned) else None,
        "count": 0 if concept_mode else len(bindable),
        "fabricated": False,
    }
