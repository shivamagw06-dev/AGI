"""Deterministic extractors for KIP P0 (lexicon / regex — no model weight updates)."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.kip.models import (
    DocumentMetadata,
    DocumentType,
    InvestmentMetadata,
    KnowledgeMetadata,
    ResearchMetadata,
)

_TICKER_RE = re.compile(r"\b([A-Z]{2,6})(?:\.(?:NS|BO))?\b")
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_TARGET_RE = re.compile(r"(?:target(?:\s+price)?|tp)\s*(?:of|:)?\s*(?:rs\.?|₹|\$)?\s*([0-9]+(?:,[0-9]{3})*(?:\.\d+)?)", re.I)
_EXPECTED_RETURN_RE = re.compile(r"expected return[^.\n]{0,40}?(-?\d+(?:\.\d+)?\s*%)", re.I)
_HORIZON_RE = re.compile(r"\b((?:3|6|12)\s*(?:months?|m)|(?:1\s*)?years?|near[- ]term|medium[- ]term|long[- ]term)\b", re.I)
_CHART_RE = re.compile(r"\b(?:chart|figure|exhibit)\s*[:#]?\s*([A-Za-z0-9][\w\s.-]{0,60})", re.I)
_METRIC_RE = re.compile(
    r"\b(roe|roa|pe|p/e|pb|p/b|eps|revenue|ebitda|nim|roa|cet1|npa)\b[^.\n]{0,40}?(-?\d+(?:\.\d+)?%?)",
    re.I,
)

KNOWN_TICKERS = {
    "ICICIBANK",
    "HDFCBANK",
    "IDBI",
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN",
    "AXISBANK",
    "KOTAKBANK",
    "BHARTIARTL",
    "LT",
    "ITC",
    "WIPRO",
    "MARUTI",
    "TATAMOTORS",
    "HINDUNILVR",
    "HCLTECH",
    "TECHM",
    "LTIM",
    "LTTS",
    "PERSISTENT",
    "COFORGE",
    "MPHASIS",
    "OFSS",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "FB",
    "ZENTEC",
}

# Common English / research words that look like tickers when uppercased.
TICKER_STOPWORDS = {
    "THE",
    "AND",
    "FOR",
    "WITH",
    "FROM",
    "THIS",
    "THAT",
    "HAVE",
    "WILL",
    "INTO",
    "OVER",
    "UNDER",
    "INDIA",
    "INDIAN",
    "MARKET",
    "MARKETS",
    "STOCK",
    "STOCKS",
    "SECTOR",
    "UPDATE",
    "OUTLOOK",
    "REVIEW",
    "GROWTH",
    "WEAK",
    "DEAL",
    # Generic sector words — never treat as NSE tickers (e.g. "IDBI BANK" → not BANK)
    "BANK",
    "BANKS",
    "NBFC",
    "FINANCE",
    "FINANCIAL",
    "INSURANCE",
    "EQUITY",
    "BOND",
    "BONDS",
    "FUND",
    "FUNDS",
    "DEALS",
    "SERVICE",
    "SERVICES",
    "GLOBAL",
    "RESEARCH",
    "NOTE",
    "WEEK",
    "THIS",
    "CONTINUES",
    "EARNINGS",
    "PRESSURE",
    "DEMAND",
    "MACRO",
    "KEY",
    "TAKEAWAYS",
    "AMP",
    "HIS",
    "IMPLICATIONS",
    "IPO",
    "USD",
    "INR",
    "CEO",
    "GDP",
    "RBI",
    "AGI",
    "CMS",
    "QOQ",
    "YOY",
    "FY",
    "Q1FY",
    "AI",
    "IT",
    # Imperative / prose tokens that appear when questions are uppercased
    "WHAT",
    "DID",
    "SAY",
    "ABOUT",
    "HOW",
    "WHY",
    "WHEN",
    "WHERE",
    "WHICH",
    "SHOULD",
    "COULD",
    "WOULD",
    "PLEASE",
    "SUMMARIZE",
    "SUMMARISE",
    "EXPLAIN",
    "COMPARE",
    "DESCRIBE",
    "DISCUSS",
    "ANALYZE",
    "ANALYSE",
    "REVIEW",
    "CAPEX",
    "OPEX",
    "MID",
    "YEAR",
    "YEARS",
    "QUARTER",
    "PRIVATE",
    "PUBLIC",
    "PRICE",
    "BOOK",
    "MODEL",
    "BUSINESS",
}

SECTOR_MAP = {
    "bank": "Financials",
    "banking": "Financials",
    "nbfc": "Financials",
    "insurance": "Financials",
    "it services": "Information Technology",
    "indian it": "Information Technology",
    "india it": "Information Technology",
    "it sector": "Information Technology",
    "software": "Information Technology",
    "pharma": "Healthcare",
    "oil": "Energy",
    "gas": "Energy",
    "auto": "Consumer Discretionary",
    "fmcg": "Consumer Staples",
    "telecom": "Communication Services",
    "metal": "Materials",
    "cement": "Materials",
    "realty": "Real Estate",
    "infra": "Industrials",
}


def looks_like_equity_ticker(tok: str) -> bool:
    """Accept known tickers or bank-style symbols (HDFCBANK), never bare BANK."""
    t = str(tok or "").upper().replace(".NS", "").replace(".BO", "")
    if not t or t in TICKER_STOPWORDS:
        return False
    if t in KNOWN_TICKERS:
        return True
    # Bank tickers on NSE are compound (AXISBANK, HDFCBANK) — not the word BANK.
    return t.endswith("BANK") and len(t) >= 6


def sanitize_tickers(tickers: list[str] | None) -> list[str]:
    """Validate explicitly supplied symbols without limiting them to a static list.

    Automatic prose extraction remains deliberately conservative in
    ``looks_like_equity_ticker``.  Explicit tickers originate from trusted
    ingestion adapters (for example the CMS matched against company_master),
    so accepting a well-formed non-stopword symbol lets KIP cover the complete
    NSE universe instead of a small hard-coded subset.
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw in tickers or []:
        tok = re.sub(r"[^A-Za-z0-9.]", "", str(raw or "")).upper()
        tok = tok.replace(".NS", "").replace(".BO", "")
        if not tok or tok in seen:
            continue
        if len(tok) < 2 or len(tok) > 12:
            continue
        if tok in TICKER_STOPWORDS or not re.fullmatch(r"[A-Z0-9]{2,12}", tok):
            continue
        out.append(tok)
        seen.add(tok)
    return out

