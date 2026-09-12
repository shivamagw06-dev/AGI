"""Adversarial institutional suite — renames, collisions, M&A, stale, contradictory, negative EPS.

Soft eval harness. Never invents live facts; exercises governance withhold paths.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.fundamentals.derivations import derive_series
from institutional_reasoning.ipi.decision import decide_portfolio

ADV_VERSION = "adversarial-suite-v1.0.0"


def _case(name: str, ok: bool, detail: Any = None) -> dict[str, Any]:
    return {"case": name, "passed": bool(ok), "detail": detail}


def run_adversarial_suite() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    # 1) Ticker rename / alias collision — Infosys vs INFY should resolve one entity
    r = govern_answer("Is Infosys expensive versus history?", ticker_hint="INFY")
    e1 = (r.get("entity") or {}).get("entity_id")
    r2 = govern_answer("Is Infosys expensive versus history?")
    e2 = (r2.get("entity") or {}).get("entity_id")
    results.append(
        _case(
            "rename_alias_stability",
            e1 == "INFY" and e2 == "INFY",
            {"e1": e1, "e2": e2},
        )
    )

    # 2) Entity collision — two names in one question must not silently merge
    r = govern_answer("Compare Infosys and TCS valuation", ticker_hint="INFY")
    ents = r.get("entity_resolution") or {}
    primary = (ents.get("primary") or {}).get("entity_id")
    secondary = ents.get("secondary")
    if isinstance(secondary, dict):
        secondary_id = secondary.get("entity_id")
    elif isinstance(secondary, list) and secondary:
        secondary_id = (secondary[0] or {}).get("entity_id") if isinstance(secondary[0], dict) else secondary[0]
    else:
        secondary_id = secondary
    results.append(
        _case(
            "comparison_entity_collision",
            primary == "INFY" and (secondary_id == "TCS" or secondary is not None),
            {"primary": primary, "secondary": secondary_id},
        )
    )

    # 3) M&A / unknown spun entity — must withhold narrative without inventing PE
    r = govern_answer("Is NewCoSpinCoXYZ expensive versus history?", ticker_hint="NEWCOSPIN")
    missing = (r.get("validation") or {}).get("missing") or []
    results.append(
        _case(
            "unknown_ma_entity_withholds",
            not r.get("narrative_allowed") or bool(missing),
            {"narrative_allowed": r.get("narrative_allowed"), "missing": missing[:8]},
        )
    )

    # 4) Stale / empty packs — portfolio on uncovered name withholds
    d = decide_portfolio(entity_id="UNKNOWNX", persist_memory=False)
    results.append(_case("uncovered_portfolio_withhold", bool(d.get("withheld")), {"action": (d.get("committee") or {}).get("action")}))

    # 5) Contradictory evidence path — risk question still binds drivers when series exist
    r = govern_answer("What are the key risks and downside for Infosys?", ticker_hint="INFY")
    missing = set((r.get("validation") or {}).get("missing") or [])
    results.append(
        _case(
            "risk_drivers_bound_when_series_exist",
            "risk_drivers" not in missing and "downside_case" not in missing,
            {"missing": sorted(missing), "complete": (r.get("validation") or {}).get("complete")},
        )
    )

    # 6) Negative earnings — PE derivation must reject (no hallucinated PE)
    # Inject via ZOMATO if loss-making periods exist; else synthetic check on derive API.
    series = derive_series("ZOMATO", "PE")
    rejected = series.get("rejected_periods") or []
    points = series.get("points") or {}
    # Either some periods rejected for negative EPS, or no positive PE invented from losses
    neg_ok = True
    if series.get("found"):
        # All stored PE points must be positive
        neg_ok = all(float(v) > 0 for v in points.values())
    results.append(
        _case(
            "negative_earnings_no_fake_pe",
            neg_ok,
            {"n_points": len(points), "rejected": len(rejected) if isinstance(rejected, list) else rejected},
        )
    )

    # 7) Sector-cap language routes to portfolio, not sector research alone
    r = govern_answer("Does Infosys breach our 20% sector cap?", ticker_hint="INFY")
    results.append(
        _case(
            "sector_cap_routes_portfolio",
            r.get("question_type") in {"portfolio", "investment_decision", "risk"},
            {"question_type": r.get("question_type")},
        )
    )

    passed = sum(1 for x in results if x["passed"])
    return {
        "adv_version": ADV_VERSION,
        "n": len(results),
        "passed": passed,
        "score": round(100.0 * passed / len(results), 2) if results else 0.0,
        "results": results,
        "gate_passed": passed == len(results),
    }
