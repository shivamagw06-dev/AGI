"""Ask ticker binding guard — never invent prose tokens as companies."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.kip.extractors import KNOWN_TICKERS, TICKER_STOPWORDS, looks_like_equity_ticker

# Explicit global names that must bind even when ERE returns a Theme first.
_ALIAS_BIND: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmeta(?:\s+platforms)?\b|\bfacebook\b|\bfb\b", re.I), "META"),
    (re.compile(r"\bapple\b|\baapl\b", re.I), "AAPL"),
    (re.compile(r"\bmicrosoft\b|\bmsft\b", re.I), "MSFT"),
    (re.compile(r"\bgoogle\b|\balphabet\b|\bgoogl\b", re.I), "GOOGL"),
    (re.compile(r"\bamazon\b|\bamzn\b", re.I), "AMZN"),
    (re.compile(r"\bnvidia\b|\bnvda\b", re.I), "NVDA"),
    (re.compile(r"\breliance(?:\s+industries)?\b|\bril\b", re.I), "RELIANCE"),
    (re.compile(r"\binfosys\b|\binfy\b", re.I), "INFY"),
    (re.compile(r"\btcs\b|\btata consultancy\b", re.I), "TCS"),
    (re.compile(r"\bhdfc\s*bank\b", re.I), "HDFCBANK"),
    (re.compile(r"\bicici\s*bank\b|\bicicibank\b", re.I), "ICICIBANK"),
    (re.compile(r"\bzen\s+technologies\b", re.I), "ZENTEC"),
)

# Map canonical company names (from KIP titles) to NSE tickers when metadata lacks tickers.
_NAME_TO_TICKER: dict[str, str] = {
    "zen technologies": "ZENTEC",
}


def accept_detected_ticker(
    raw: Any,
    *,
    ere_blocked: bool = False,
    allow_when_blocked: bool = False,
) -> Optional[str]:
    """Return a safe equity ticker or None.

    Soft packs must not bind research-prose tokens (SUMMARIZE, WHAT, CAPEX)
    or unrelated symbols when ERE has blocked research / needs clarification.
    """
    if raw is None:
        return None
    t = str(raw).upper().replace(".NS", "").replace(".BO", "").strip()
    if not t or "_" in t:
        return None
    if t in TICKER_STOPWORDS:
        return None
    if ere_blocked and not allow_when_blocked:
        return None
    if looks_like_equity_ticker(t) or t in KNOWN_TICKERS:
        return t
    return None


def alias_ticker_from_question(question: str) -> Optional[str]:
    q = str(question or "")
    for pattern, ticker in _ALIAS_BIND:
        if pattern.search(q):
            return ticker
    return None


def _title_overlap_score(question: str, title: str) -> int:
    q_lower = str(question or "").lower()
    title_words = [
        w
        for w in re.findall(r"[a-z0-9]+", str(title or "").lower())
        if len(w) >= 4 and w not in {"research", "report", "update", "indian", "market", "global"}
    ]
    if not title_words:
        return 0
    return sum(1 for w in title_words if w in q_lower)


def kip_title_bind(question: str, kip: Any) -> Optional[str]:
    """Bind equity ticker from ingested AGI research titles in KIP."""
    q = str(question or "").strip()
    if len(q) < 12 or kip is None:
        return None
    try:
        resp = kip.search(q, mode="keyword", limit=5)
    except Exception:
        return None
    hits = getattr(resp, "hits", None) or []
    best: tuple[int, float, Optional[str]] = (0, 0.0, None)
    for hit in hits:
        title = str(getattr(hit, "title", "") or "").strip()
        if not title:
            continue
        overlap = _title_overlap_score(q, title)
        if overlap < 2 and not any(len(w) >= 8 and w in q.lower() for w in re.findall(r"[a-z0-9]+", title.lower())):
            continue
        score = float(getattr(hit, "score", 0) or 0)
        tickers = getattr(hit, "tickers", None) or []
        candidate = None
        for raw in tickers:
            candidate = accept_detected_ticker(raw, allow_when_blocked=True)
            if candidate:
                break
        if not candidate:
            candidate = alias_ticker_from_question(title)
        if not candidate:
            name_part = re.split(r"\s[—–\-]\s|\s₹", title)[0].strip().lower()
            name_part = re.sub(r"[''\u2019]s\b", "", name_part)
            name_part = re.sub(r"[^\w\s]", "", name_part).strip()
            candidate = _NAME_TO_TICKER.get(name_part)
            if candidate:
                candidate = accept_detected_ticker(candidate, allow_when_blocked=True)
        if not candidate:
            continue
        if overlap > best[0] or (overlap == best[0] and score > best[1]):
            best = (overlap, score, candidate)
    return best[2]


def looks_like_framework_meta_executive(text: str) -> bool:
    """True when ICE/framework scaffolding is being passed off as the answer."""
    low = (text or "").lower().strip()
    if not low:
        return False
    meta_markers = (
        "frameworks applied:",
        "frameworks applied",
        "playbook:",
        "reasoning follows the analytical checklist",
        "template: research note",
        "analyse via",
        "analyze via",
        "framework input domain",
        "committee vote",
        "fill from existing reasoning",
        "evidence coverage=",
        "entity-bound analysis",
        "governance path:",
        "lidi validated publish",
    )
    if any(m in low for m in meta_markers):
        return True
    if low.startswith("intent:") and ("template:" in low or "frameworks" in low):
        return True
    if low.startswith("intent:"):
        return True
    # Committee boilerplate leaked as lead narrative
    if "only when franchise" in low and "position sizing" in low:
        return True
    return False
