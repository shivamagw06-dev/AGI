"""Popular / suggested investor questions — dynamic, context-aware, no engine names."""

from __future__ import annotations

from typing import Any


SEED_QUESTIONS: list[dict[str, str]] = [
    {
        "question": "Should I buy ICICI Bank?",
        "category": "company",
        "reason": "Frequently asked company research",
    },
    {
        "question": "What changed after RBI?",
        "category": "macro",
        "reason": "Policy transmission into equities",
    },
    {
        "question": "Why is Nifty falling?",
        "category": "market_summary",
        "reason": "Daily index move literacy",
    },
    {
        "question": "Which sectors benefit from lower rates?",
        "category": "macro",
        "reason": "Rates sensitivity across the book",
    },
    {
        "question": "Latest Tata Motors outlook?",
        "category": "company",
        "reason": "Auto cycle and earnings continuity",
    },
    {
        "question": "What is AGI's current market view?",
        "category": "market_summary",
        "reason": "Today's institutional house view",
    },
    {
        "question": "Compare HDFC Bank vs ICICI Bank.",
        "category": "compare",
        "reason": "Popular relative-value question",
    },
    {
        "question": "Best defence companies in India?",
        "category": "theme",
        "reason": "Trending theme coverage",
    },
    {
        "question": "How should investors position for US yields?",
        "category": "macro",
        "reason": "Global financial conditions",
    },
    {
        "question": "Is IT services still a buy?",
        "category": "theme",
        "reason": "Deal pipeline and pricing watch",
    },
    {
        "question": "What are the risks for Reliance?",
        "category": "risk",
        "reason": "Risk-focused conglomerate research",
    },
    {
        "question": "Summarise today's market for an investor.",
        "category": "market_summary",
        "reason": "Daily desk briefing",
    },
]


def build_popular_questions(
    *,
    home: dict[str, Any] | None = None,
    themes: list[dict[str, Any]] | None = None,
    research: list[dict[str, Any]] | None = None,
    calendar: list[dict[str, Any]] | None = None,
    regime_label: str | None = None,
    risk_label: str | None = None,
) -> list[dict[str, Any]]:
    """Assemble Popular Investor Questions from live desk context + seeds."""
    out: list[dict[str, Any]] = []

    # Macro / regime-aware
    if regime_label and regime_label != "Unavailable":
        out.append(
            {
                "question": f"What does a {regime_label} regime mean for equities?",
                "category": "macro",
                "reason": "Tied to today's market regime",
                "source": "market_regime",
            }
        )
    if risk_label and risk_label != "Unavailable":
        out.append(
            {
                "question": f"How should investors interpret current market risk ({risk_label})?",
                "category": "risk",
                "reason": "Tied to today's risk level",
                "source": "market_risk",
            }
        )

    # Calendar / central bank events
    for ev in (calendar or [])[:3]:
        title = str(ev.get("title") or ev.get("name") or "")
        if not title:
            continue
        lower = title.lower()
        if any(x in lower for x in ("rbi", "fed", "mpc", "policy", "rate")):
            out.append(
                {
                    "question": f"What does {title} mean for banks?",
                    "category": "macro",
                    "reason": "Tied to today's macro event",
                    "source": "economic_calendar",
                }
            )
            out.append(
                {
                    "question": "Which sectors benefit from lower interest rates?",
                    "category": "macro",
                    "reason": "Rates sensitivity after policy events",
                    "source": "economic_calendar",
                }
            )
            out.append(
                {
                    "question": "How has AGI's market view changed after the latest policy announcement?",
                    "category": "house_view",
                    "reason": "House view evolution after macro event",
                    "source": "economic_calendar",
                }
            )
            break

    # Themes
    for th in (themes or [])[:4]:
        name = th.get("name") or th.get("id")
        if not name:
            continue
        out.append(
            {
                "question": f"Which companies are linked to {name}?",
                "category": "theme",
                "reason": "Trending theme",
                "source": "themes",
            }
        )

    # Latest research tickers
    for r in (research or [])[:5]:
        tickers = r.get("tickers") or []
        title = r.get("title")
        if tickers:
            t = str(tickers[0]).upper()
            out.append(
                {
                    "question": f"What is AGI's view on {t}?",
                    "category": "house_view",
                    "reason": "Tied to latest AGI research",
                    "source": "research",
                }
            )
            out.append(
                {
                    "question": f"What changed since last earnings for {t}?",
                    "category": "company",
                    "reason": "Earnings continuity from latest research",
                    "source": "research",
                }
            )
        elif title:
            out.append(
                {
                    "question": f"Summarise: {title}",
                    "category": "research_summary",
                    "reason": "Generated from latest AGI research",
                    "source": "research",
                }
            )

    # Seed fallbacks
    for seed in SEED_QUESTIONS:
        out.append({**seed, "source": "popular"})

    # De-dupe by question text
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for row in out:
        q = str(row.get("question") or "").strip()
        key = q.lower()
        if not q or key in seen:
            continue
        seen.add(key)
        uniq.append(row)
        if len(uniq) >= 12:
            break
    return uniq


