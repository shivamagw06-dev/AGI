"""Institutional analog / memory temporal filter — no future period labels."""

from __future__ import annotations

from typing import Any

from temporal_integrity.object_filter.filter import filter_objects
from temporal_integrity.validator.contract import build_contract
from temporal_integrity.validator.dates import text_has_future_year


def _memory_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("memories", "scored", "top_memories", "results"):
        rows = pack.get(key)
        if isinstance(rows, list) and rows:
            return [r if isinstance(r, dict) else {"raw": r} for r in rows]
    return []


def filter_analogs(institutional_memory: dict[str, Any] | None, *, as_of: str | None) -> dict[str, Any]:
    im = dict(institutional_memory or {})
    if not as_of:
        return {
            "institutional_memory": im,
            "n_checked": 0,
            "n_rejected": 0,
            "rejected": [],
            "as_of": as_of,
            "fabricated": False,
        }

    memories = _memory_rows(im)
    # Normalize memory dicts (scored wrappers may nest memory)
    normalized: list[dict[str, Any]] = []
    for m in memories:
        if isinstance(m.get("memory"), dict):
            base = dict(m["memory"])
            base["_score_wrap"] = {k: v for k, v in m.items() if k != "memory"}
            normalized.append(base)
        else:
            normalized.append(m)

    res = filter_objects(normalized, as_of=as_of, source="institutional_analog", reject_unknown=False)

    # Rebuild scored list if present
    kept = res["kept"]
    kept_ids = {str(m.get("memory_id") or m.get("id") or "") for m in kept}

    if "scored" in im and isinstance(im["scored"], list):
        new_scored = []
        for row in im["scored"]:
            mem = row.get("memory") if isinstance(row, dict) else None
            mid = ""
            if isinstance(mem, dict):
                mid = str(mem.get("memory_id") or mem.get("id") or "")
                c = build_contract(mem, as_of=as_of, source="institutional_analog")
                if c.get("temporal_status") != "allowed":
                    continue
            elif isinstance(row, dict):
                mid = str(row.get("memory_id") or row.get("id") or "")
                if mid and mid not in kept_ids:
                    continue
            new_scored.append(row)
        im["scored"] = new_scored
        im["scored_count"] = len(new_scored)

    if "memories" in im:
        im["memories"] = kept
    if "top_memories" in im:
        im["top_memories"] = kept
    im["top_memory_ids"] = [
        str(m.get("memory_id") or m.get("id"))
        for m in kept
        if m.get("memory_id") or m.get("id")
    ][:10]
    im["have_we_seen_this_before"] = bool(im["top_memory_ids"]) or bool(kept)

    # Surface bullets — exclude any with future years (reject, do not rewrite facts)
    bullets = list(im.get("surface_bullets") or [])
    kept_bullets = []
    bullet_rejected = []
    for b in bullets:
        if text_has_future_year(b, as_of):
            bullet_rejected.append(
                {
                    "object": {"text": b},
                    "contract": {
                        "object_id": "imai_surface_bullet",
                        "temporal_status": "rejected",
                        "reason_if_rejected": "surface_future_year",
                    },
                }
            )
        else:
            kept_bullets.append(b)
    im["surface_bullets"] = kept_bullets
    im["temporal_integrity"] = {
        "guard": "analog_filter",
        "as_of": as_of,
        "n_memories_rejected": res["n_rejected"],
        "n_bullets_rejected": len(bullet_rejected),
    }

    rejected = list(res["rejected"]) + bullet_rejected
    return {
        "institutional_memory": im,
        "n_checked": res["n_checked"] + len(bullets),
        "n_rejected": len(rejected),
        "rejected": rejected,
        "as_of": as_of,
        "fabricated": False,
    }
