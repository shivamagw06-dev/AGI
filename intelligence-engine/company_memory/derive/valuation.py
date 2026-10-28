"""Valuation History — bands + relative context from P2.2 / HD derived."""

from __future__ import annotations

from typing import Any


def derive_valuation_history(
    entity: str,
    *,
    valuation_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = valuation_pack if isinstance(valuation_pack, dict) else {}
    hist = pack.get("historical") if isinstance(pack.get("historical"), dict) else {}
    rel = pack.get("relative") if isinstance(pack.get("relative"), dict) else {}
    cur = pack.get("current") if isinstance(pack.get("current"), dict) else {}
    peers = pack.get("peer_universe") if isinstance(pack.get("peer_universe"), dict) else {}

    # Soft HD PE series
    hd_pe = {}
    try:
        from knowledge_factory.historical_depth.producers.derived import produce_derived

        derived = produce_derived(entity)
        hd_pe = ((derived.get("metrics") or {}).get("PE") or {}).get("points") or {}
        percentiles = derived.get("pe_percentiles") or {}
    except Exception:
        percentiles = {}

    pe_band = hist.get("pe") if isinstance(hist.get("pe"), dict) else {}
    if not pe_band and hd_pe:
        vals = [float(v) for v in hd_pe.values() if isinstance(v, (int, float))]
        if len(vals) >= 3:
            s = sorted(vals)
            n = len(s)
            med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
            pe_band = {
                "window": "history",
                "median": round(med, 2),
                "high": round(max(s), 2),
                "low": round(min(s), 2),
                "current": cur.get("pe"),
                "percentile": percentiles.get(list(hd_pe.keys())[-1]) if hd_pe else None,
                "observations": n,
                "source": "historical_depth.derived",
            }

    return {
        "available": bool(pe_band or cur.get("pe") is not None or peers.get("resolved")),
        "entity": entity,
        "current": {
            "pe": cur.get("pe"),
            "pb": cur.get("pb"),
            "ev_ebitda": cur.get("ev_ebitda"),
            "peg": cur.get("peg"),
            "forward_pe": cur.get("forward_pe"),
        },
        "historical_bands": {
            "pe": pe_band,
            "pb": hist.get("pb") if isinstance(hist.get("pb"), dict) else None,
            "ev_ebitda": hist.get("ev_ebitda") if isinstance(hist.get("ev_ebitda"), dict) else None,
        },
        "relative": {
            "pe": rel.get("pe"),
            "pb": rel.get("pb"),
            "ev_ebitda": rel.get("ev_ebitda"),
        },
        "peers": {
            "primary": peers.get("primary_peers") or [],
            "sector": peers.get("sector"),
            "industry": peers.get("industry"),
            "source": peers.get("source"),
        },
        "stance": pack.get("stance"),
        "observations": pack.get("observations") or [],
        "lineage": pack.get("lineage") or [{"source": "valuation_intelligence"}],
    }
