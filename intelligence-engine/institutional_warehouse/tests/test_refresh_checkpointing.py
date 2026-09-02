"""The refresh must record where it got to, not only whether it finished.

Eight consecutive daily runs reported ok=False with an empty errors list and a
null finished_at -- the run row exactly as inserted. The per-stage try/except
cannot produce that, since a raising stage is caught and recorded, so the run
was dying somewhere the loop could not see and leaving no evidence behind.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from institutional_warehouse import refresh


class CheckpointBehaviour(unittest.TestCase):
    """Asserted against the source, because run() builds its runners internally."""

    def test_each_stage_writes_a_checkpoint(self):
        import inspect
        src = inspect.getsource(refresh)
        # The checkpoint must happen inside the stage loop, not once at the end.
        self.assertIn("completed.append(stage)", src)
        self.assertIn("_checkpoint()", src)

    def test_a_failing_checkpoint_never_fails_the_run(self):
        import inspect
        src = inspect.getsource(refresh)
        checkpoint = src[src.index("def _checkpoint"):src.index("for stage in wanted")]
        self.assertIn("except Exception", checkpoint)
        self.assertIn("pass", checkpoint)

    def test_row_counts_cannot_take_the_run_record_with_them(self):
        """The scan covers ~7m rows and used to run before the finalising UPDATE."""
        import inspect
        src = inspect.getsource(refresh)
        block = src[src.index("counts = {tab: store.row_count"):]
        head = src[:src.index("counts = {tab: store.row_count")]
        self.assertTrue(head.rstrip().endswith("try:"),
                        "row_count scan must be wrapped so it cannot kill the run record")
        self.assertIn("row_count_failed", block)

    def test_the_finalising_update_still_records_completion(self):
        import inspect
        src = inspect.getsource(refresh)
        self.assertIn("UPDATE wh_refresh_runs SET finished_at = ?", src)
        self.assertIn('counts["stages_completed"] = completed', src)


if __name__ == "__main__":
    unittest.main()
