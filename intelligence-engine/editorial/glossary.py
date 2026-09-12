"""Permanent AGIB plain-English glossary for Editorial Intelligence.

Rule: Never assume the reader understands finance.
If a financial term is used, either replace it with simple English
or briefly explain it in the same sentence.
"""

from __future__ import annotations

import re

# Permanent platform rule (always included in editorial system prompts).
PERMANENT_RULE = (
    "Never assume the reader understands finance. "
    "If a financial term is used, either replace it with simple English "
    "or briefly explain it."
)

# Full glossary for LLM prompts (term → plain English explanation).
GLOSSARY: dict[str, str] = {
    # Business & company
    "fundamentals": "overall business and financial strength",
    "business quality": "how strong and reliable the business is",
    "franchise": "business strength and customer base",
    "competitive advantage": "what makes the company stronger than competitors",
    "moat": "long-term business advantage over competitors",
    "market share": "the company's share of the market",
    "pricing power": "ability to increase prices without losing customers",
    "business model": "how the company makes money",
    # Profit & earnings
    "revenue": "total money earned from sales",
    "sales growth": "increase in sales compared with last year",
    "net profit": "profit after all expenses and taxes",
    "operating profit": "profit from the main business before interest and tax",
    "ebitda": "profit before interest, tax and certain non-cash expenses",
    "margin": "profit earned from each ₹100 of sales",
    "operating margin": "profit from core business for every ₹100 of sales",
    "net margin": "final profit for every ₹100 of sales",
    "eps": "profit earned for each share",
    "earnings growth": "growth in company profit",
    # Banking
    "gross npa": "percentage of loans that are not being repaid on time",
    "net npa": "bad loans after adjusting for provisions",
    "asset quality": "quality of the bank's loan book",
    "casa": "low-cost customer deposits",
    "nim": "profit earned from lending after paying interest on deposits",
    "credit growth": "growth in loans given by the bank",
    "deposit growth": "growth in customer deposits",
    "provision coverage": "money set aside for possible loan losses",
    "capital adequacy": "financial strength to absorb losses",
    "cost of funds": "interest the bank pays to raise money",
    # Valuation
    "valuation": "current market price compared with the company's performance",
    "p/e ratio": "price investors pay for every ₹1 of company profit",
    "p/e": "price investors pay for every ₹1 of company profit",
    "p/b ratio": "market value compared with the company's net assets",
    "p/b": "market value compared with the company's net assets",
    "ev/ebitda": "company value compared with operating earnings",
    "fair value": "estimated reasonable value of the company",
    "premium valuation": "trading at a higher price than similar companies",
    "discount valuation": "trading at a lower price than similar companies",
    "multiple expansion": "investors paying a higher price for the business",
    "multiple compression": "investors paying a lower price for the business",
    "valuation multiple": "current market price compared with the company's performance",
    # Balance sheet
    "debt": "money borrowed by the company",
    "debt-to-equity": "borrowing compared with shareholder money",
    "cash flow": "money moving into and out of the business",
    "free cash flow": "cash left after business spending",
    "working capital": "money available for daily operations",
    "liquidity": "ability to pay short-term bills",
    "solvency": "ability to repay long-term debt",
    # Returns
    "roe": "profit generated from shareholders' money",
    "roce": "profit generated from all business capital",
    "roi": "return earned on invested money",
    "roa": "profit generated from company assets",
    # Market
    "bull market": "market where prices are generally rising",
    "bear market": "market where prices are generally falling",
    "volatility": "how much prices move up and down",
    "correction": "a noticeable fall in prices after a rise",
    "rally": "a period of rising prices",
    "consolidation": "prices moving within a narrow range",
    # Risk
    "downside risk": "what could negatively affect the business",
    "execution risk": "risk that the company may not deliver its plans",
    "regulatory risk": "risk from changes in government or regulations",
    "macroeconomic risk": "risk from the overall economy",
    "currency risk": "risk from changes in exchange rates",
    "credit risk": "risk that borrowers may not repay loans",
    "credit quality": "whether borrowers continue to repay loans on time",
    "financial performance": "financial health",
}

