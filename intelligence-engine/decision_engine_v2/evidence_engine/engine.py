"""Evidence summary across soft layer inputs."""

from __future__ import annotations

from typing import Any


def summarise_evidence(inputs: dict[str, Any]) -> dict[str, Any]:
    layers = inputs.get("layers") or {}
    items: list[dict[str, Any]] = []
    mapping = [
        ("filing_intelligence", "FIL", "found"),
        ("filing_diff", "FDI", "enabled"),
        ("management_intelligence", "MII", "confidence"),
        ("accounting_intelligence", "ACI", "confidence"),
        ("evidence_intelligence", "EIL", "enabled"),
        ("peer_intelligence", "PIL", "enabled"),
        ("causal_intelligence", "CIG", "confidence"),
        ("knowledge_graph", "IKG", "relationship_count"),
        ("forecast_intelligence", "FIE", "most_likely"),
        ("institutional_memory", "ILM", "lesson_count"),
        ("simulation_lab", "SSL", "expected_return"),
        ("portfolio_intelligence", "PIO", "portfolio_quality"),
    ]
    for key, label, field in mapping:
        layer = layers.get(key) or {}
        val = layer.get(field)
        items.append(
            {
                "layer": label,
                "key": key,
                "signal": val,
                "present": bool(layer) and layer.get("enabled", True) is not False,
                "summary": layer.get("summary") or layer.get("cio_brief") or layer.get("executive_forecast"),
            }
        )
    present_n = sum(1 for i in items if i["present"])
    return {
        "items": items,
        "present_count": present_n,
        "coverage": round(present_n / max(1, len(items)), 3),
        "rule": "Evidence summarised from soft layer signals — IDE V2 never invents filings",
    }
