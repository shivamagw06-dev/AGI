"""One-time Capital IQ screener seed — makes bulk-uploaded company reference
data durable across restarts/redeploys, without a persistent disk.

Render's filesystem is ephemeral unless a persistent disk is attached (see
app/kip/persist.py's `enforce_persistent_kip_or_raise` warning) — a
JSON-per-ticker IKT store written via a one-time API upload would be wiped
on the next deploy. Committing the *source* Capital IQ exports to the repo
(capital_iq_exports/) and re-deriving the IKT facts from them on every boot
makes the data durable by construction: the checked-in spreadsheet, not the
derived JSON store, is the source of truth — exactly the same pattern
`trading_universe` uses for NIFTYstocks.csv.

Idempotent and cheap to call on every boot: skips re-ingesting once the
store already has the expected company count, and always runs off the
critical path (see the background-thread call site in app/main.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("institutional_knowledge_tables.seed_capital_iq")

_EXPORTS_DIR = Path(__file__).resolve().parents[2] / "capital_iq_exports"
# Header lives only on the first file; 2035 + 7000 are headerless
# continuation batches of the same Capital IQ screener export (same 40
# columns, same column order). Combined they cover the full Indian public
# company universe (~7,800+ unique resolved tickers).
_FILES = ("capiq_export_460.xlsx", "capiq_export_2035.xlsx", "capiq_export_7000.xlsx")
# Below this company count, treat the store as not-yet-seeded (real ingests
# resolve ~100% of the ~7,800+ unique companies across all three files; a
# much lower count means a fresh/wiped disk, not a partial prior run worth
# preserving). Threshold sits between the old 2-file corpus (~2,027) and the
# full 3-file corpus so a deploy that only has the first two files still
# re-seeds once the third lands.
_MIN_EXPECTED_COMPANIES = 5000


def _already_seeded() -> bool:
    from institutional_knowledge_tables.store import list_companies

    try:
        return len(list_companies()) >= _MIN_EXPECTED_COMPANIES
    except Exception:
        return False


def seed_if_needed(*, force: bool = False) -> dict[str, Any]:
    """Ingests the committed Capital IQ exports into IKT if the store looks
    unseeded (or `force=True`). Safe to call on every boot."""

    if not force and _already_seeded():
        return {"ok": True, "skipped": True, "reason": "already_seeded"}

    from institutional_knowledge_tables.bulk_sheet import ingest_company_sheet, read_sheet_rows

    if not _EXPORTS_DIR.exists():
        return {"ok": False, "error": "capital_iq_exports_dir_missing", "path": str(_EXPORTS_DIR)}

    results: list[dict[str, Any]] = []
    column_names: list[str] | None = None
    # Shared across all three CapIQ chunks so a company that appears as
    # BSE:500191 in file 1 and NSEI:HMT in file 3 collapses to one IKT key
    # (preferring the NSE symbol) instead of splitting facts across two.
    name_canonical: dict[str, str] = {}
    for filename in _FILES:
        path = _EXPORTS_DIR / filename
        if not path.exists():
            results.append({"ok": False, "filename": filename, "error": "file_missing"})
            continue
        content = path.read_bytes()
        try:
            if column_names is None:
                df = read_sheet_rows(content, filename)
                column_names = list(df.columns)
                out = ingest_company_sheet(
                    content,
                    filename,
                    source_label=f"capital_iq_exports/{filename}",
                    name_canonical=name_canonical,
                )
            else:
                out = ingest_company_sheet(
                    content,
                    filename,
                    source_label=f"capital_iq_exports/{filename}",
                    column_names=column_names,
                    name_canonical=name_canonical,
                )
        except Exception as exc:  # pragma: no cover - defensive
            out = {"ok": False, "filename": filename, "error": str(exc)[:300]}
        results.append({"filename": filename, **out})

    try:
        from app.ui.company_router import invalidate_index_cache

        invalidate_index_cache()
    except Exception:
        pass

    total_resolved = sum(r.get("resolved_count", 0) for r in results)
    total_unresolved = sum(r.get("unresolved_count", 0) for r in results)
    ok = all(r.get("ok") for r in results)
    return {
        "ok": ok,
        "skipped": False,
        "files": [r.get("filename") for r in results],
        "total_resolved": total_resolved,
        "total_unresolved": total_unresolved,
        "results": results,
    }