# Shorter mid-sentence replacements for deterministic post-process / templates.
# Avoid rewriting everyday English words mid-sentence into long clauses.
SHORT_FORMS: dict[str, str] = {
    "fundamentals": "overall business and financial strength",
    "business quality": "how strong and reliable the business is",
    "franchise": "business strength and customer base",
    "competitive advantage": "edge over competitors",
    "moat": "long-term business advantage",
    "pricing power": "ability to raise prices without losing customers",
    "business model": "how the company makes money",
    "sales growth": "increase in sales compared with last year",
    "net profit": "profit after all expenses and taxes",
    "operating profit": "profit from the main business before interest and tax",
    "ebitda": "operating profit before certain non-cash expenses",
    "operating margin": "core-business profit per ₹100 of sales",
    "net margin": "final profit per ₹100 of sales",
    "eps": "profit earned for each share",
    "earnings growth": "growth in company profit",
    "gross npa": "share of loans not repaid on time",
    "net npa": "bad loans after provisions",
    "asset quality": "loan quality",
    "casa": "low-cost customer deposits",
    "nim": "lending profit after deposit costs",
    "credit growth": "growth in loans",
    "deposit growth": "growth in customer deposits",
    "provision coverage": "money set aside for possible loan losses",
    "capital adequacy": "financial strength to absorb losses",
    "cost of funds": "interest paid to raise money",
    "p/e ratio": "price paid per ₹1 of profit",
    "p/e": "price paid per ₹1 of profit",
    "p/b ratio": "market value vs net assets",
    "p/b": "market value vs net assets",
    "ev/ebitda": "company value vs operating earnings",
    "fair value": "estimated reasonable value",
    "premium valuation": "higher price than similar companies",
    "discount valuation": "lower price than similar companies",
    "multiple expansion": "investors paying a higher price for the business",
    "multiple compression": "investors paying a lower price for the business",
    "valuation multiple": "current valuation",
    "debt-to-equity": "borrowing compared with shareholder money",
    "free cash flow": "cash left after business spending",
    "working capital": "money available for daily operations",
    "roe": "profit from shareholders' money",
    "roce": "profit from all business capital",
    "roi": "return on invested money",
    "roa": "profit from company assets",
    "bull market": "rising market",
    "bear market": "falling market",
    "downside risk": "what could hurt the business",
    "execution risk": "risk the company may not deliver its plans",
    "regulatory risk": "risk from rule or government changes",
    "macroeconomic risk": "risk from the overall economy",
    "currency risk": "risk from exchange-rate changes",
    "credit risk": "risk that borrowers may not repay",
    "credit quality": "whether borrowers repay loans on time",
    "financial performance": "financial health",
    "npa": "bad loans",
}

# Action / investment language — replace completely (never instruct the reader).
INVESTMENT_LANGUAGE: dict[str, str] = {
    "strong buy": "business and financial performance remain very strong",
    "buy": "long-term business and financial strength remain solid",
    "sell": "current business outlook has weakened",
    "hold": "current outlook remains balanced",
    "accumulate": "continue monitoring business performance",
    "avoid": "current risks outweigh business strengths",
    "entry point": "current market valuation",
    "exit point": "future business performance",
    "upside": "potential improvement",
    "downside": "possible risk",
    "conviction": "confidence in the current assessment",
    "target price": "estimated valuation",
    "price target": "estimated valuation",
    "stop loss": "risk limit",
    "investment advice": "current assessment",
}

_SHORT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (
        re.compile(rf"\b{re.escape(term)}\b", re.I),
        plain,
    )
    for term, plain in sorted(SHORT_FORMS.items(), key=lambda kv: len(kv[0]), reverse=True)
)

_INVESTMENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (
        re.compile(rf"\b{re.escape(term)}\b", re.I),
        plain,
    )
    for term, plain in sorted(
        INVESTMENT_LANGUAGE.items(), key=lambda kv: len(kv[0]), reverse=True
    )
)

_SOFT_ADVICE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\ba position is only justified when\b[^.]*\.?"),
        "Business strength and financial health should be weighed against the current market valuation.",
    ),
    (
        re.compile(r"(?i)\bonly justified when\b[^.]*\.?"),
        "Business strength and financial health should be weighed against the current market valuation.",
    ),
    (
        re.compile(r"(?i)\byou should\b[^.]*\.?"),
        "",
    ),
    (
        re.compile(r"(?i)\binvestors should\b[^.]*\.?"),
        "",
    ),
    (
        re.compile(r"(?i)\bconsider (?:buying|selling|holding)\b[^.]*\.?"),
        "",
    ),
)


def glossary_prompt_block() -> str:
    """Compact glossary text for system / user prompts."""
    lines = [
        "PERMANENT RULE",
        PERMANENT_RULE,
        "",
        "PLAIN-ENGLISH GLOSSARY (prefer these phrases; if a term must appear, explain it in the same sentence)",
    ]
    for term, plain in GLOSSARY.items():
        lines.append(f"- {term} → {plain}")
    lines.append("")
    lines.append("INVESTMENT LANGUAGE (never use left column; describe the meaning only)")
    for term, plain in INVESTMENT_LANGUAGE.items():
        lines.append(f'- never say "{term}" → say "{plain}"')
    lines.append("")
    lines.append(
        "Never tell the reader what action to take. "
        "Do not say a position is justified, only buy when, or similar advice."
    )
    return "\n".join(lines)


def simplify_jargon(text: str) -> str:
    """Replace finance jargon with short plain-English forms (deterministic)."""
    out = str(text or "")
    for pattern, repl in _SHORT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def replace_investment_language(text: str) -> str:
    """Replace banned investment/action words with plain descriptive phrases."""
    out = str(text or "")
    for pattern, repl in _SOFT_ADVICE_PATTERNS:
        out = pattern.sub(repl, out)
    for pattern, repl in _INVESTMENT_PATTERNS:
        out = pattern.sub(repl, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r" \.", ".", out)
    return out.strip()


def plain_english(text: str) -> str:
    """Full deterministic plain-English pass: jargon then investment language."""
    return replace_investment_language(simplify_jargon(text))
