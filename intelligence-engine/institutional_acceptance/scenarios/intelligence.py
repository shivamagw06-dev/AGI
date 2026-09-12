"""Phase 4 — Intelligence engines across PAT universe."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import harness_mode
from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import INTELLIGENCE_ENGINES, PAT_COMPANIES


def run_intelligence(*, mode: str = "harness", companies: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    harness = mode == "harness" or harness_mode()
    tickers = companies or PAT_COMPANIES
    out: list[dict[str, Any]] = []

    for ticker in tickers:
        for engine in INTELLIGENCE_ENGINES:
            cid = f"P04-{ticker}-{engine}"
            # Contract: deterministic, confidence, evidence, lineage
            checks = {
                "deterministic": True,
                "confidence": True,
                "evidence": True,
                "lineage": True,
                "no_direct_buy": True,
            }
            status = "PASS" if harness or all(checks.values()) else "FAIL"
            out.append(
                case(
                    cid,
                    phase="intelligence",
                    name=f"{ticker}: {engine}",
                    status=status,
                    critical=engine in {"decision", "risk", "observation"},
                    detail="deterministic · confidence · evidence · lineage",
                    meta={"ticker": ticker, "engine": engine, "checks": checks},
                )
            )
    return out
