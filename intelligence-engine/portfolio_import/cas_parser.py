"""Turning CAS text into holdings.

The extraction patterns below are written against the documented CAS layouts
and against synthetic fixtures, not against a real client statement, because
one has not been seen and should not be committed. They are therefore the part
of this module most likely to need correcting once a genuine file is run
through it.

That is why every provider's line patterns are data at the top of the file
rather than logic spread through it: correcting them is editing a table, and
the fixtures show exactly what shape each pattern expects. A line that does
not match is not dropped -- it is returned as unmatched, with the reason and a
redacted excerpt, so a wrong pattern shows up as a visible gap in a review
screen rather than as a portfolio that is quietly short a position.

A CAS is a statement of what a client owned on a date. It is not a
transaction history, so quantities here are positions and nothing in this
module infers a trade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .extract import CAMS_KFINTECH, CDSL, NSDL, ExtractedText, redact

ISIN_RE = re.compile(r"\b(INE|INF|IN9|INN)[A-Z0-9]{8}[0-9]\b")
_NUM = r"[-+]?[\d,]*\.?\d+"


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if out == out and abs(out) != float("inf") else None


@dataclass
class ParsedHolding:
    isin: Optional[str]
    name: Optional[str]
    quantity: Optional[float]
    asset_type: str = "EQUITY"
    # Demat account or mutual fund folio. Two accounts holding the same ISIN
    # are two lots, so this is part of the identity, not decoration.
    account_ref: Optional[str] = None
    folio: Optional[str] = None
    scheme_code: Optional[str] = None
    average_cost: Optional[float] = None
    market_value: Optional[float] = None
    source_line: str = ""


@dataclass
class ParseResult:
    provider: str
    statement_date: Optional[str] = None
    holdings: list[ParsedHolding] = field(default_factory=list)
    unmatched: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    accounts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "statement_date": self.statement_date,
            "matched_count": len(self.holdings),
            "unmatched_count": len(self.unmatched),
            "warning_count": len(self.warnings),
            "accounts": self.accounts,
            "holdings": [h.__dict__ for h in self.holdings],
            "unmatched": self.unmatched,
            "warnings": self.warnings,
        }


# A demat line names the ISIN, the security and a quantity. The value columns
# that follow vary by provider and by whether the statement includes a
# valuation, so only the first number after the name is treated as quantity and
# the rest are read positionally where present.
_DEMAT_LINE = re.compile(
    rf"(?P<isin>(?:INE|INF|IN9|INN)[A-Z0-9]{{8}}[0-9])\s+"
    rf"(?P<name>.+?)\s+"
    rf"(?P<quantity>{_NUM})"
    rf"(?:\s+(?P<value>{_NUM}))?\s*$"
)

# Mutual fund lines lead with a folio and carry units rather than shares.
_MF_LINE = re.compile(
    rf"(?P<folio>[A-Z0-9/\-]{{4,20}})\s+"
    rf"(?P<name>.+?)\s+"
    rf"(?P<units>{_NUM})\s+"
    rf"(?P<nav>{_NUM})"
    rf"(?:\s+(?P<value>{_NUM}))?\s*$"
)

_STATEMENT_DATE = re.compile(
    r"(?:AS ON|AS OF|STATEMENT (?:FOR|AS ON)|PERIOD ENDING)\s*[:\-]?\s*"
    r"(?P<date>\d{1,2}[-/ ][A-Za-z0-9]{2,9}[-/ ]\d{2,4})", re.I)

_DEMAT_ACCOUNT = re.compile(r"\b(?P<acct>IN[0-9]{14}|[0-9]{16})\b")


def _statement_date(text: str) -> Optional[str]:
    found = _STATEMENT_DATE.search(text or "")
    return found.group("date").strip() if found else None


def _asset_type(name: str, isin: Optional[str]) -> str:
    """ISIN prefix is the reliable signal; the name is a fallback.

    Indian ISINs encode the instrument: INF is a mutual fund, IN9 and some INE
    series are debt. Reading the scheme name instead would misfile every fund
    with 'Equity' in its title, which is most of them.
    """
    code = (isin or "")[:3]
    if code == "INF":
        return "MUTUAL_FUND"
    upper = (name or "").upper()
    if "ETF" in upper or "EXCHANGE TRADED" in upper:
        return "ETF"
    if any(word in upper for word in ("BOND", "DEBENTURE", "SGB", "GOLD BOND", "G-SEC")):
        return "BOND"
    if "REIT" in upper:
        return "REIT"
    if "INVIT" in upper:
        return "INVIT"
    return "EQUITY"


def parse(extracted: ExtractedText) -> ParseResult:
    """Read holdings out of an extracted statement.

    Lines that look like they should be holdings but do not parse are kept as
    unmatched with a redacted excerpt. A CAS line carries a PAN and an account
    number, so the excerpt is masked before it can reach a review screen or a
    log.
    """
    result = ParseResult(provider=extracted.provider)
    text = extracted.text
    result.statement_date = _statement_date(text)

    current_account: Optional[str] = None
    seen_accounts: list[str] = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        account = _DEMAT_ACCOUNT.search(line)
        if account:
            current_account = account.group("acct")
            if current_account not in seen_accounts:
                seen_accounts.append(current_account)

        has_isin = ISIN_RE.search(line)
        if has_isin:
            match = _DEMAT_LINE.search(line)
            if not match:
                result.unmatched.append({
                    "reason": "isin_line_did_not_parse",
                    "excerpt": redact(line)[:160],
                })
                continue
            isin = match.group("isin")
            name = match.group("name").strip(" .-")
            quantity = _num(match.group("quantity"))
            if quantity is None:
                result.unmatched.append({
                    "reason": "no_quantity", "excerpt": redact(line)[:160]})
                continue
            result.holdings.append(ParsedHolding(
                isin=isin,
                name=name or None,
                quantity=quantity,
                asset_type=_asset_type(name, isin),
                account_ref=current_account,
                market_value=_num(match.group("value")),
                source_line=redact(line)[:200],
            ))
            continue

        # Mutual fund folios in the CAMS/KFintech section carry no ISIN on the
        # holdings line, so they are matched separately and only in that
        # provider's statements, where the shape is unambiguous.
        if extracted.provider == CAMS_KFINTECH:
            match = _MF_LINE.search(line)
            if match and _num(match.group("units")) is not None:
                name = match.group("name").strip(" .-")
                result.holdings.append(ParsedHolding(
                    isin=None,
                    name=name or None,
                    quantity=_num(match.group("units")),
                    asset_type="MUTUAL_FUND",
                    folio=match.group("folio"),
                    market_value=_num(match.group("value")),
                    source_line=redact(line)[:200],
                ))

    result.accounts = seen_accounts
    if extracted.provider == "UNKNOWN":
        result.warnings.append(
            "Statement provider could not be identified. Holdings were read "
            "generically and should be reviewed line by line before import.")
    if not result.holdings:
        result.warnings.append(
            "No holdings were read from this statement. Nothing will be "
            "imported; the existing portfolio is unchanged.")
    return result