THEME_KEYWORDS = {
    "rate_cut": ["rate cut", "easing cycle", "lower rates", "repo cut"],
    "digital_banking": ["digital banking", "upi", "fintech", "neobank"],
    "ai_adoption": ["generative ai", "ai adoption", "machine learning", "llm"],
    "capex_cycle": ["capex", "capacity expansion", "order book"],
    "china_plus_one": ["china plus one", "china+1", "supply chain diversification"],
    "ev_transition": ["electric vehicle", "ev transition", "battery"],
    "inflation": ["inflation", "cpi", "sticky prices"],
    "credit_growth": ["credit growth", "loan growth", "advances"],
}

MACRO_TOPICS = [
    "inflation",
    "rates",
    "liquidity",
    "fx",
    "gdp",
    "fiscal",
    "commodity",
    "rbi",
    "fed",
]

SOURCE_RELIABILITY = {
    "agi": 0.95,
    "agi_research": 0.95,
    "broker": 0.8,
    "sec": 0.9,
    "nse": 0.9,
    "bse": 0.9,
    "newsletter": 0.55,
    "government": 0.85,
    "central_bank": 0.9,
    "industry": 0.7,
}


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def apply_ocr(content: str, *, needs_ocr: bool, ocr_text: str, ocr_enabled: bool) -> tuple[str, bool]:
    if not needs_ocr:
        return content, False
    if not ocr_enabled:
        return content or ocr_text, False
    # P0: OCR passthrough — use provided OCR text or treat content as already digitized.
    digitized = (ocr_text or content or "").strip()
    return digitized, True


def extract_document_metadata(
    *,
    title: str,
    author: str,
    source: str,
    document_type: DocumentType,
    broker: str,
    language: str,
    doc_date: date | None,
    content: str,
    version: int,
) -> DocumentMetadata:
    inferred_title = title or _first_line(content) or "Untitled"
    inferred_date = doc_date
    if inferred_date is None:
        m = _DATE_RE.search(content)
        if m:
            inferred_date = date.fromisoformat(m.group(1))
    return DocumentMetadata(
        title=inferred_title[:300],
        author=author,
        source=source,
        date=inferred_date,
        document_type=document_type,
        broker=broker,
        language=language or "en",
        version=version,
    )


