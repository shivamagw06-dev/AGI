"""Ownership Intelligence trends — Decision Engine cares about direction more than a snapshot."""

from __future__ import annotations

from typing import Any


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _trend(series: list[float | None], *, min_n: int = 3) -> dict[str, Any]:
    clean = [v for v in series if v is not None]
    if len(clean) < min_n:
        if len(clean) >= 2:
            delta = round(clean[-1] - clean[0], 2)
            direction = "rising" if delta > 0.15 else "falling" if delta < -0.15 else "stable"
            return {"direction": direction, "quarters": len(clean), "delta_pp": delta, "latest": clean[-1]}
        return {"direction": "unknown", "quarters": len(clean), "delta_pp": None, "latest": clean[-1] if clean else None}
    # Last N consecutive direction
    window = clean[-8:]
    deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
    up = sum(1 for d in deltas if d > 0.05)
    down = sum(1 for d in deltas if d < -0.05)
    if up >= max(3, len(deltas) - 1) and down == 0:
        direction = "rising"
        streak = up
    elif down >= max(3, len(deltas) - 1) and up == 0:
        direction = "falling"
        streak = down
    elif abs(window[-1] - window[0]) <= 0.5:
        direction = "stable"
        streak = len(window)
    else:
        direction = "mixed"
        streak = len(window)
    return {
        "direction": direction,
        "quarters": len(clean),
        "streak_quarters": streak,
        "delta_pp": round(window[-1] - window[0], 2),
        "latest": window[-1],
        "series_tail": [round(x, 2) for x in window[-6:]],
    }


def derive_ownership_history(
    entity: str,
    *,
    ownership_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = ownership_pack if isinstance(ownership_pack, dict) else {}
    history = list(pack.get("quarter_history") or [])
    if not history:
        try:
            from knowledge_factory.historical_depth import store as hd_store

            series = hd_store.get_series("shareholding", entity) or {}
            for r in series.get("records") or []:
                p = r.get("payload") or {}
                history.append(
                    {
                        "period_end": r.get("period_end"),
                        "quarter_label": r.get("period"),
                        "promoter": p.get("promoter"),
                        "fii": p.get("fii"),
                        "dii": p.get("dii"),
                        "mutual_funds": p.get("mutual_funds"),
                        "insurance": p.get("insurance"),
                        "promoter_pledge_pct": p.get("pledged"),
                    }
                )
        except Exception:
            pass

    # Oldest → newest
    def _key(r: dict[str, Any]) -> str:
        return str(r.get("period_end") or r.get("quarter_label") or "")

    ordered = sorted([r for r in history if isinstance(r, dict)], key=_key)

    def col(name: str) -> list[float | None]:
        return [_f(r.get(name)) for r in ordered]

    promoter_t = _trend(col("promoter"))
    fii_t = _trend(col("fii"))
    dii_t = _trend(col("dii"))
    mf_t = _trend(col("mutual_funds"))
    ins_t = _trend(col("insurance"))
    pledge_t = _trend(col("promoter_pledge_pct"), min_n=2)

    latest = ordered[-1] if ordered else {}
    narrative = []
    if promoter_t.get("latest") is not None:
        narrative.append(
            f"Promoter {promoter_t['latest']}% — {promoter_t['direction']} over {promoter_t.get('quarters')} quarters."
        )
    if fii_t.get("direction") in {"rising", "falling"}:
        narrative.append(f"FII {fii_t['direction']} ({fii_t.get('delta_pp')} pp).")
    if mf_t.get("direction") in {"rising", "falling"}:
        narrative.append(f"Mutual funds {mf_t['direction']} ({mf_t.get('delta_pp')} pp).")
    if ins_t.get("direction") == "stable" and ins_t.get("latest") is not None:
        narrative.append(f"Insurance steady near {ins_t['latest']}%.")
    if pledge_t.get("latest") not in (None, 0, 0.0):
        narrative.append(f"Promoter pledge {pledge_t['latest']}%.")

    return {
        "available": bool(ordered) or pack.get("ok") is True,
        "entity": entity,
        "source": pack.get("source") or "ownership_intelligence",
        "as_of_quarter": pack.get("as_of_quarter") or latest.get("period_end"),
        "latest": {
            "promoter": _f(pack.get("promoter") if pack.get("promoter") is not None else latest.get("promoter")),
            "fii": _f(pack.get("fii") if pack.get("fii") is not None else latest.get("fii")),
            "dii": _f(pack.get("dii") if pack.get("dii") is not None else latest.get("dii")),
            "mutual_funds": _f(
                pack.get("mutual_funds") if pack.get("mutual_funds") is not None else latest.get("mutual_funds")
            ),
            "insurance": _f(pack.get("insurance") if pack.get("insurance") is not None else latest.get("insurance")),
            "pledge": _f(
                pack.get("promoter_pledge_pct")
                if pack.get("promoter_pledge_pct") is not None
                else latest.get("promoter_pledge_pct")
            ),
        },
        "trends": {
            "promoter": promoter_t,
            "fii": fii_t,
            "dii": dii_t,
            "mutual_funds": mf_t,
            "insurance": ins_t,
            "pledge": pledge_t,
        },
        "observations": narrative,
        "quarters_n": len(ordered),
        "lineage": [{"source": "ownership_intelligence", "n": len(ordered)}],
    }
