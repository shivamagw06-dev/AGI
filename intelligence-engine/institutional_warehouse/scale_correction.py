"""Correct annual rows stored on the wrong scale, against a reference of record.

The census found 12,431 annual rows holding values impossible for INR million.
Correcting them needs evidence per row, not a blanket multiply: a row is only
correctable when an independent source says what the value should be, and says
it consistently across several fields.

The reference is the Capital IQ 10-year master export already in the repository,
3,008 companies x FY2017-FY2026 x 32 aggregate-money fields. Its unit is not
declared in the file, so it is *inferred* and magnitude-verified - RELIANCE
FY2026 revenue 10,572,190 reads as Rs 10.57 lakh crore, and TCS FY2020 1,569,490
matches the warehouse's own capital_iq_workbook row exactly. That inference is
recorded with the data and should be confirmed against the export settings
before this is run at scale.

Why a row-level factor
----------------------
A feed that reports in rupees reports every money field in rupees. Correcting
only the fields with a reference match would leave a row internally inconsistent
- revenue in millions beside an uncorrected cost in rupees is worse than either
mistake alone. So the factor is derived from the fields that do have evidence,
required to agree across at least MIN_AGREEING_FIELDS of them, and then applied
to every aggregate-money field on the row. A row whose fields disagree about the
factor is not corrected; it is reported for review.

Per-share and count fields are never touched. eps, book_value and
shares_outstanding are not aggregate money, and shares_outstanding is derived
as capital_in_inr_million x 1,000,000 / face_value - scaling it would be the
1,000,000x share-count error this exists to avoid.
"""

from __future__ import annotations

import gzip
import json
import uuid
import re

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from institutional_warehouse import audit, db
from institutional_warehouse.value_plausibility import IMPOSSIBLE_MILLION, MONEY_FIELDS
from institutional_warehouse.values import now_iso


REFERENCE_PATH = (Path(__file__).resolve().parent / "reference"
                  / "capiq_master_10y_inr_million.json.gz")

#: Scale gaps this will correct. Nothing else - a factor of 10 could be a
#: genuine restatement and is not corrected automatically.
KNOWN_FACTORS = {1e6: "rupees stored as INR million",
                 1e7: "crore stored as rupees"}

#: How close a field's implied factor must sit to a known one.
FACTOR_TOLERANCE = 0.15

#: Independent fields that must agree before a row is corrected. One field
#: agreeing with the reference can be coincidence; four cannot.
MIN_AGREEING_FIELDS = 4

TAB = "financials_annual"
_FY4_RE = re.compile(r"(\d{4})")
_FY2_RE = re.compile(r"FY\s*(\d{2})(?!\d)")

_REFERENCE: Optional[Dict[str, Any]] = None


def load_reference() -> Dict[str, Any]:
    global _REFERENCE
    if _REFERENCE is None:
        with gzip.open(REFERENCE_PATH, "rt", encoding="utf-8") as handle:
            _REFERENCE = json.load(handle)
    return _REFERENCE


def fiscal_key(label: Any) -> Optional[str]:
    """Fold FY26, FY2026 and 2026 onto one key.

    The warehouse carries both widths - the census had to fold them too - and a
    two-digit year silently missing the reference would look like "no evidence"
    rather than a parsing gap.
    """
    text = str(label or "").upper().replace(" ", "")
    match = _FY4_RE.search(text)
    if match:
        return f"FY{match.group(1)}"
    match = _FY2_RE.search(text)
    return f"FY20{match.group(1)}" if match else None


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out or out == 0 else out


def _nearest_factor(ratio: float) -> Optional[float]:
    for factor in KNOWN_FACTORS:
        if abs(ratio - factor) / factor <= FACTOR_TOLERANCE:
            return factor
    return None


