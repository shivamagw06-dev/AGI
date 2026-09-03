"""What a confirmed import would change, worked out before anything is written.

This module returns a plan. It performs no writes, which is the whole point:
the client sees adds, updates and closures and confirms them, and only then
does a caller apply the plan. A parse that goes wrong therefore costs a review
screen, not a portfolio.

The identity of a lot is:

    (portfolio_id, source, account_ref, isin_or_folio)

not the ISIN alone. The same stock held in two demat accounts is two lots and
stays two lots, because a single merged row cannot carry two average costs and
cannot be unpicked when one account is disconnected. The portfolio view adds
them up; the store keeps them apart.

The closure rule carries the subtlety that matters most here. A holding absent
from a statement is only evidence of a sale if the statement covered the
account it lived in. An NSDL CAS says nothing about a CDSL demat, and a
CAMS statement says nothing about shares. Closing on absence alone would empty
a client's portfolio the first time they uploaded a partial statement, so
closure is scoped to the accounts the statement actually reported.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

MANUAL = "MANUAL"


def row_id(kind: str, key: tuple) -> str:
    """A stable id for one proposed change.

    The browser sends these back to say which rows to import, so they must be
    derived from the change itself rather than from list position: a plan
    rebuilt in a different order would otherwise silently reassign a client's
    selection to different holdings.
    """
    raw = json.dumps([kind, [str(part) if part is not None else None for part in key]],
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def basis_hash(existing_holdings: Iterable[dict[str, Any]]) -> str:
    """A digest of the portfolio the plan was computed against.

    Checked again at confirmation. If the portfolio moved in between -- another
    device, another import, a manual edit -- the plan describes a state that no
    longer exists, and applying it would write changes the client never saw.
    """
    rows = sorted(
        (f"{r.get('id')}|{r.get('source')}|{r.get('account_ref')}|{r.get('isin')}"
         f"|{r.get('folio')}|{r.get('quantity')}|{r.get('average_cost')}"
         for r in existing_holdings or []))
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def lot_key(*, source: str, account_ref: Optional[str],
            isin: Optional[str], folio: Optional[str]) -> tuple:
    """The identity a lot is matched on across imports."""
    return (str(source or "").upper(),
            str(account_ref or "").strip().upper() or None,
            str(isin or "").strip().upper() or None,
            str(folio or "").strip().upper() or None)


@dataclass
class ImportPlan:
    source: str
    statement_date: Optional[str] = None
    statement_fingerprint: Optional[str] = None
    already_imported: bool = False
    basis: str = ""
    adds: list[dict[str, Any]] = field(default_factory=list)
    updates: list[dict[str, Any]] = field(default_factory=list)
    closures: list[dict[str, Any]] = field(default_factory=list)
    unchanged: list[dict[str, Any]] = field(default_factory=list)
    review_queue: list[dict[str, Any]] = field(default_factory=list)
    protected_manual: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "statement_date": self.statement_date,
            # Deliberately not the fingerprint: it identifies the document and
            # is never returned to a browser.
            "already_imported": self.already_imported,
            "basis": self.basis,
            "counts": {
                "add": len(self.adds), "update": len(self.updates),
                "close": len(self.closures), "unchanged": len(self.unchanged),
                "review": len(self.review_queue),
                "manual_protected": self.protected_manual,
            },
            "adds": self.adds, "updates": self.updates,
            "closures": self.closures, "unchanged": self.unchanged,
            "review_queue": self.review_queue,
            "warnings": self.warnings,
        }


def _changed(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key, incoming_value in (("quantity", incoming.get("quantity")),
                                ("average_cost", incoming.get("average_cost"))):
        if incoming_value is None:
            continue
        current = existing.get(key)
        if current is None or abs(float(current) - float(incoming_value)) > 1e-9:
            fields[key] = {"from": current, "to": incoming_value}
    return fields


def build_plan(*, parsed_holdings: Iterable[dict[str, Any]],
               existing_holdings: Iterable[dict[str, Any]],
               source: str,
               statement_accounts: Optional[Iterable[str]] = None,
               statement_date: Optional[str] = None,
               statement_fingerprint: Optional[str] = None,
               previous_fingerprints: Optional[Iterable[str]] = None,
               unmatched: Optional[Iterable[dict[str, Any]]] = None) -> ImportPlan:
    """Work out adds, updates and closures without applying any of them."""
    plan = ImportPlan(source=str(source or "").upper(),
                      statement_date=statement_date,
                      statement_fingerprint=statement_fingerprint)

    # Re-uploading the same file must be a no-op rather than a duplicate. The
    # fingerprint is a digest of the document, so this holds without keeping
    # the document.
    if statement_fingerprint and statement_fingerprint in set(previous_fingerprints or ()):
        plan.already_imported = True
        plan.warnings.append(
            "This statement has already been imported. Nothing will change.")
        return plan

    existing_list = list(existing_holdings or [])
    plan.basis = basis_hash(existing_list)

    existing_by_key: dict[tuple, dict[str, Any]] = {}
    for row in existing_list:
        row_source = str(row.get("source") or MANUAL).upper()
        if row_source == MANUAL:
            # Never touched by an import, and not counted as a candidate for
            # closure either: a client's own entry is not the statement's to
            # contradict.
            plan.protected_manual += 1
            continue
        existing_by_key[lot_key(source=row_source,
                                account_ref=row.get("account_ref"),
                                isin=row.get("isin"),
                                folio=row.get("folio"))] = row

    scoped_accounts = {str(a).strip().upper() for a in (statement_accounts or ()) if a}
    seen_keys: set[tuple] = set()

    for holding in parsed_holdings or []:
        isin = holding.get("isin")
        folio = holding.get("folio")
        if not isin and not folio:
            # Nothing to identify it by. It goes to review, never to holdings.
            plan.review_queue.append({"reason": "no_isin_or_folio", "holding": holding})
            continue
        key = lot_key(source=plan.source, account_ref=holding.get("account_ref"),
                      isin=isin, folio=folio)
        seen_keys.add(key)
        current = existing_by_key.get(key)
        if current is None:
            plan.adds.append({"row_id": row_id("add", key), "key": list(key),
                              "holding": holding})
            continue
        diff = _changed(current, holding)
        if diff:
            plan.updates.append({"row_id": row_id("update", key), "key": list(key),
                                 "id": current.get("id"), "changes": diff,
                                 "holding": holding})
        else:
            plan.unchanged.append({"key": list(key), "id": current.get("id")})

    for key, row in existing_by_key.items():
        if key in seen_keys:
            continue
        if str(row.get("source") or "").upper() != plan.source:
            # Another broker's lot. This statement is silent about it.
            continue
        account = (key[1] or "")
        if scoped_accounts and account and account not in scoped_accounts:
            # The statement did not cover the account this lot lives in, so its
            # absence is not evidence of a sale.
            continue
        if scoped_accounts and not account:
            continue
        plan.closures.append({"row_id": row_id("close", key), "key": list(key),
                              "id": row.get("id"),
                              "quantity": row.get("quantity"),
                              "reason": "absent_from_statement"})

    for row in unmatched or []:
        plan.review_queue.append({"reason": row.get("reason") or "unparsed",
                                  "excerpt": row.get("excerpt")})

    if plan.closures:
        plan.warnings.append(
            f"{len(plan.closures)} holding(s) are absent from this statement and "
            "would be marked inactive. They are not deleted and can be restored.")
    return plan
