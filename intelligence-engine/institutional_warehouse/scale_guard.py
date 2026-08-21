"""Stop a value wrong by a million from being stored. Off by default.

The census found the live source of new mis-scaled rows: a feed with no entry in
``units.SOURCE_DEFAULT_UNIT`` falls through ``resolve_unit`` to "treat the value
as already canonical", and its raw rupees are stored in a column that means INR
million. earnings_intelligence_p21 and financial_connector both do this, and
both were still creating such rows on 2026-08-21.

The fix for those two is an entry in SOURCE_DEFAULT_UNIT, once their true unit is
established rather than guessed. This guard is the thing that keeps the next
feed from repeating it, because the failure mode is silence: nothing errors, and
a number a million times too large reads downstream as an ordinary number.

Why isolate rather than reject
------------------------------
A rejected row is data lost; a quarantined row is data a person can look at. The
warehouse already quarantines rather than dropping, and this follows that.

Why it is off by default
------------------------
Turning it on changes what lands in the warehouse, and the census has to be
reviewed before anything starts refusing writes. ``MODE_REPORT`` counts what it
would have caught and stores everything, which is how it should first run.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from institutional_warehouse import units
from institutional_warehouse.value_plausibility import (IMPOSSIBLE_MILLION,
                                                        MONEY_FIELDS)

MODE_OFF = "off"
MODE_REPORT = "report"
MODE_ISOLATE = "isolate"

#: Deliberately the least surprising default. See the module docstring.
DEFAULT_MODE = MODE_OFF


def implausible_fields(row: dict[str, Any]) -> list[str]:
    """Which aggregate money fields cannot be INR million as stored."""
    out = []
    for field in MONEY_FIELDS:
        value = row.get(field)
        if value is None or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number and abs(number) > IMPOSSIBLE_MILLION:
            out.append(field)
    return out


def inspect(tab_id: str, rows: Sequence[dict[str, Any]], *, source: str,
            mode: Optional[str] = None) -> dict[str, Any]:
    """Classify a batch before it is stored. Never mutates a row.

    Returns the rows to keep, the rows to isolate, and why. In MODE_REPORT
    everything is kept and the finding is only counted, so the guard can be
    watched for a while before it is allowed to change an outcome.
    """
    mode = mode or DEFAULT_MODE
    if mode == MODE_OFF:
        return {"mode": mode, "keep": list(rows), "isolate": [], "findings": []}

    documented = units.SOURCE_DEFAULT_UNIT.get(str(source or "").strip().lower())
    findings: list[dict[str, Any]] = []
    keep: list[dict[str, Any]] = []
    isolate: list[dict[str, Any]] = []

    for row in rows:
        bad = implausible_fields(row)
        if not bad:
            keep.append(row)
            continue
        finding = {
            "symbol": row.get("symbol"),
            "fields": bad,
            "source": source,
            # An undocumented source is the condition that produced this defect
            # in the first place, so it is reported as part of the finding
            # rather than inferred later from the source name.
            "source_unit_documented": documented is not None,
            "documented_unit": documented,
            "reason": ("value cannot be INR million as stored"
                       + ("" if documented else "; source has no documented unit")),
        }
        findings.append(finding)
        if mode == MODE_ISOLATE:
            isolate.append(row)
        else:
            keep.append(row)

    return {"mode": mode, "keep": keep, "isolate": isolate, "findings": findings,
            "would_isolate": len(findings)}
