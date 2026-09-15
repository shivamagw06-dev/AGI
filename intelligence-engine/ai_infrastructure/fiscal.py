"""Fiscal calendars for the AI-infrastructure universe.

Five of the seven cover companies close their books on 31 December. Modine
closes on 31 March, so Modine's "FY2027" is roughly calendar 2026 and overlaps
its peers' FY2026 far more than their FY2027. Ranking the two on a shared
"FY2027 EPS gap" without saying so compares different economic years.

This has already gone wrong twice in this codebase for the same underlying
reason -- a period label treated as though it were a date. The rule here is that
a label is never sufficient on its own: every stored estimate carries an
absolute `fiscal_period_end`, and comparisons are made on that.

Schneider Electric is included because it belongs to the universe, not because
it can be ingested the same way. It is not an SEC registrant, files under IFRS
in France, and publishes full statements half-yearly with revenue-only updates
at Q1 and Q3, so its evidence pipeline is bespoke and its data will be sparser.
Recording that here keeps the sparseness legible as a property of the issuer
rather than looking like a broken loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class FiscalCalendar:
    symbol: str
    name: str
    fiscal_year_end_month: int
    fiscal_year_end_day: int
    # True when the FY label is the calendar year the period *ends* in, which is
    # the convention for every name here. Recorded rather than assumed because
    # it is not universal -- Nvidia's FY2026 ends in January 2026, while other
    # January closers label the same period FY2025.
    label_is_ending_year: bool = True
    sec_registrant: bool = True
    cik: Optional[str] = None
    # Structured backlog / remaining-performance-obligation tagging in XBRL.
    backlog_in_xbrl: bool = False
    reports_quarterly: bool = True
    notes: str = ""


UNIVERSE: dict[str, FiscalCalendar] = {
    "TT": FiscalCalendar("TT", "Trane Technologies plc", 12, 31,
                         cik="0001466258", backlog_in_xbrl=False,
                         notes="Backlog disclosed in releases and calls, not XBRL."),
    "VRT": FiscalCalendar("VRT", "Vertiv Holdings Co", 12, 31,
                          cik="0001674101", backlog_in_xbrl=False,
                          notes="Orders and book-to-bill are narrative disclosures."),
    "ETN": FiscalCalendar("ETN", "Eaton Corp plc", 12, 31,
                          cik="0001551182", backlog_in_xbrl=True),
    "MOD": FiscalCalendar("MOD", "Modine Manufacturing Co", 3, 31,
                          cik="0000067347", backlog_in_xbrl=False,
                          notes="March year end: FY2027 is mostly calendar 2026."),
    "ANET": FiscalCalendar("ANET", "Arista Networks, Inc.", 12, 31,
                           cik="0001596532", backlog_in_xbrl=True),
    "GEV": FiscalCalendar("GEV", "GE Vernova Inc.", 12, 31,
                          cik="0001996810", backlog_in_xbrl=True),
    "SU": FiscalCalendar("SU", "Schneider Electric SE", 12, 31,
                         sec_registrant=False, cik=None, backlog_in_xbrl=False,
                         reports_quarterly=False,
                         notes="Euronext Paris, IFRS. No SEC filings and no XBRL. "
                               "Full statements half-yearly; Q1/Q3 revenue only."),
}


def normalise_label(label: object) -> Optional[str]:
    """`FY27`, `FY2027`, `2027`, `fy 27` all mean FY2027."""
    text = str(label or "").strip().upper().replace(" ", "")
    if text.startswith("FY"):
        text = text[2:]
    if not text.isdigit():
        return None
    if len(text) == 2:
        return f"FY20{text}"
    if len(text) == 4:
        return f"FY{text}"
    return None


def period_end(symbol: str, label: object) -> Optional[date]:
    """The absolute date a company's fiscal period closes.

    Returns nothing for an unknown symbol rather than assuming December. A
    silent December default is precisely how Modine's March year end would
    disappear into a comparison that looks fine.
    """
    cal = UNIVERSE.get(str(symbol or "").strip().upper())
    normalised = normalise_label(label)
    if cal is None or normalised is None:
        return None
    year = int(normalised[2:])
    if not cal.label_is_ending_year:
        year += 1
    return date(year, cal.fiscal_year_end_month, cal.fiscal_year_end_day)


def periods_are_comparable(left_symbol: str, right_symbol: str, label: object,
                           *, tolerance_days: int = 92) -> bool:
    """Whether two companies' same-labelled periods describe the same economic year.

    Trane FY2027 and Modine FY2027 end nine months apart, so on the default
    tolerance they are not comparable and a screen ranking them together should
    say so instead of quietly averaging them.
    """
    left, right = period_end(left_symbol, label), period_end(right_symbol, label)
    if left is None or right is None:
        return False
    return abs(left.toordinal() - right.toordinal()) <= tolerance_days