def extract_investment_metadata(
    content: str,
    *,
    tickers: list[str] | None = None,
    companies: list[str] | None = None,
    themes: list[str] | None = None,
    sectors: list[str] | None = None,
) -> InvestmentMetadata:
    text = content or ""
    found = set(sanitize_tickers(tickers))
    for m in _TICKER_RE.finditer(text):
        tok = m.group(1).upper()
        if looks_like_equity_ticker(tok):
            found.add(tok)
    lower = text.lower()
    sector_hits = []
    for key, sector in SECTOR_MAP.items():
        if key in lower and sector not in sector_hits:
            sector_hits.append(sector)
    theme_hits = list(themes or [])
    for theme, keys in THEME_KEYWORDS.items():
        if any(k in lower for k in keys) and theme not in theme_hits:
            theme_hits.append(theme)
    macro = [t for t in MACRO_TOPICS if t in lower]
    countries = []
    if any(x in lower for x in ("india", "rbi", "nse", "bse", "nifty")):
        countries.append("IN")
    if any(x in lower for x in ("united states", "federal reserve", "fed ", "s&p")):
        countries.append("US")
    company_names = list(companies or [])
    for t in sorted(found):
        if t not in company_names:
            company_names.append(t)
    industries = list(sector_hits)
    return InvestmentMetadata(
        companies=company_names,
        tickers=sorted(found),
        industries=industries,
        sectors=list(sectors or []) or sector_hits,
        countries=countries,
        themes=theme_hits,
        macro_topics=macro,
    )


def extract_research_metadata(content: str) -> ResearchMetadata:
    lines = [ln.strip() for ln in (content or "").splitlines() if ln.strip()]
    thesis = _section_text(content, ("investment thesis", "thesis", "our view", "recommendation"))
    bull = _bullets_after(content, ("bull case", "upside", "positives"))
    bear = _bullets_after(content, ("bear case", "downside", "negatives"))
    counters = _bullets_after(content, ("counter", "contrary", "debate"))
    catalysts = _bullets_after(content, ("catalyst", "triggers", "upcoming"))
    risks = _bullets_after(content, ("risk", "key risks", "concerns"))
    valuation = _section_text(content, ("valuation", "multiples", "fair value"))
    forecasts = _bullets_after(content, ("forecast", "outlook", "estimates"))
    assumptions = _bullets_after(content, ("assumption", "we assume"))
    targets = [m.group(0) for m in _TARGET_RE.finditer(content or "")]
    metrics: dict[str, str] = {}
    for m in _METRIC_RE.finditer(content or ""):
        metrics[m.group(1).lower()] = m.group(2)
    tables = _extract_simple_tables(content)
    timeline_events = []
    for m in _DATE_RE.finditer(content or ""):
        timeline_events.append({"date": m.group(1), "context": _nearby(content, m.start(), 80)})
    if not thesis and lines:
        thesis = lines[0][:500]
    er = ""
    m_er = _EXPECTED_RETURN_RE.search(content or "")
    if m_er:
        er = m_er.group(1).strip()
    horizon = ""
    m_h = _HORIZON_RE.search(content or "")
    if m_h:
        horizon = m_h.group(1).strip()
    charts = [m.group(0).strip() for m in _CHART_RE.finditer(content or "")][:12]
    evidence = _bullets_after(content, ("supporting evidence", "evidence", "sources"))
    return ResearchMetadata(
        investment_thesis=thesis[:2000],
        bull_case=bull[:12],
        bear_case=bear[:12],
        counter_arguments=counters[:12],
        catalysts=catalysts[:12],
        risks=risks[:12],
        valuation=valuation[:1000],
        forecasts=forecasts[:12],
        target_prices=targets[:8],
        expected_return=er,
        time_horizon=horizon,
        assumptions=assumptions[:12],
        key_metrics=metrics,
        tables=tables[:5],
        charts=charts,
        supporting_evidence=evidence[:12],
        timeline_events=timeline_events[:20],
    )


