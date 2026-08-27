"""PCE-01 reusable policy profiles / mandates."""

from __future__ import annotations

from typing import Optional

from institutional_policy.models import MandateProfile, PolicyConstraint
from institutional_policy.schema import DEFAULT_POLICY_PROFILE


def _c(
    cid: str,
    category: str,
    name: str,
    operator: str,
    limit: float,
    *,
    unit: str = "weight",
    description: str = "",
) -> PolicyConstraint:
    return PolicyConstraint(
        constraint_id=cid,
        category=category,
        name=name,
        operator=operator,
        limit=limit,
        unit=unit,
        description=description or f"{operator} {name} = {limit}",
    )


def _family_office() -> MandateProfile:
    return MandateProfile(
        profile_id="family_office",
        label="Family Office",
        description="Concentrated but governed family-office equity book",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.25),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.80),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.60),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.40),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.30),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.05),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.25),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 4, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.22, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.70),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.15),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 5.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 15.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 1.30, unit="beta"),
        ),
    )


def _balanced() -> MandateProfile:
    return MandateProfile(
        profile_id="balanced",
        label="Balanced",
        description="Balanced multi-sector mandate",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.20),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.70),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.40),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.35),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.25),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.08),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.20),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 8, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.15, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.45),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.10),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 3.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 12.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 1.15, unit="beta"),
        ),
    )


def _conservative() -> MandateProfile:
    return MandateProfile(
        profile_id="conservative",
        label="Conservative",
        description="Capital-preservation oriented mandate",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.15),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.55),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.30),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.25),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.15),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.15),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.40),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 12, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.10, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.35),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.05),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 2.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 8.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 0.95, unit="beta"),
        ),
    )


def _growth() -> MandateProfile:
    return MandateProfile(
        profile_id="growth",
        label="Growth",
        description="Growth-oriented mandate with looser concentration",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.30),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.85),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.50),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.50),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.35),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.03),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.15),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 5, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.28, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.75),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.20),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 7.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 20.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 1.40, unit="beta"),
        ),
    )


def _pms() -> MandateProfile:
    return MandateProfile(
        profile_id="pms",
        label="PMS",
        description="India PMS-style concentrated equity mandate",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.25),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.75),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.55),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.40),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.30),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.05),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.20),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 6, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.20, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.60),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.12),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 4.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 14.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 1.25, unit="beta"),
        ),
    )


def _mutual_fund() -> MandateProfile:
    return MandateProfile(
        profile_id="mutual_fund",
        label="Mutual Fund",
        description="Diversified mutual-fund style constraints",
        constraints=(
            _c("pos_max_holding", "position", "Maximum Holding", "max", 0.10),
            _c("pos_max_top5", "position", "Maximum Top-5 Weight", "max", 0.40),
            _c("sec_max_financials", "sector", "Maximum Financials", "max", 0.35),
            _c("sec_max_it", "sector", "Maximum IT", "max", 0.30),
            _c("sec_max_energy", "sector", "Maximum Energy", "max", 0.20),
            _c("cash_min", "cash", "Minimum Cash", "min", 0.02),
            _c("cash_max", "cash", "Maximum Cash", "max", 0.15),
            _c("div_min_holdings", "diversification", "Minimum Holdings", "min", 25, unit="count"),
            _c("div_max_hhi", "diversification", "Maximum HHI", "max", 0.08, unit="score"),
            _c("div_max_sector", "diversification", "Maximum Concentration", "max", 0.35),
            _c("liq_max_illiquid", "liquidity", "Maximum Illiquid Exposure", "max", 0.05),
            _c("liq_max_exit_days", "liquidity", "Minimum Exit Capacity", "max", 2.0, unit="days"),
            _c("risk_max_stress", "risk", "Maximum Stress Loss", "max", 10.0, unit="pct"),
            _c("risk_max_beta", "risk", "Maximum Beta", "max", 1.10, unit="beta"),
        ),
    )


_PROFILES: dict[str, MandateProfile] = {
    "family_office": _family_office(),
    "balanced": _balanced(),
    "conservative": _conservative(),
    "growth": _growth(),
    "pms": _pms(),
    "mutual_fund": _mutual_fund(),
}


def list_profiles() -> list[dict]:
    return [
        {"profile_id": p.profile_id, "label": p.label, "description": p.description}
        for p in _PROFILES.values()
    ]


def get_mandate(profile_id: Optional[str] = None) -> MandateProfile:
    key = (profile_id or DEFAULT_POLICY_PROFILE).strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "family": "family_office",
        "fo": "family_office",
        "mf": "mutual_fund",
        "mutualfund": "mutual_fund",
        "default": DEFAULT_POLICY_PROFILE,
    }
    key = aliases.get(key, key)
    if key == "custom":
        # Custom defaults to family office limits (override via future payload)
        return _family_office()
    if key not in _PROFILES:
        return _PROFILES[DEFAULT_POLICY_PROFILE]
    return _PROFILES[key]
