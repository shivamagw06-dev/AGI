"""Evidence pack temporal filter."""

from __future__ import annotations

from typing import Any

from temporal_integrity.object_filter.filter import filter_objects
from temporal_integrity.validator.dates import text_has_future_year


def filter_evidence(evidence: dict[str, Any] | None, *, as_of: str | None) -> dict[str, Any]:
    ev = dict(evidence or {})
    if not as_of:
        return {
            "evidence": ev,
            "n_checked": 0,
            "n_rejected": 0,
            "rejected": [],
            "as_of": as_of,
            "fabricated": False,
        }

    rejected: list[dict[str, Any]] = []
    n_checked = 0

    for key in ("items", "packs", "ranked", "documents", "snippets"):
        rows = ev.get(key)
        if not isinstance(rows, list):
            continue
        # list of dicts or strings
        dict_rows = [r for r in rows if isinstance(r, dict)]
        str_rows = [r for r in rows if isinstance(r, str)]
        if dict_rows:
            res = filter_objects(dict_rows, as_of=as_of, source=f"evidence:{key}", reject_unknown=False)
            n_checked += res["n_checked"]
            rejected.extend(res["rejected"])
            kept = res["kept"] + [r for r in str_rows if not text_has_future_year(r, as_of)]
            for r in str_rows:
                n_checked += 1
                if text_has_future_year(r, as_of):
                    rejected.append(
                        {
                            "object": {"text": r},
                            "contract": {
                                "object_id": f"evidence:{key}",
                                "temporal_status": "rejected",
                                "reason_if_rejected": "surface_future_year",
                            },
                        }
                    )
            ev[key] = kept
        elif str_rows:
            kept_s = []
            for r in str_rows:
                n_checked += 1
                if text_has_future_year(r, as_of):
                    rejected.append(
                        {
                            "object": {"text": r},
                            "contract": {
                                "object_id": f"evidence:{key}",
                                "temporal_status": "rejected",
                                "reason_if_rejected": "surface_future_year",
                            },
                        }
                    )
                else:
                    kept_s.append(r)
            ev[key] = kept_s

    ev["temporal_integrity"] = {
        "guard": "evidence_filter",
        "as_of": as_of,
        "n_rejected": len(rejected),
    }
    return {
        "evidence": ev,
        "n_checked": n_checked,
        "n_rejected": len(rejected),
        "rejected": rejected,
        "as_of": as_of,
        "fabricated": False,
    }
