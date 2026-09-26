"""Configurable throughput and priority for ICF (no hard-coded daily crawl target)."""

from __future__ import annotations

import os
from typing import Any

from institutional_coverage_factory.schema import DEFAULT_CONFIG, PriorityTier


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["enabled"] = os.environ.get("AGI_ICF_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    cfg["max_companies_per_day"] = _env_int(
        "AGI_ICF_MAX_COMPANIES_PER_DAY", int(cfg["max_companies_per_day"])
    )
    cfg["max_parallel_collectors"] = _env_int(
        "AGI_ICF_MAX_PARALLEL_COLLECTORS", int(cfg["max_parallel_collectors"])
    )
    tick = _env_int(
        "AGI_ICF_TICK_INTERVAL_MINUTES", int(cfg["tick_interval_minutes"])
    )
    cfg["tick_interval_minutes"] = tick
    cfg["planner_interval_minutes"] = tick
    cfg["companies_per_tick"] = _env_int(
        "AGI_ICF_COMPANIES_PER_TICK", int(cfg["companies_per_tick"])
    )
    cfg["coverage_threshold"] = _env_float(
        "AGI_ICF_COVERAGE_THRESHOLD", float(cfg["coverage_threshold"])
    )
    cfg["institutional_coverage_threshold"] = _env_float(
        "AGI_ICF_ICC_THRESHOLD", float(cfg["institutional_coverage_threshold"])
    )
    ready = _env_float(
        "AGI_ICF_RESEARCH_READINESS_THRESHOLD",
        float(cfg["research_readiness_threshold"]),
    )
    cfg["research_readiness_threshold"] = ready
    cfg["research_ready_threshold"] = ready
    cfg["knowledge_confidence_threshold"] = _env_float(
        "AGI_ICF_KNOWLEDGE_CONFIDENCE_THRESHOLD",
        float(cfg["knowledge_confidence_threshold"]),
    )
    retry = dict(cfg["retry_policy"])
    retry["max_attempts"] = _env_int(
        "AGI_ICF_RETRY_MAX_ATTEMPTS", int(retry["max_attempts"])
    )
    cfg["retry_policy"] = retry
    raw_priority = os.environ.get("AGI_ICF_PRIORITY_ORDER", "").strip()
    if raw_priority:
        tiers = []
        for part in raw_priority.split(","):
            key = part.strip().upper()
            try:
                tiers.append(PriorityTier(key).value)
            except ValueError:
                continue
        if tiers:
            cfg["priority"] = tiers
    return cfg


def as_yaml_dict() -> dict[str, Any]:
    """Surface matching the recommended coverage_factory YAML shape."""
    cfg = load_config()
    return {
        "coverage_factory": {
            "enabled": cfg["enabled"],
            "max_companies_per_day": cfg["max_companies_per_day"],
            "max_parallel_collectors": cfg["max_parallel_collectors"],
            "priority": list(cfg["priority"]),
            "retry_policy": {"max_attempts": cfg["retry_policy"]["max_attempts"]},
            "coverage_threshold": cfg["coverage_threshold"],
            "institutional_coverage_threshold": cfg["institutional_coverage_threshold"],
        }
    }
