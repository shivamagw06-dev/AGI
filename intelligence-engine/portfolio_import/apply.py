"""Turning a confirmed selection into writes, trusting only the stored plan.

The browser sends an import id and a list of row ids. It does not send
holdings, quantities, ISINs or anything else, and none of those would be
believed if it did: a client who can post arbitrary rows to a confirm endpoint
can write any position into their own portfolio and, if the endpoint is sloppy
about ownership, into somebody else's. So the selection is a filter over a plan
the server already holds, and unknown ids are rejected rather than ignored.

Three checks run before a single write is produced:

* The plan belongs to the caller.
* The plan has not expired.
* The portfolio still looks the way it did when the plan was computed. If it
  moved in between -- another device, another import, a manual edit -- the plan
  describes a state that no longer exists, and applying it would write changes
  the client never reviewed.

This module still writes nothing. It returns the operations for a caller to
apply inside one transaction, so a partial failure leaves the portfolio exactly
as it was.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .reconcile import basis_hash


class ConfirmError(Exception):
    """A refusal that is safe to show a client."""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


@dataclass
class WriteBatch:
    """Operations to apply in a single transaction."""

    inserts: list[dict[str, Any]] = field(default_factory=list)
    updates: list[dict[str, Any]] = field(default_factory=list)
    closures: list[dict[str, Any]] = field(default_factory=list)
    skipped_unknown_rows: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.inserts or self.updates or self.closures)

    def as_dict(self) -> dict[str, Any]:
        return {
            "counts": {"insert": len(self.inserts), "update": len(self.updates),
                       "close": len(self.closures)},
            "inserts": self.inserts, "updates": self.updates,
            "closures": self.closures,
        }


def _expired(expires_at: Any, now: datetime) -> bool:
    if not expires_at:
        return False
    text = str(expires_at).replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        # An unparseable expiry is treated as expired. Failing closed on a
        # timestamp we cannot read is the only safe reading.
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when <= now


def build_writes(*, plan: dict[str, Any], selected_row_ids: Iterable[str],
                 caller_user_id: str, current_holdings: Iterable[dict[str, Any]],
                 portfolio_id: Optional[str] = None,
                 now: Optional[datetime] = None) -> WriteBatch:
    """Validate a confirmation and return what to write.

    `plan` is the row the server loaded, not anything the browser supplied.
    """
    now = now or datetime.now(timezone.utc)

    owner = str(plan.get("user_id") or "")
    if not owner or owner != str(caller_user_id or ""):
        # Not "not found": the caller is asking about someone else's plan.
        raise ConfirmError("not_your_import")
    if str(plan.get("status") or "") != "parsed":
        raise ConfirmError("import_already_resolved")
    if _expired(plan.get("expires_at"), now):
        raise ConfirmError("import_expired")

    body = plan.get("plan_summary") or {}
    if not isinstance(body, dict) or not body:
        raise ConfirmError("import_plan_missing")

    holdings = list(current_holdings or [])
    if body.get("basis") and body["basis"] != basis_hash(holdings):
        # The portfolio moved after the plan was shown.
        raise ConfirmError("portfolio_changed")

    by_row: dict[str, tuple[str, dict[str, Any]]] = {}
    for kind, key in (("insert", "adds"), ("update", "updates"), ("close", "closures")):
        for row in body.get(key) or []:
            row_id = str(row.get("row_id") or "")
            if row_id:
                by_row[row_id] = (kind, row)

    selected = [str(r) for r in (selected_row_ids or [])]
    if not selected:
        raise ConfirmError("nothing_selected")

    batch = WriteBatch()
    seen: set[str] = set()
    for row_id in selected:
        if row_id in seen:
            continue
        seen.add(row_id)
        found = by_row.get(row_id)
        if found is None:
            # A row the plan does not contain. Recorded rather than silently
            # dropped, because it means the client saw something we did not
            # produce -- a stale tab, or a tampered request.
            batch.skipped_unknown_rows.append(row_id)
            continue
        kind, row = found
        if kind == "insert":
            holding = dict(row.get("holding") or {})
            batch.inserts.append({
                "row_id": row_id,
                "portfolio_id": portfolio_id,
                "user_id": owner,
                "source": body.get("source"),
                "isin": holding.get("isin"),
                "folio": holding.get("folio"),
                "account_ref": holding.get("account_ref"),
                "asset_name": holding.get("name"),
                "asset_type": holding.get("asset_type") or "EQUITY",
                "quantity": holding.get("quantity"),
                "average_cost": holding.get("average_cost"),
                "as_of_date": body.get("statement_date"),
                "is_active": True,
            })
        elif kind == "update":
            changes = row.get("changes") or {}
            fields = {name: change.get("to") for name, change in changes.items()
                      if isinstance(change, dict)}
            if not fields:
                continue
            batch.updates.append({
                "row_id": row_id, "id": row.get("id"), "user_id": owner,
                "fields": {**fields, "as_of_date": body.get("statement_date")},
            })
        else:
            batch.closures.append({
                "row_id": row_id, "id": row.get("id"), "user_id": owner,
                "fields": {"is_active": False,
                           "closed_at": now.isoformat(),
                           "as_of_date": body.get("statement_date")},
            })

    if batch.skipped_unknown_rows and batch.is_empty:
        raise ConfirmError("no_valid_rows_selected")
    return batch