def assess_row(row: Dict[str, Any], reference: Dict[str, Any]) -> Dict[str, Any]:
    """What the reference says about this row's scale."""
    symbol = str(row.get("symbol") or "").upper()
    year = fiscal_key(row.get("fiscal_year"))
    ref = ((reference.get("data") or {}).get(symbol) or {}).get(year or "") or {}
    verdict: Dict[str, Any] = {
        "row_id": row.get("row_id"), "symbol": symbol, "fiscal_year": year,
        "source": row.get("source"), "reference_fields": len(ref),
        "agreeing_fields": [], "disagreeing_fields": [], "factor": None,
        "correctable": False, "reason": None,
    }
    if not ref:
        verdict["reason"] = "no_reference_for_company_and_year"
        return verdict

    votes: Dict[float, List[str]] = {}
    for field in MONEY_FIELDS:
        stored = _num(row.get(field))
        expected = _num(ref.get(field))
        if stored is None or expected is None:
            continue
        factor = _nearest_factor(abs(stored) / abs(expected))
        if factor:
            votes.setdefault(factor, []).append(field)
        else:
            verdict["disagreeing_fields"].append(field)

    if not votes:
        verdict["reason"] = "no_field_implies_a_known_scale_factor"
        return verdict
    factor, fields = max(votes.items(), key=lambda kv: len(kv[1]))
    verdict["factor"] = factor
    verdict["agreeing_fields"] = sorted(fields)
    if len(fields) < MIN_AGREEING_FIELDS:
        verdict["reason"] = f"only_{len(fields)}_fields_agree_need_{MIN_AGREEING_FIELDS}"
        return verdict
    if len(votes) > 1:
        verdict["reason"] = "fields_disagree_about_the_factor"
        return verdict
    verdict["correctable"] = True
    verdict["reason"] = KNOWN_FACTORS[factor]
    return verdict


def plan(*, symbols: Optional[Iterable[str]] = None,
         sample: int = 20) -> Dict[str, Any]:
    """Every row the reference can vouch for. Writes nothing."""
    db.init()
    reference = load_reference()
    table = db.physical_table(TAB)
    wanted = {str(s).upper() for s in symbols} if symbols else None

    all_symbols = [str(r.get("symbol") or "") for r in db.query(
        f"SELECT DISTINCT symbol FROM {table} WHERE sys_published = 1 ORDER BY symbol")]
    all_symbols = [s for s in all_symbols if s and (wanted is None or s.upper() in wanted)]

    correctable: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}
    scanned = 0
    for symbol in all_symbols:
        for row in db.query(
                f"SELECT * FROM {table} WHERE sys_published = 1 AND symbol = ?", (symbol,)):
            scanned += 1
            # Only rows the census already calls impossible. A row that looks
            # right is not rescaled because a reference happens to differ.
            if not any((_num(row.get(f)) or 0) and abs(_num(row.get(f))) > IMPOSSIBLE_MILLION
                       for f in MONEY_FIELDS):
                continue
            verdict = assess_row(row, reference)
            reasons[verdict["reason"] or "?"] = reasons.get(verdict["reason"] or "?", 0) + 1
            if verdict["correctable"]:
                correctable.append(verdict)

    by_factor: Dict[str, int] = {}
    for item in correctable:
        key = f"{item['factor']:.0e}"
        by_factor[key] = by_factor.get(key, 0) + 1
    return {
        "ok": True, "dry_run": True, "applied": False, "tab": TAB,
        "rows_scanned": scanned,
        "rows_impossible": sum(reasons.values()),
        "rows_correctable": len(correctable),
        "by_factor": by_factor,
        "outcomes": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "reference": {"companies": reference.get("companies"),
                      "unit": reference.get("unit"),
                      "unit_is_inferred": reference.get("unit_is_inferred"),
                      "source_file": reference.get("source_file")},
        "min_agreeing_fields": MIN_AGREEING_FIELDS,
        "sample": correctable[:sample],
        "row_ids": [c["row_id"] for c in correctable],
    }


def _record_run(run_id: str, changes: List[Dict[str, Any]], *, actor: str) -> None:
    """Row-level backup, written before a single value moves."""
    db.execute(
        "INSERT INTO wh_provenance_runs (run_id, created_at, tab_id, kind, actor,"
        " source, from_value, to_value, rows_changed, rolled_back_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,NULL)",
        (run_id, now_iso(), TAB, "scale_correction", actor, "capiq_master_10y",
         "raw", "rescaled", len({c['row_id'] for c in changes})))
    for i in range(0, len(changes), 500):
        db.executemany(
            "INSERT INTO wh_provenance_run_rows (run_id, row_id, tab_id, column_key,"
            " old_value, new_value) VALUES (?,?,?,?,?,?)",
            [(run_id, c["row_id"], TAB, c["field"], repr(c["old"]), repr(c["new"]))
             for c in changes[i:i + 500]])