def build_knowledge_metadata(
    *,
    source: str,
    doc_date: date | None,
    as_of: date | None,
    research: ResearchMetadata,
    investment: InvestmentMetadata,
    related_documents: list[str] | None = None,
    summary: str = "",
) -> KnowledgeMetadata:
    reliability = SOURCE_RELIABILITY.get(source.lower(), 0.65)
    freshness = _freshness(doc_date, as_of or date.today())
    conf = 0.35 + 0.15 * bool(research.investment_thesis)
    conf += 0.1 * bool(research.bull_case)
    conf += 0.1 * bool(research.bear_case)
    conf += 0.1 * bool(investment.tickers)
    conf += 0.1 * reliability
    conf = min(0.98, conf)
    return KnowledgeMetadata(
        freshness=freshness,
        confidence=round(conf, 4),
        source_reliability=reliability,
        related_documents=list(related_documents or []),
        related_companies=list(investment.tickers),
        related_themes=list(investment.themes),
        related_research=[],
        summary=summary,
    )


def extractive_summary(content: str, research: ResearchMetadata, max_chars: int = 600) -> str:
    parts: list[str] = []
    if research.investment_thesis:
        parts.append(research.investment_thesis)
    for label, items in (
        ("Bull", research.bull_case[:2]),
        ("Bear", research.bear_case[:2]),
        ("Risks", research.risks[:2]),
        ("Catalysts", research.catalysts[:2]),
    ):
        if items:
            parts.append(f"{label}: " + "; ".join(items))
    if not parts:
        parts.append((content or "")[:max_chars])
    text = " | ".join(parts)
    return text[:max_chars]


def _freshness(doc_date: date | None, as_of: date) -> float:
    if doc_date is None:
        return 0.6
    age = (as_of - doc_date).days
    if age <= 0:
        return 1.0
    if age <= 7:
        return 0.95
    if age <= 30:
        return 0.85
    if age <= 90:
        return 0.7
    if age <= 365:
        return 0.5
    return 0.3


def _first_line(content: str) -> str:
    for ln in (content or "").splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def _section_text(content: str, headers: tuple[str, ...]) -> str:
    lower = (content or "").lower()
    for h in headers:
        idx = lower.find(h)
        if idx < 0:
            continue
        chunk = content[idx : idx + 400]
        # drop header line
        parts = chunk.split("\n", 1)
        body = parts[1] if len(parts) > 1 else chunk
        return body.strip().split("\n\n")[0].strip()
    return ""


def _bullets_after(content: str, headers: tuple[str, ...], limit: int = 8) -> list[str]:
    lines = (content or "").splitlines()
    lower_lines = [ln.lower() for ln in lines]
    start = -1
    for i, ln in enumerate(lower_lines):
        if any(h in ln for h in headers):
            start = i + 1
            break
    if start < 0:
        # fallback keyword scan
        hits = []
        for ln in lines:
            lnl = ln.lower()
            if any(h.split()[0] in lnl for h in headers) and len(ln.strip()) > 8:
                hits.append(ln.strip(" -•*\t"))
        return hits[:limit]
    out: list[str] = []
    for ln in lines[start : start + 30]:
        s = ln.strip()
        if not s:
            if out:
                break
            continue
        if s.endswith(":") and len(s) < 40:
            break
        if s[0] in "-•*" or re.match(r"^\d+[.)]", s) or len(s) < 120:
            out.append(s.lstrip("-•* ").strip())
        if len(out) >= limit:
            break
    return out


def _extract_simple_tables(content: str) -> list[dict]:
    tables = []
    for block in re.split(r"\n\s*\n", content or ""):
        rows = [r for r in block.splitlines() if "|" in r]
        if len(rows) >= 2:
            headers = [c.strip() for c in rows[0].split("|") if c.strip()]
            data = []
            for r in rows[1:]:
                cols = [c.strip() for c in r.split("|") if c.strip()]
                if cols and not set(cols[0]) <= {"-", "="}:
                    data.append(cols)
            if headers and data:
                tables.append({"headers": headers, "rows": data[:20]})
    return tables


def _nearby(content: str, idx: int, window: int) -> str:
    start = max(0, idx - window)
    end = min(len(content), idx + window)
    return re.sub(r"\s+", " ", content[start:end]).strip()


def parse_iso_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
