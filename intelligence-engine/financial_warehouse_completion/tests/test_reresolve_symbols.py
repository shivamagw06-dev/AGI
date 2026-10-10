"""Filling in symbols the master could not supply when the row was written."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from financial_warehouse_completion import insider_trades as it


STORED = [
    {"company_name": "Panacea Biotec", "symbol": None, "reported_on": "2026-08-25"},
    {"company_name": "Hindustan Foods", "symbol": "", "reported_on": "2026-08-25"},
    {"company_name": "Some Unlisted Co", "symbol": None, "reported_on": "2026-08-25"},
]

INDEX = ({"panacea biotec": "PANACEABIO", "hindustan foods": "HNDFDS"},
         [("panacea biotec", "PANACEABIO"), ("hindustan foods", "HNDFDS")])


def _patch(rows=STORED, index=INDEX, write=None):
    import institutional_warehouse.db as db
    import institutional_warehouse.gateway as gw
    return (
        mock.patch.object(db, "physical_table", return_value="insider_trades"),
        mock.patch.object(db, "query", return_value=rows),
        mock.patch.object(it, "symbol_index", return_value=index),
        mock.patch.object(gw, "write",
                          return_value=write or {"ok": True, "updated": 2}),
    )


def run(**kw):
    patches = _patch(**{k: v for k, v in kw.items() if k in ("rows", "index", "write")})
    for p in patches:
        p.start()
    try:
        return it.reresolve_symbols(dry_run=kw.get("dry_run", True))
    finally:
        for p in patches:
            p.stop()


class Resolving(unittest.TestCase):
    def test_it_fills_the_rows_the_master_can_now_name(self):
        out = run()
        self.assertEqual(out["unresolved_before"], 3)
        self.assertEqual(out["now_resolvable"], 2)
        self.assertEqual(out["still_unmatched"], 1)

    def test_a_company_the_master_still_does_not_know_stays_blank(self):
        # Rather than a fabricated ticker.
        out = run()
        self.assertNotIn("Some Unlisted Co", [s["company"] for s in out["sample"]])

    def test_a_dry_run_writes_nothing(self):
        import institutional_warehouse.gateway as gw
        with mock.patch.object(gw, "write") as write:
            run(dry_run=True)
        write.assert_not_called()

    def test_applying_writes_only_the_rows_it_resolved(self):
        import institutional_warehouse.gateway as gw
        captured = {}

        def fake_write(tab, rows, **kw):
            captured["rows"] = rows
            captured["reason"] = kw.get("reason")
            return {"ok": True, "updated": len(rows)}

        patches = _patch()
        for p in patches[:3]:
            p.start()
        with mock.patch.object(gw, "write", side_effect=fake_write):
            out = it.reresolve_symbols(dry_run=False)
        for p in patches[:3]:
            p.stop()
        self.assertEqual(len(captured["rows"]), 2)
        self.assertTrue(all(r["symbol"] for r in captured["rows"]))
        self.assertIn("master", captured["reason"])


class Guards(unittest.TestCase):
    def test_an_empty_master_index_is_refused_not_reported_clean(self):
        # Resolving nothing against an empty index would report a successful
        # run that changed nothing, which is how a broken master looks like a
        # finished job.
        out = run(index=({}, []))
        self.assertFalse(out["ok"])
        self.assertEqual(out["stage"], "index")

    def test_nothing_unresolved_is_success_not_an_error(self):
        out = run(rows=[])
        self.assertTrue(out["ok"])
        self.assertEqual(out["unresolved"], 0)

    def test_rows_that_already_resolved_are_never_revisited(self):
        # The query asks only for blank symbols. Re-deciding a match a person
        # may have seen and trusted is a different operation.
        import institutional_warehouse.db as db
        seen = {}

        def fake_query(sql):
            seen["sql"] = sql
            return STORED

        with mock.patch.object(db, "physical_table", return_value="insider_trades"), \
             mock.patch.object(db, "query", side_effect=fake_query), \
             mock.patch.object(it, "symbol_index", return_value=INDEX):
            it.reresolve_symbols(dry_run=True)
        self.assertIn("symbol IS NULL", seen["sql"])


if __name__ == "__main__":
    unittest.main()
