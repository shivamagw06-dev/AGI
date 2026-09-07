"""Soft pull from Causal Intelligence Graph — no CIG redesign."""

from __future__ import annotations

from typing import Any


def soft_causal_transmission(ticker: str) -> dict[str, Any]:
    try:
        from causal_graph.production import soft_slice_for_analyst

        slice_ = (soft_slice_for_analyst(ticker, analyst="committee") or {}).get("causal_intelligence") or {}
        if not slice_:
            return {"enabled": False}
        return {
            "enabled": bool(slice_.get("enabled", True)),
            "confidence": slice_.get("confidence"),
            "upstream_drivers": slice_.get("upstream_drivers"),
            "why": slice_.get("why"),
            "propagation_map": slice_.get("propagation_map"),
            "portfolio_impact": slice_.get("portfolio_impact"),
        }
    except Exception as exc:
        return {"enabled": False, "soft_error": str(exc)[:120]}