def follow_up_questions(
    *,
    question: str,
    intent: str | None,
    related_companies: list[str],
    related_themes: list[str],
    house_label: str | None,
    risks: list[str] | None = None,
    catalysts: list[str] | None = None,
    knowledge_graph: dict[str, Any] | None = None,
    recent_research_titles: list[str] | None = None,
) -> list[str]:
    """Generate 4–8 intelligent follow-ups from thesis, risks, graph and research."""
    q = (question or "").strip()
    company = related_companies[0] if related_companies else None
    theme = related_themes[0] if related_themes else None
    peers = related_companies[1] if len(related_companies) > 1 else None
    buckets = (knowledge_graph or {}).get("buckets") if isinstance(knowledge_graph, dict) else {}
    buckets = buckets if isinstance(buckets, dict) else {}
    competitors = list(buckets.get("competitors") or [])
    suppliers = list(buckets.get("suppliers") or [])
    macro_themes = list(buckets.get("macro_themes") or related_themes)

    out: list[str] = []
    if company:
        compare_to = peers or (competitors[0] if competitors else "HDFC Bank")
        out.append(f"How does {company} compare with {compare_to}?")
        out.append(f"What are the biggest risks for {company}?")
        out.append(f"How has AGI's view on {company} changed over time?")
        out.append(f"What do broker reports say about {company}?")
        out.append(f"How did earnings affect the thesis for {company}?")
        out.append(f"What catalysts could re-rate {company}?")
    if risks:
        out.append(f"How material is this risk: {str(risks[0])[:90]}?")
    if catalysts:
        out.append(f"What happens if this catalyst plays out: {str(catalysts[0])[:90]}?")
    if suppliers:
        out.append(f"How exposed is {company or 'the thesis'} to supplier {suppliers[0]}?")
    if competitors:
        out.append(f"Does {competitors[0]} challenge the current house view?")
    if theme or macro_themes:
        tname = theme or macro_themes[0]
        out.append(f"Which companies benefit most from {tname}?")
        out.append(f"What are the key risks in the {tname} theme?")
    if recent_research_titles:
        out.append(f"What changed after: {str(recent_research_titles[0])[:90]}?")
    if intent in {"macro", "market_summary", "recommendation_request", "general_research"}:
        out.append("What is AGI's current market view?")
        out.append("Which sectors look relatively attractive today?")
        out.append("What changed in today's research desk?")
    if house_label:
        out.append(f"Why is the house view {house_label}?")
    if not out:
        out = [
            "What is AGI's current market view?",
            "Summarise today's research.",
            "Which themes are trending?",
            "What are the key macro risks?",
        ]
    # Always include question-aware variants
    if q and "compare" not in q.lower():
        out.append(f"What evidence supports the answer to: {q[:80]}?")
    # De-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for item in out:
        k = item.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(item)
        if len(uniq) >= 8:
            break
    return uniq[:8] if len(uniq) >= 4 else (uniq + SEED_QUESTIONS_TEXT())[:6]


def SEED_QUESTIONS_TEXT() -> list[str]:
    return [s["question"] for s in SEED_QUESTIONS]


def autocomplete(
    query: str,
    *,
    companies: list[str] | None = None,
    themes: list[dict[str, Any]] | None = None,
    sectors: list[str] | None = None,
    articles: list[dict[str, Any]] | None = None,
    popular: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    q = (query or "").strip().lower()
    if len(q) < 1:
        return {
            "companies": [],
            "themes": [],
            "sectors": [],
            "articles": [],
            "questions": (popular or SEED_QUESTIONS)[:6],
            "popular_searches": SEED_QUESTIONS[:6],
        }

    def match(text: str) -> bool:
        return q in (text or "").lower()

    co = [{"kind": "company", "id": c, "label": c} for c in (companies or []) if match(c)][:6]
    th = [
        {"kind": "theme", "id": t.get("id") or t.get("name"), "label": t.get("name") or t.get("id")}
        for t in (themes or [])
        if match(str(t.get("name") or t.get("id") or ""))
    ][:6]
    sec = [{"kind": "sector", "id": s, "label": s} for s in (sectors or []) if match(s)][:6]
    arts = [
        {
            "kind": "article",
            "id": a.get("id") or a.get("research_id"),
            "label": a.get("title"),
            "ticker": (a.get("tickers") or [None])[0],
        }
        for a in (articles or [])
        if match(str(a.get("title") or ""))
    ][:6]
    questions = [
        {"kind": "question", "id": p.get("question"), "label": p.get("question"), "reason": p.get("reason")}
        for p in (popular or SEED_QUESTIONS)
        if match(str(p.get("question") or ""))
    ][:6]
    if not questions:
        questions = [
            {"kind": "question", "id": p["question"], "label": p["question"], "reason": p.get("reason")}
            for p in SEED_QUESTIONS
            if match(p["question"])
        ][:6]
    return {
        "companies": co,
        "themes": th,
        "sectors": sec,
        "articles": arts,
        "questions": questions,
        "popular_searches": (popular or SEED_QUESTIONS)[:6],
    }
