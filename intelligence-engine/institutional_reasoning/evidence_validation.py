"""Phase 1 — Evidence Validation (execution governance).

Frameworks may only execute on evidence that is:
  * bound to the resolved entity
  * numerically real (not a provider placeholder such as 0 / 0.00 / None)
  * fresh enough for the question
  * complete for the contract's required fields

Returns structured verdicts — never prose.
Architecture v1.0.1 LOCKED — soft helper under institutional_reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

VALIDATION_VERSION = "evidence-validation-v1.0.0"

DEFAULT_MAX_AGE_DAYS = 45
PLACEHOLDER_NUMBERS = {0, 0.0}
PLACEHOLDER_STRINGS = {"", "0", "0.0", "0.00", "0%", "n/a", "na", "none", "null", "-", "--"}

# Canonical evidence field → acceptable source keys inside runtime packs.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "current_pe": ("trailing_pe", "current_pe", "pe", "pe_ratio", "forward_pe"),
    "forward_pe": ("forward_pe", "fwd_pe", "pe_forward"),
    "historical_pe": (
        "historical_pe",
        "pe_history",
        "avg_pe_5y",
        "avg_pe_10y",
        "median_pe_5y",
        "pe_5y_avg",
        "pe_10y_avg",
    ),
    "historical_percentile": (
        "historical_percentile",
        "pe_percentile",
        "valuation_percentile",
        "hist_percentile",
        "percentile",
    ),
    "peer_pe": ("peer_pe", "peer_median_pe", "sector_pe", "index_pe", "peer_group_pe"),
    "ev_ebitda": ("ev_ebitda", "evebitda", "ev_to_ebitda"),
    "price_to_book": ("price_to_book", "pb", "pb_ratio"),
    "peg": ("peg", "peg_ratio"),
    "dividend_yield": ("dividend_yield", "div_yield"),
    "roic": ("roic", "return_on_invested_capital"),
    "roe": ("roe", "return_on_equity"),
    "margins": ("operating_margin", "ebit_margin", "net_margin", "margin"),
    "revenue_quality": ("revenue_growth", "organic_growth", "revenue_quality"),
    "competitive_position": ("market_share", "moat_score", "competitive_position"),
    "cash_conversion": ("cash_conversion", "ocf_to_ebitda", "fcf_conversion"),
    "leverage": ("net_debt_to_ebitda", "debt_equity", "leverage"),
    "earnings_quality": ("earnings_quality", "accruals", "earnings_quality_score"),
    "peer_set": ("peers", "peer_set", "peer_group", "comparables"),
    "comparable_metrics": ("peer_metrics", "comparable_metrics", "peer_table"),
    "peer_percentile": ("peer_percentile", "peer_rank"),
    "downside_case": ("bear", "bear_case", "downside", "downside_case", "stress_case"),
    "expected_return": ("expected_return", "expected_cagr", "irr"),
    "exposure": ("exposure", "weight", "allocation"),
    "risk_contribution": ("risk_contribution", "risk_share", "var_contribution"),
    "macro_series": ("macro_series", "cpi", "gdp", "repo_rate", "policy_rate"),
    "policy_stance": ("policy_stance", "mpc_stance", "fed_stance"),
    "sector_metrics": ("sector_metrics", "sector_pe", "sector_growth"),
    "sector_history": ("sector_history", "sector_pe_history"),
    "risk_drivers": ("risk_drivers", "key_risks", "risks"),
    "driver_assumptions": ("assumptions", "driver_assumptions", "key_assumptions"),
    "scenario_set": ("scenarios", "scenario_set", "bull_base_bear"),
    "academy_concepts": ("concepts", "concept_ids", "academy_concepts"),
    "academy_frameworks": ("frameworks", "framework_ids", "academy_frameworks"),
}


@dataclass
class FieldVerdict:
    field_name: str
    present: bool
    value: Any = None
    source_key: str | None = None
    provenance: str | None = None
    as_of: str | None = None
    entity_id: str | None = None
    rejected_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field_name,
            "present": self.present,
            "value": self.value if isinstance(self.value, (int, float, str)) else None,
            "source_key": self.source_key,
            "provenance": self.provenance,
            "as_of": self.as_of,
            "entity_id": self.entity_id,
            "rejected_reason": self.rejected_reason,
        }


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value in PLACEHOLDER_NUMBERS
    if isinstance(value, str):
        return value.strip().lower() in PLACEHOLDER_STRINGS
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _impossible_value(field_name: str, value: Any) -> str | None:
    """Reject economically impossible metric values for framework execution."""
    if not isinstance(value, (int, float)):
        return None
    pe_fields = {
        "current_pe",
        "forward_pe",
        "historical_pe",
        "peer_pe",
        "historical_percentile",
    }
    if field_name in pe_fields or field_name.endswith("_pe"):
        if field_name == "historical_percentile":
            if value < 0 or value > 100:
                return "impossible_percentile"
        elif value < 0:
            return "impossible_negative_multiple"
    return None


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _entity_of(node: dict[str, Any], parent_entity: str | None) -> str | None:
    for key in ("symbol", "ticker", "entity_id", "company_symbol", "company_id"):
        val = node.get(key)
        if val:
            return str(val).upper().replace("^", "")
    # Pack roots often declare the subject once under "company"/"identity".
    for container in ("company", "identity", "entity"):
        sub = node.get(container)
        if isinstance(sub, dict):
            for key in ("company_symbol", "symbol", "ticker", "entity_id", "company_id"):
                val = sub.get(key)
                if val:
                    return str(val).upper().replace("^", "")
    return parent_entity


def _walk(
    node: Any,
    *,
    entity: str | None = None,
    provenance: str | None = None,
    as_of: str | None = None,
    depth: int = 0,
) -> list[tuple[str, Any, str | None, str | None, str | None]]:
    """Flatten (key, value, entity, provenance, as_of) with inherited context."""
    out: list[tuple[str, Any, str | None, str | None, str | None]] = []
    if depth > 6:
        return out
    if isinstance(node, dict):
        cur_entity = _entity_of(node, entity)
        cur_prov = (
            node.get("provider")
            or node.get("source")
            or node.get("winning_provider")
            or provenance
        )
        cur_as_of = (
            node.get("verified_at")
            or node.get("as_of")
            or node.get("timestamp")
            or node.get("last_updated")
            or as_of
        )
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                out.extend(
                    _walk(
                        v,
                        entity=cur_entity,
                        provenance=str(cur_prov) if cur_prov else None,
                        as_of=str(cur_as_of) if cur_as_of else None,
                        depth=depth + 1,
                    )
                )
                # DVC-shaped nodes: {"field": "trailing_pe", "value": 24.1}
                if isinstance(v, dict) and "value" in v and v.get("field"):
                    out.append(
                        (
                            str(v.get("field")),
                            v.get("value"),
                            _entity_of(v, cur_entity),
                            str(v.get("winning_provider") or v.get("provider") or cur_prov or ""),
                            str(v.get("verified_at") or cur_as_of or ""),
                        )
                    )
                # Scalar lists (e.g. risk_drivers) — bind under the parent key.
                elif (
                    isinstance(v, list)
                    and v
                    and all(not isinstance(x, (dict, list)) for x in v)
                ):
                    out.append(
                        (
                            str(k),
                            v,
                            cur_entity,
                            str(cur_prov) if cur_prov else None,
                            str(cur_as_of) if cur_as_of else None,
                        )
                    )
            else:
                out.append(
                    (
                        str(k),
                        v,
                        cur_entity,
                        str(cur_prov) if cur_prov else None,
                        str(cur_as_of) if cur_as_of else None,
                    )
                )
    elif isinstance(node, list):
        for item in node[:50]:
            out.extend(
                _walk(item, entity=entity, provenance=provenance, as_of=as_of, depth=depth + 1)
            )
    return out


def validate_field(
    field_name: str,
    packs: dict[str, dict[str, Any]],
    *,
    entity_id: str | None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> FieldVerdict:
    aliases = FIELD_ALIASES.get(field_name, (field_name,))
    now = datetime.now(timezone.utc)
    best_reject: str | None = None

    for pack_name, pack in packs.items():
        for key, value, ent, prov, as_of in _walk(pack, provenance=pack_name):
            kl = str(key).lower()
            if not any(a == kl or a in kl for a in aliases):
                continue
            if _is_placeholder(value):
                best_reject = best_reject or "placeholder_value"
                continue
            impossible = _impossible_value(field_name, value)
            if impossible:
                best_reject = best_reject or impossible
                continue
            if entity_id and ent and ent != str(entity_id).upper():
                best_reject = best_reject or f"entity_mismatch:{ent}"
                continue
            if entity_id and not ent:
                best_reject = best_reject or "entity_unbound"
                continue
            ts = _parse_ts(as_of)
            if ts and now - ts > timedelta(days=max_age_days):
                best_reject = best_reject or "stale_evidence"
                continue
            return FieldVerdict(
                field_name=field_name,
                present=True,
                value=value,
                source_key=key,
                provenance=prov or pack_name,
                as_of=as_of,
                entity_id=ent,
            )

    return FieldVerdict(
        field_name=field_name,
        present=False,
        rejected_reason=best_reject or "not_found",
    )


def validate_contract(
    *,
    question_type: str,
    entity_id: str | None,
    packs: dict[str, dict[str, Any]],
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> dict[str, Any]:
    from institutional_reasoning.evidence_contracts import contract_for

    contract = contract_for(question_type)
    verdicts = [
        validate_field(f, packs, entity_id=entity_id, max_age_days=max_age_days)
        for f in contract.required
    ]
    optional_verdicts = [
        validate_field(f, packs, entity_id=entity_id, max_age_days=max_age_days)
        for f in contract.optional
    ]
    observed = [v.field_name for v in verdicts if v.present]
    missing = [v.field_name for v in verdicts if not v.present]
    rejected = {
        v.field_name: v.rejected_reason
        for v in verdicts
        if not v.present and v.rejected_reason and v.rejected_reason != "not_found"
    }
    coverage = (len(observed) / len(contract.required)) if contract.required else 1.0
    return {
        "version": VALIDATION_VERSION,
        "question_type": contract.question_type,
        "contract_version": contract.version,
        "entity_id": entity_id,
        "required": list(contract.required),
        "observed": observed,
        "missing": missing,
        "rejected": rejected,
        "coverage": round(coverage, 4),
        "complete": not missing,
        "optional_present": [v.field_name for v in optional_verdicts if v.present],
        "field_verdicts": [v.to_dict() for v in verdicts],
        "provenance": sorted(
            {v.provenance for v in verdicts if v.present and v.provenance}
        ),
    }
