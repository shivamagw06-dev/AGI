"""Resolve units on real filings and report what would change. Applies nothing.

A shadow pass: it reads filings, resolves each fact's declared unit, and records
the value that *would* result. No stored row is read for writing, no value is
converted, and the result is a report.

On row mapping
--------------
A fact is mapped to a warehouse row only when the filing lineage is known. It
never is: `source_document` and `retrieval_date` are populated on 0 of 102,822
fundamentals rows, no row records which provider answered, and
`statement_version` holds the statement kind ("income", "mixed") rather than a
provenance path. So this pass reports mapped_rows = 0 and says why.

That is the finding, not a limitation to work around. The estimate that 11,307
rows would change value assumes those rows arrived by the XBRL path, and nothing
stored can confirm it. Recording lineage is the prerequisite for converting
anything, and it does not exist yet.
"""

from __future__ import annotations

import collections
import hashlib
import os
import re
from typing import Any, Iterable, Optional

from institutional_warehouse import xbrl_units as xu

#: The two provenance paths for earnings_intelligence_p21. They must never share
#: a unit method: one reads a declared unit, the other multiplies by 100,000 on
#: the comment "Integrated feed often in lakhs".
PATH_XBRL = "nse_xbrl_fact"
PATH_LAKHS = "integrated_summary_lakhs"
PATH_YAHOO = "yahoo_quotesummary"

#: What the importer currently assumes for these feeds, via resolve_unit's
#: fallback: no entry in SOURCE_DEFAULT_UNIT, so the value is treated as already
#: INR million.
CURRENT_ASSUMPTION = "inr_million (assumed_canonical)"

_FACT_RE = re.compile(
    r"<((?:[\w-]+):([A-Za-z0-9_.-]+))\s+([^>]*?)/?>\s*([-+]?[0-9][0-9,]*\.?[0-9]*)?", re.S)
_ATTR_RE = re.compile(r'([\w:.-]+)="([^"]*)"')


def _attrs(text: str) -> dict[str, str]:
    return {k: v for k, v in _ATTR_RE.findall(text or "")}


def scan_document(document: str, *, filing_url: str = "", provider: str = "",
                  path: str = PATH_XBRL, company: str = "") -> dict[str, Any]:
    """Every numeric fact in one filing, with its resolved unit. Reads only."""
    digest = hashlib.sha256((document or "").encode("utf-8", "replace")).hexdigest()
    units = xu.parse_units(document)
    inline = xu.is_inline_xbrl(document)

    facts: list[dict[str, Any]] = []
    counts: collections.Counter = collections.Counter()

    for match in _FACT_RE.finditer(document or ""):
        qname, local, attr_text, raw = match.group(1), match.group(2), match.group(3), match.group(4)
        if raw is None or local in ("unit", "measure", "context", "divide"):
            continue
        attrs = _attrs(attr_text)
        if "contextRef" not in attrs:
            continue
        fact = {
            "unitRef": attrs.get("unitRef"),
            "decimals": attrs.get("decimals"),
            "scale": attrs.get("scale"),
            "sign": attrs.get("sign"),
            "raw_value": raw.replace(",", ""),
        }
        resolved = xu.resolve(fact, units)
        if inline and resolved["usable_as_money"]:
            # A plain-XBRL reading of an inline document would ignore @scale.
            resolved = {**resolved, "usable_as_money": False,
                        "normalised_value": None,
                        "reason": "inline_xbrl_scale_not_supported"}

        record = {
            "filing_url": filing_url,
            "filing_sha256": digest,
            "company": company,
            "provider": provider,
            "parser_path": path,
            "fact_qname": qname,
            "concept": local,
            "context_ref": attrs.get("contextRef"),
            "unit_ref": resolved["unit_ref"],
            "resolved_kind": resolved["kind"],
            "resolved_measures": (units.get(str(fact["unitRef"]), {}) or {}).get("measures"),
            "currency": resolved["currency"],
            # Metadata only. Nothing in this module multiplies by it.
            "decimals": resolved["decimals"],
            "inline_scale": fact["scale"],
            "inline_sign": fact["sign"],
            "raw_value": resolved["raw_value"],
            "proposed_normalised_value": resolved["normalised_value"],
            "proposed_scale_factor": resolved["scale_factor"],
            "transform": resolved["transform"],
            "outcome": resolved["reason"],
            "current_assumption": CURRENT_ASSUMPTION,
            # Would the resolved treatment differ from what the importer does now?
            "differs_from_current": bool(resolved["usable_as_money"]),
            "applied": False,
        }
        facts.append(record)

        if resolved["usable_as_money"]:
            counts["disagreement_would_convert"] += 1
        elif resolved["reason"] == "compound_unit_is_not_an_aggregate":
            counts["unsupported_compound_unit"] += 1
        elif resolved["reason"] == "inline_xbrl_scale_not_supported":
            counts["inline_xbrl_rejected"] += 1
        elif resolved["reason"] in ("shares_is_not_money", "pure_is_not_money"):
            counts["agreement_not_money"] += 1
        else:
            counts["unknown_fails_closed"] += 1

    return {"filing_sha256": digest, "company": company, "provider": provider,
            "parser_path": path, "inline": inline, "units": units,
            "facts": facts, "counts": counts}


