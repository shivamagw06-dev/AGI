"""What a confirmed import would change — and what it must never change."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from portfolio_import.reconcile import build_plan, lot_key


def held(**over):
    row = {"id": "h1", "source": "NSDL", "account_ref": "IN30001234567890",
           "isin": "INE002A01018", "folio": None, "quantity": 25.0,
           "average_cost": 2715.4}
    row.update(over)
    return row


def parsed(**over):
    row = {"isin": "INE002A01018", "account_ref": "IN30001234567890",
           "folio": None, "quantity": 25.0, "average_cost": 2715.4,
           "name": "Reliance Industries"}
    row.update(over)
    return row


class Identity(unittest.TestCase):
    def test_the_same_stock_in_two_accounts_is_two_lots(self):
        """A merged row cannot carry two average costs."""
        a = lot_key(source="NSDL", account_ref="IN3000", isin="INE002A01018", folio=None)
        b = lot_key(source="NSDL", account_ref="IN9999", isin="INE002A01018", folio=None)
        self.assertNotEqual(a, b)

    def test_two_brokers_holding_one_isin_produce_two_adds(self):
        plan = build_plan(
            parsed_holdings=[parsed(account_ref="IN3000"), parsed(account_ref="IN9999")],
            existing_holdings=[], source="NSDL")
        self.assertEqual(len(plan.adds), 2)


class NothingIsWrittenHere(unittest.TestCase):
    def test_the_plan_is_only_a_plan(self):
        existing = [held()]
        plan = build_plan(parsed_holdings=[parsed(quantity=30)],
                          existing_holdings=existing, source="NSDL")
        self.assertEqual(len(plan.updates), 1)
        # The input is untouched: applying is a separate, confirmed step.
        self.assertEqual(existing[0]["quantity"], 25.0)


class Updates(unittest.TestCase):
    def test_a_quantity_change_is_an_update_with_both_values(self):
        plan = build_plan(parsed_holdings=[parsed(quantity=30)],
                          existing_holdings=[held()], source="NSDL")
        self.assertEqual(len(plan.updates), 1)
        self.assertEqual(plan.updates[0]["changes"]["quantity"],
                         {"from": 25.0, "to": 30})

    def test_an_unchanged_holding_is_not_an_update(self):
        plan = build_plan(parsed_holdings=[parsed()],
                          existing_holdings=[held()], source="NSDL")
        self.assertEqual(plan.updates, [])
        self.assertEqual(len(plan.unchanged), 1)

    def test_a_corporate_action_quantity_change_is_reported_not_hidden(self):
        """A 1:2 split doubles the quantity; the client sees the change."""
        plan = build_plan(parsed_holdings=[parsed(quantity=50)],
                          existing_holdings=[held(quantity=25.0)], source="NSDL")
        self.assertEqual(plan.updates[0]["changes"]["quantity"]["to"], 50)


class ManualHoldingsAreUntouchable(unittest.TestCase):
    def test_a_manual_holding_is_never_updated_or_closed(self):
        manual = held(id="m1", source="MANUAL")
        plan = build_plan(parsed_holdings=[], existing_holdings=[manual], source="NSDL")
        self.assertEqual(plan.updates, [])
        self.assertEqual(plan.closures, [])
        self.assertEqual(plan.protected_manual, 1)

    def test_a_manual_row_for_the_same_isin_does_not_block_an_import(self):
        manual = held(id="m1", source="MANUAL")
        plan = build_plan(parsed_holdings=[parsed()], existing_holdings=[manual],
                          source="NSDL")
        self.assertEqual(len(plan.adds), 1)
        self.assertEqual(plan.protected_manual, 1)


class Closures(unittest.TestCase):
    def test_a_sold_holding_is_marked_not_deleted(self):
        plan = build_plan(parsed_holdings=[], existing_holdings=[held()],
                          source="NSDL", statement_accounts=["IN30001234567890"])
        self.assertEqual(len(plan.closures), 1)
        self.assertEqual(plan.closures[0]["reason"], "absent_from_statement")

    def test_a_partial_statement_does_not_close_another_account(self):
        """An NSDL CAS says nothing about a CDSL demat."""
        other = held(id="h2", account_ref="1201060000123456")
        plan = build_plan(parsed_holdings=[parsed()], existing_holdings=[held(), other],
                          source="NSDL", statement_accounts=["IN30001234567890"])
        closed_ids = {c["id"] for c in plan.closures}
        self.assertNotIn("h2", closed_ids)

    def test_another_brokers_lot_is_never_closed_by_this_statement(self):
        other = held(id="h3", source="CDSL", account_ref="1201060000123456")
        plan = build_plan(parsed_holdings=[parsed()],
                          existing_holdings=[held(), other], source="NSDL",
                          statement_accounts=["IN30001234567890"])
        self.assertNotIn("h3", {c["id"] for c in plan.closures})

    def test_closures_are_warned_about(self):
        plan = build_plan(parsed_holdings=[], existing_holdings=[held()],
                          source="NSDL", statement_accounts=["IN30001234567890"])
        self.assertTrue(any("marked inactive" in w for w in plan.warnings))


class Idempotence(unittest.TestCase):
    def test_reimporting_the_same_statement_changes_nothing(self):
        plan = build_plan(parsed_holdings=[parsed(quantity=999)],
                          existing_holdings=[held()], source="NSDL",
                          statement_fingerprint="abc123",
                          previous_fingerprints=["abc123"])
        self.assertTrue(plan.already_imported)
        self.assertEqual(plan.adds, [])
        self.assertEqual(plan.updates, [])
        self.assertEqual(plan.closures, [])

    def test_a_different_statement_is_not_blocked(self):
        plan = build_plan(parsed_holdings=[parsed(quantity=30)],
                          existing_holdings=[held()], source="NSDL",
                          statement_fingerprint="def456",
                          previous_fingerprints=["abc123"])
        self.assertFalse(plan.already_imported)
        self.assertEqual(len(plan.updates), 1)


class ReviewQueue(unittest.TestCase):
    def test_an_unidentifiable_holding_goes_to_review_not_to_holdings(self):
        plan = build_plan(parsed_holdings=[parsed(isin=None, folio=None)],
                          existing_holdings=[], source="NSDL")
        self.assertEqual(plan.adds, [])
        self.assertEqual(len(plan.review_queue), 1)
        self.assertEqual(plan.review_queue[0]["reason"], "no_isin_or_folio")

    def test_parser_rejects_are_carried_into_the_review_queue(self):
        plan = build_plan(parsed_holdings=[parsed()], existing_holdings=[],
                          source="NSDL",
                          unmatched=[{"reason": "isin_line_did_not_parse",
                                      "excerpt": "INE0... masked"}])
        self.assertEqual(len(plan.review_queue), 1)


if __name__ == "__main__":
    unittest.main()
