"""Institutional document / section / transcript temporal filter."""

from __future__ import annotations

from typing import Any

from temporal_integrity.object_filter.filter import filter_objects
from temporal_integrity.validator.dates import text_has_future_year


def filter_documents(documents: list[dict[str, Any]] | None, *, as_of: str | None) -> dict[str, Any]:
    docs = list(documents or [])
    if not as_of:
        return {
            "documents": docs,
            "n_checked": 0,
            "n_rejected": 0,
            "rejected": [],
            "as_of": as_of,
            "fabricated": False,
        }

    res = filter_objects(docs, as_of=as_of, source="document", reject_unknown=False)
    kept_docs = []
    rejected = list(res["rejected"])
    n_checked = res["n_checked"]

    for doc in res["kept"]:
        d = dict(doc)
        for key in ("paragraphs", "sections", "chunks", "transcript_chunks"):
            parts = d.get(key)
            if not isinstance(parts, list):
                continue
            kept_parts = []
            for p in parts:
                n_checked += 1
                if isinstance(p, dict):
                    pres = filter_objects([p], as_of=as_of, source=f"document:{key}", reject_unknown=False)
                    if pres["n_rejected"]:
                        rejected.extend(pres["rejected"])
                    else:
                        text = p.get("text") or p.get("content") or ""
                        if text_has_future_year(text, as_of):
                            rejected.append(
                                {
                                    "object": p,
                                    "contract": {
                                        "object_id": p.get("id") or key,
                                        "temporal_status": "rejected",
                                        "reason_if_rejected": "surface_future_year",
                                    },
                                }
                            )
                        else:
                            kept_parts.append(p)
                else:
                    if text_has_future_year(p, as_of):
                        rejected.append(
                            {
                                "object": {"text": p},
                                "contract": {
                                    "object_id": key,
                                    "temporal_status": "rejected",
                                    "reason_if_rejected": "surface_future_year",
                                },
                            }
                        )
                    else:
                        kept_parts.append(p)
            d[key] = kept_parts
        kept_docs.append(d)

    return {
        "documents": kept_docs,
        "n_checked": n_checked,
        "n_rejected": len(rejected),
        "rejected": rejected,
        "as_of": as_of,
        "fabricated": False,
    }