def apply(*, actor: str, confirm: bool = False, limit: Optional[int] = None,
          symbols: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Rescale the rows the reference vouches for. Refuses without confirmation.

    Every field's prior value is written to wh_provenance_run_rows before the
    update, so the run reverses against the exact rows and values it touched.
    """
    proposal = plan(symbols=symbols, sample=0)
    targets = proposal["row_ids"][:limit] if limit else proposal["row_ids"]
    if not confirm:
        return {"ok": False, "error": "confirm_required",
                "would_change_rows": len(targets), "plan": {
                    k: proposal[k] for k in ("rows_scanned", "rows_impossible",
                                             "rows_correctable", "by_factor", "outcomes")}}
    if not targets:
        return {"ok": True, "changed": 0, "already_done": True}

    db.init()
    table = db.physical_table(TAB)
    reference = load_reference()
    run_id = uuid.uuid4().hex
    changes: List[Dict[str, Any]] = []
    updates: List[tuple] = []

    for i in range(0, len(targets), 400):
        batch = targets[i:i + 400]
        marks = ",".join("?" for _ in batch)
        for row in db.query(f"SELECT * FROM {table} WHERE row_id IN ({marks})", batch):
            verdict = assess_row(row, reference)
            # Re-assessed at write time. A row that changed since the plan was
            # built is skipped rather than corrected against stale evidence.
            if not verdict["correctable"]:
                continue
            factor = verdict["factor"]
            for field in MONEY_FIELDS:
                old = _num(row.get(field))
                if old is None:
                    continue
                new = old / factor
                changes.append({"row_id": row["row_id"], "field": field,
                                "old": old, "new": new})
                updates.append((new, row["row_id"]))

    if not changes:
        return {"ok": True, "changed": 0, "reason": "no row still qualified at write time"}

    _record_run(run_id, changes, actor=actor)
    by_field: Dict[str, List[tuple]] = {}
    for change in changes:
        by_field.setdefault(change["field"], []).append((change["new"], change["row_id"]))
    for field, pairs in by_field.items():
        for i in range(0, len(pairs), 500):
            db.executemany(
                f"UPDATE {table} SET {field} = ? WHERE row_id = ?", pairs[i:i + 500])

    result = {"ok": True, "run_id": run_id,
              "rows_changed": len({c["row_id"] for c in changes}),
              "values_changed": len(changes),
              "rollback": f"scale_correction.rollback('{run_id}', confirm=True)"}
    audit.record("scale_correction", tab_id=TAB, actor=actor, detail=result, ok=True)
    return result


def rollback(run_id: str, *, actor: str, confirm: bool = False) -> Dict[str, Any]:
    """Restore every value this run changed, against its recorded row ids."""
    db.init()
    runs = db.query("SELECT * FROM wh_provenance_runs WHERE run_id = ?", (run_id,))
    if not runs:
        return {"ok": False, "error": f"unknown_run:{run_id}"}
    if runs[0].get("rolled_back_at"):
        return {"ok": True, "already_rolled_back": True, "run_id": run_id}
    rows = db.query(
        "SELECT row_id, column_key, old_value FROM wh_provenance_run_rows WHERE run_id = ?",
        (run_id,))
    if not confirm:
        return {"ok": False, "error": "confirm_required", "values_to_restore": len(rows)}

    table = db.physical_table(TAB)
    by_field: Dict[str, List[tuple]] = {}
    for row in rows:
        by_field.setdefault(str(row["column_key"]), []).append(
            (float(str(row["old_value"])), str(row["row_id"])))
    for field, pairs in by_field.items():
        for i in range(0, len(pairs), 500):
            db.executemany(
                f"UPDATE {table} SET {field} = ? WHERE row_id = ?", pairs[i:i + 500])
    db.execute("UPDATE wh_provenance_runs SET rolled_back_at = ? WHERE run_id = ?",
               (now_iso(), run_id))
    audit.record("scale_correction_rollback", tab_id=TAB, actor=actor,
                 detail={"run_id": run_id, "values_restored": len(rows)}, ok=True)
    return {"ok": True, "run_id": run_id, "values_restored": len(rows)}
