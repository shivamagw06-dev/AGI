"""Legacy FSE-01 warehouse façade for statement packs.

Institutional Validated Financial Facts storage is FSE-06:
`financial_statements_engine.financial_warehouse`.
"""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.store import paths_for
from financial_statements_engine.util import now_iso, write_json_atomic
from financial_statements_engine.validate import apply_validation_status, validate_statement
from financial_statements_engine.versioning import commit_version


def publish_statement(statement: dict[str, Any], *, allow_flagged: bool = True) -> dict[str, Any]:
    """Validate → version → publish (or withhold). Never edits metric values."""
    report = validate_statement(statement)
    gated = apply_validation_status(statement, report)
    versioned = commit_version(gated)

    ticker = str(versioned["ticker"]).upper()
    pub_dir = paths_for(ticker)["published"]
    pub_dir.mkdir(parents=True, exist_ok=True)

    status = versioned.get("publication_status")
    if status == "withheld" or (status == "flagged" and not allow_flagged):
        # Persist withheld artifact separately; do not promote to latest canonical
        write_json_atomic(pub_dir / f"withheld_{versioned['statement_id'].replace(':', '_')}.json", versioned)
        return {
            "ok": False,
            "published": False,
            "publication_status": status,
            "statement": versioned,
            "validation": report,
        }

    # Merge into latest pack index
    latest_path = pub_dir / "latest.json"
    latest: dict[str, Any] = {}
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))

    statements = list(latest.get("statements") or [])
    # Replace same statement_type + period_end pointer (history remains in versions/)
    statements = [
        s
        for s in statements
        if not (
            s.get("statement_type") == versioned.get("statement_type")
            and s.get("period_end") == versioned.get("period_end")
        )
    ]
    statements.append(
        {
            "statement_id": versioned.get("statement_id"),
            "statement_type": versioned.get("statement_type"),
            "period_type": versioned.get("period_type"),
            "period_end": versioned.get("period_end"),
            "version": versioned.get("version"),
            "publication_status": versioned.get("publication_status"),
            "validation_status": versioned.get("validation_status"),
            "path": str(
                paths_for(ticker)["versions"]
                / str(versioned["statement_type"])
                / str(versioned["period_end"])
                / f"v{versioned['version']}.json"
            ),
        }
    )
    pack = {
        "ticker": ticker,
        "engine": "financial_statements_engine",
        "updated_at": now_iso(),
        "statements": statements,
        "issues_recommendations": False,
    }
    write_json_atomic(latest_path, pack)
    write_json_atomic(
        paths_for(ticker)["versions"]
        / str(versioned["statement_type"])
        / str(versioned["period_end"])
        / f"v{versioned['version']}.json",
        versioned,
    )
    return {
        "ok": True,
        "published": True,
        "publication_status": versioned.get("publication_status"),
        "statement": versioned,
        "validation": report,
        "latest": pack,
    }


def get_published(ticker: str) -> dict[str, Any] | None:
    path = paths_for(ticker.upper().strip())["published"] / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_statement_file(path: str) -> dict[str, Any] | None:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