def shadow(paths: Iterable[str], *, provider: str = "nse_india",
           sample_per_outcome: int = 3) -> dict[str, Any]:
    """Run the shadow over a set of filings and summarise. Applies nothing."""
    counts: collections.Counter = collections.Counter()
    by_concept: collections.Counter = collections.Counter()
    by_company: collections.Counter = collections.Counter()
    by_filing: dict[str, dict[str, int]] = {}
    by_path: collections.Counter = collections.Counter()
    samples: dict[str, list[dict[str, Any]]] = {}
    filings = 0
    unit_shapes: collections.Counter = collections.Counter()

    for path_name in paths:
        try:
            document = open(path_name, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        company = os.path.basename(os.path.dirname(path_name))
        result = scan_document(document, filing_url=path_name, provider=provider,
                               path=PATH_XBRL, company=company)
        filings += 1
        counts.update(result["counts"])
        by_filing[result["filing_sha256"][:16]] = dict(result["counts"])
        for unit in result["units"].values():
            unit_shapes[f"{unit['kind']}:{','.join(unit['measures'])}"] += 1
        for fact in result["facts"]:
            by_path[fact["parser_path"]] += 1
            if fact["differs_from_current"]:
                by_concept[fact["concept"]] += 1
                by_company[company] += 1
            bucket = samples.setdefault(fact["outcome"], [])
            if len(bucket) < sample_per_outcome:
                bucket.append(fact)

    total = sum(counts.values())
    return {
        "ok": True,
        "applied": False,
        "read_only": True,
        "filings_scanned": filings,
        "facts_examined": total,
        "counts": dict(counts),
        "rates": {k: round(100.0 * v / total, 2) for k, v in counts.items()} if total else {},
        "unit_shapes": dict(unit_shapes),
        "by_concept_would_convert": dict(by_concept.most_common(20)),
        "by_company_would_convert": dict(by_company.most_common(20)),
        "by_parser_path": dict(by_path),
        "by_filing": by_filing,
        "row_mapping": {
            "mapped_rows": 0,
            "why": ("no stored row records its filing: source_document and "
                    "retrieval_date are populated on 0 of 102,822 fundamentals "
                    "rows, provider is not recorded, and statement_version holds "
                    "the statement kind rather than a provenance path"),
            "consequence": ("the estimate that 11,307 rows would change value "
                            "remains a hypothesis; it assumes those rows arrived "
                            "by the XBRL path and nothing stored can confirm it"),
        },
        "verification_samples": samples,
    }


def index_declared_facts(scans: Iterable[dict[str, Any]],
                         concepts: Optional[set] = None) -> dict[tuple, list[dict[str, Any]]]:
    """Index declared money facts by (company, exact value).

    The basis for the one lineage signal that does not need recorded provenance:
    a stored value identical to a filing fact, to the cent, did not arrive by
    coincidence.
    """
    index: dict[tuple, list[dict[str, Any]]] = {}
    for scan in scans:
        for fact in scan.get("facts", []):
            if fact["outcome"] != "declared":
                continue
            if concepts is not None and fact["concept"] not in concepts:
                continue
            try:
                value = round(float(fact["raw_value"]), 2)
            except (TypeError, ValueError):
                continue
            if value:
                index.setdefault((fact["company"], value), []).append(fact)
    return index


def confirm_lineage(rows: Iterable[dict[str, Any]], index: dict[tuple, list[dict[str, Any]]],
                    *, fields: Iterable[str]) -> dict[str, Any]:
    """Which stored rows can be proven to have come by the XBRL path.

    Recorded lineage does not exist - source_document and retrieval_date are
    populated on 0 of 102,822 fundamentals rows - so this matches on the value
    itself. A row whose stored number equals a declared fact to the cent came
    from that fact, and is therefore absolute rupees.

    Only rows this confirms may be treated as known. Everything else stays a
    hypothesis, which is the whole point of running it.
    """
    confirmed: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        for field in fields:
            try:
                value = round(float(row.get(field)), 2)
            except (TypeError, ValueError):
                continue
            if not value:
                continue
            hits = index.get((symbol, value))
            if not hits:
                continue
            entry = confirmed.setdefault(str(row.get("row_id")), {
                "row_id": row.get("row_id"), "symbol": symbol,
                "source": row.get("source"), "matched_fields": [],
                "filings": set(), "concepts": set(),
            })
            entry["matched_fields"].append(field)
            entry["filings"].add(hits[0]["filing_sha256"])
            entry["concepts"].add(hits[0]["concept"])
    for entry in confirmed.values():
        entry["filings"] = sorted(entry["filings"])
        entry["concepts"] = sorted(entry["concepts"])
    return {"confirmed_rows": len(confirmed), "rows": confirmed,
            "basis": "stored value identical to a declared XBRL fact"}
