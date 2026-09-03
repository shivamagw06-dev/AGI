"""Confirmation trusts the stored plan and nothing the browser sends."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from portfolio_import.apply import ConfirmError, build_writes
from portfolio_import.reconcile import basis_hash, build_plan

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
OWNER = "user-1"


def held(**over):
    row = {"id": "h1", "source": "NSDL", "account_ref": "IN30001234567890",
           "isin": "INE002A01018", "folio": None, "quantity": 25.0,
           "average_cost": 2715.4}
    row.update(over)
    return row


def parsed(**over):
    row = {"isin": "INE002A01018", "account_ref": "IN30001234567890",
           "folio": None, "quantity": 30.0, "average_cost": 2715.4,
           "name": "Reliance Industries"}
    row.update(over)
    return row


def make_plan(existing, incoming, **over):
    plan = build_plan(parsed_holdings=incoming, existing_holdings=existing,
                      source="NSDL", statement_date="2026-08-31",
                      statement_accounts=["IN30001234567890"])
    row = {"user_id": OWNER, "status": "parsed",
           "expires_at": (NOW + timedelta(hours=1)).isoformat(),
           "plan_summary": plan.as_dict()}
    row.update(over)
    return row, plan


class OwnershipAndLifecycle(unittest.TestCase):
    def test_another_users_plan_is_refused(self):
        row, plan = make_plan([held()], [parsed()])
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                         caller_user_id="someone-else",
                         current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "not_your_import")

    def test_an_expired_plan_is_refused(self):
        row, plan = make_plan([held()], [parsed()],
                              expires_at=(NOW - timedelta(minutes=1)).isoformat())
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                         caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "import_expired")

    def test_an_unreadable_expiry_fails_closed(self):
        row, plan = make_plan([held()], [parsed()], expires_at="not a date")
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                         caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "import_expired")

    def test_an_already_confirmed_plan_cannot_be_applied_twice(self):
        row, plan = make_plan([held()], [parsed()], status="confirmed")
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                         caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "import_already_resolved")


class TheBrowserIsNotTrusted(unittest.TestCase):
    def test_only_row_ids_are_honoured_never_supplied_holdings(self):
        """A confirm that carried its own rows could write any position."""
        row, plan = make_plan([held()], [parsed()])
        batch = build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                             caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(len(batch.updates), 1)
        # The quantity comes from the stored plan, not from any input here.
        self.assertEqual(batch.updates[0]["fields"]["quantity"], 30.0)

    def test_an_unknown_row_id_is_recorded_not_silently_ignored(self):
        row, plan = make_plan([held()], [parsed()])
        batch = build_writes(plan=row,
                             selected_row_ids=[plan.updates[0]["row_id"], "deadbeef"],
                             caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(batch.skipped_unknown_rows, ["deadbeef"])
        self.assertEqual(len(batch.updates), 1)

    def test_a_selection_of_only_unknown_rows_is_refused(self):
        row, _ = make_plan([held()], [parsed()])
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=["nope"], caller_user_id=OWNER,
                         current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "no_valid_rows_selected")

    def test_an_empty_selection_is_refused(self):
        row, _ = make_plan([held()], [parsed()])
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[], caller_user_id=OWNER,
                         current_holdings=[held()], now=NOW)
        self.assertEqual(ctx.exception.code, "nothing_selected")

    def test_a_duplicated_row_id_is_applied_once(self):
        row, plan = make_plan([held()], [parsed()])
        rid = plan.updates[0]["row_id"]
        batch = build_writes(plan=row, selected_row_ids=[rid, rid, rid],
                             caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(len(batch.updates), 1)


class Integrity(unittest.TestCase):
    def test_a_portfolio_that_moved_invalidates_the_plan(self):
        """Applying it would write changes the client never reviewed."""
        row, plan = make_plan([held()], [parsed()])
        moved = [held(quantity=999.0)]
        with self.assertRaises(ConfirmError) as ctx:
            build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                         caller_user_id=OWNER, current_holdings=moved, now=NOW)
        self.assertEqual(ctx.exception.code, "portfolio_changed")

    def test_an_unchanged_portfolio_passes_the_check(self):
        row, plan = make_plan([held()], [parsed()])
        batch = build_writes(plan=row, selected_row_ids=[plan.updates[0]["row_id"]],
                             caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertFalse(batch.is_empty)

    def test_the_basis_covers_quantity_not_just_membership(self):
        one = basis_hash([held(quantity=25.0)])
        two = basis_hash([held(quantity=26.0)])
        self.assertNotEqual(one, two)


class Selection(unittest.TestCase):
    def test_a_client_can_import_some_rows_and_not_others(self):
        row, plan = make_plan(
            [], [parsed(), parsed(isin="INE009A01021", name="Infosys")])
        chosen = plan.adds[0]["row_id"]
        batch = build_writes(plan=row, selected_row_ids=[chosen],
                             caller_user_id=OWNER, current_holdings=[], now=NOW)
        self.assertEqual(len(batch.inserts), 1)
        self.assertEqual(batch.inserts[0]["row_id"], chosen)

    def test_a_closure_marks_inactive_rather_than_deleting(self):
        row, plan = make_plan([held()], [])
        batch = build_writes(plan=row, selected_row_ids=[plan.closures[0]["row_id"]],
                             caller_user_id=OWNER, current_holdings=[held()], now=NOW)
        self.assertEqual(len(batch.closures), 1)
        self.assertIs(batch.closures[0]["fields"]["is_active"], False)
        self.assertIn("closed_at", batch.closures[0]["fields"])

    def test_inserts_carry_the_statement_date_as_of(self):
        row, plan = make_plan([], [parsed()])
        batch = build_writes(plan=row, selected_row_ids=[plan.adds[0]["row_id"]],
                             caller_user_id=OWNER, current_holdings=[], now=NOW)
        self.assertEqual(batch.inserts[0]["as_of_date"], "2026-08-31")


class FingerprintIsNotPublic(unittest.TestCase):
    def test_the_plan_shown_to_a_client_omits_the_statement_fingerprint(self):
        """It identifies the document; a keyed digest still should not travel."""
        _, plan = make_plan([held()], [parsed()])
        self.assertNotIn("statement_fingerprint", plan.as_dict())


if __name__ == "__main__":
    unittest.main()
