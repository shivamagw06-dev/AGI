"""Parser Replay Engine — re-parse historical evidence; never mutate raw or old drafts."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.quality.diff import diff_drafts
from financial_statements_engine.parsing.quality.manifest import load_manifest
from financial_statements_engine.raw_evidence import read_raw_bytes
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def replay(
    *,
    ticker: str,
    evidence_id: str,
    prior_manifest_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay parse for evidence. Creates new draft + manifest with replay_of set."""
    from financial_statements_engine.parsing.pipeline import parse_document

    data = read_raw_bytes(ticker, evidence_id)
    if data is None:
        return {"ok": False, "error": "raw_evidence_not_found", "evidence_id": evidence_id}

    prior = None
    if prior_manifest_id:
        prior_manifest = load_manifest(ticker, prior_manifest_id)
        if prior_manifest and prior_manifest.get("draft_id"):
            draft_path = (
                ensure_dirs()
                / "parsing"
                / "drafts"
                / ticker.upper()
                / f"{str(prior_manifest['draft_id']).replace(':', '_')}.json"
            )
            if draft_path.exists():
                import json

                prior = json.loads(draft_path.read_text(encoding="utf-8"))

    result = parse_document(
        ticker=ticker,
        data=data,
        evidence_id=evidence_id,
        meta={**(meta or {}), "replay_of": prior_manifest_id},
    )
    diff = diff_drafts(prior, result) if result.get("ok") else None
    report = {
        "ok": bool(result.get("ok")),
        "ticker": ticker.upper().strip(),
        "evidence_id": evidence_id,
        "prior_manifest_id": prior_manifest_id,
        "new_manifest_id": (result.get("manifest") or {}).get("manifest_id"),
        "new_draft_id": result.get("draft_id"),
        "diff": diff,
        "raw_evidence_modified": False,
        "historical_drafts_overwritten": False,
        "as_of": now_iso(),
        "layer": "replay_engine",
    }
    path = ensure_dirs() / "parsing" / "replays" / ticker.upper() / f"{report.get('new_manifest_id', 'fail').replace(':', '_')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, report)
    report["report_path"] = str(path)
    return report
