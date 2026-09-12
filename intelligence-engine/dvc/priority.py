"""Configurable provider priority for DVC."""

from __future__ import annotations

from typing import Any

from dvc.schema import DEFAULT_PROVIDER_PRIORITY


def provider_priority(provider_id: str, *, overrides: dict[str, int] | None = None) -> int:
    table = dict(DEFAULT_PROVIDER_PRIORITY)
    if overrides:
        table.update(overrides)
    try:
        from app.core.config import get_settings

        s = get_settings()
        raw = getattr(s, "dvc_provider_priority", "") or ""
        # Format: "indianapi:2,finnhub:3,yahoo:5"
        for part in str(raw).split(","):
            part = part.strip()
            if ":" in part:
                pid, pr = part.split(":", 1)
                try:
                    table[pid.strip().lower()] = int(pr.strip())
                except ValueError:
                    pass
    except Exception:
        pass
    return int(table.get((provider_id or "").lower(), 100))


def sort_providers(provider_ids: list[str]) -> list[str]:
    return sorted(provider_ids, key=lambda p: (provider_priority(p), p))


def base_confidence(provider_id: str) -> float:
    """Prior confidence before agreement adjustments."""
    pr = provider_priority(provider_id)
    # priority 1 → 0.99, 2 → 0.97, … floor 0.70
    return max(0.70, min(0.99, 1.01 - (pr * 0.02)))
