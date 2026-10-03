"""Boot seed — Capital IQ Broker Estimates → valuation_consensus store.

Same durability pattern as institutional_knowledge_tables/seed_capital_iq.py:
the checked-in spreadsheet under capital_iq_exports/ is the source of truth;
the derived live.json store is re-derived on boot when empty/wiped.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("valuation_consensus.seed_broker_estimates")

_EXPORTS_DIR = Path(__file__).resolve().parents[2] / "capital_iq_exports"
_FILE = "broker_estimates.xlsx"
_MIN_EXPECTED = 500


def _already_seeded() -> bool:
    try:
        from valuation_consensus.store import load_live

        return int(load_live().get("row_count") or 0) >= _MIN_EXPECTED
    except Exception:
        return False


def seed_if_needed(*, force: bool = False) -> dict[str, Any]:
    """Ingest committed broker_estimates.xlsx when the store looks empty."""
    if not force and _already_seeded():
        return {"ok": True, "skipped": True, "reason": "already_seeded"}

    path = _EXPORTS_DIR / _FILE
    if not path.exists():
        return {
            "ok": False,
            "error": "broker_estimates_missing",
            "path": str(path),
        }

    from valuation_consensus.production import seed_from_path

    try:
        result = seed_from_path(path, actor="broker_estimates_boot_seed")
        logger.info(
            "valuation_consensus seed: ok=%s rows=%s",
            result.get("ok"),
            result.get("row_count"),
        )
        return result
    except Exception as exc:
        logger.exception("valuation_consensus seed failed")
        return {"ok": False, "error": str(exc)[:300]}
