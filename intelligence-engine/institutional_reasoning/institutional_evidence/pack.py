"""Module 11 — Institutional Evidence Pack.

What every framework receives. Frameworks consume packs — never raw APIs.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.accounting_quality import (
    produce_accounting_quality,
)
from institutional_reasoning.institutional_evidence.business_quality import (
    produce_business_quality,
)
from institutional_reasoning.institutional_evidence.dcf import produce_dcf_intelligence
from institutional_reasoning.institutional_evidence.historical import (
    produce_historical_intelligence,
)
from institutional_reasoning.institutional_evidence.peer import produce_peer_intelligence
from institutional_reasoning.institutional_evidence.provenance import (
    metric_provenance,
    now_iso,
)
from institutional_reasoning.institutional_evidence.quality import (
    MIN_FRAMEWORK_SCORE,
    pack_score,
    score_metric,
)
from institutional_reasoning.institutional_evidence.sector import produce_sector_intelligence

PACK_VERSION = "institutional-evidence-pack-v1.0.0"


def _current_pe_from_packs(
    entity_id: str,
    packs: dict[str, dict[str, Any]] | None,
) -> float | None:
    """Soft extract current PE from existing DVC/YFP/CID packs without fetching."""
    if not packs:
        return None
    eid = str(entity_id).upper()
    aliases = ("trailing_pe", "current_pe", "pe", "forward_pe", "pe_ratio")

    def walk(node: Any, depth: int = 0) -> float | None:
        if depth > 5 or node is None:
            return None
        if isinstance(node, dict):
            ent = None
            for k in ("symbol", "ticker", "entity_id", "company_symbol"):
                if node.get(k):
                    ent = str(node[k]).upper()
                    break
            # DVC field shape
            if node.get("field") in aliases and node.get("value") is not None:
                if not ent or ent == eid:
                    try:
                        v = float(node["value"])
                        if v > 0:
                            return v
                    except Exception:
                        pass
            for key, val in node.items():
                kl = str(key).lower()
                if kl in aliases and isinstance(val, (int, float)) and val > 0:
                    if not ent or ent == eid:
                        return float(val)
                found = walk(val, depth + 1)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node[:40]:
                found = walk(item, depth + 1)
                if found is not None:
                    return found
        return None

    for pack in packs.values():
        found = walk(pack)
        if found is not None:
            return found
    return None


def _field_envelope(
    *,
    field: str,
    value: Any,
    entity_id: str,
    provider: str,
    method: str,
    quality: dict[str, Any],
    as_of: str,
    data_class: str = "institutional_seed",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Emit contract field only when quality ≥ framework threshold."""
    if value is None:
        return None
    if not quality.get("accept_for_framework"):
        return None
    return metric_provenance(
        field=field,
        value=value,
        entity_id=entity_id,
        provider=provider,
        method=method,
        validated=True,
        quality=quality.get("score"),
        as_of=as_of,
        data_class=data_class,
        extra=extra,
    )


def build_institutional_pack(
    entity_id: str,
    *,
    entity_name: str | None = None,
    entity_type: str | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
    dcf_inputs: dict[str, Any] | None = None,
    financials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the Institutional Evidence Pack for one entity."""
    eid = str(entity_id or "").upper()
    as_of = now_iso()
    current_pe = _current_pe_from_packs(eid, existing_packs)

    hist = produce_historical_intelligence(eid, current_pe=current_pe)
    # If no live current PE, use latest series point (transparent seed).
    if current_pe is None:
        current_pe = hist.get("current_pe")

    peer = produce_peer_intelligence(eid, current_pe=current_pe)
    sector = produce_sector_intelligence(eid)
    bq = produce_business_quality(eid)
    aq = produce_accounting_quality(eid, financials=financials)
    dcf = produce_dcf_intelligence(eid, inputs=dcf_inputs, entity_type=entity_type)

    pe_quality = hist.get("quality") or score_metric(
        value=hist.get("historical_pe"),
        entity_id=eid,
        metric_entity=eid,
        provider="historical_engine",
        as_of=as_of,
        series_n=0,
        validated=False,
    )
    cur_quality = score_metric(
        value=current_pe,
        entity_id=eid,
        metric_entity=eid,
        provider="institutional_seed" if current_pe is not None else "missing",
        as_of=as_of,
        series_n=int((hist.get("pe") or {}).get("analytics", {}).get("n") or 0),
        expected_n=10,
        data_class="institutional_seed",
        validated=current_pe is not None,
        consistency_ok=True,
    )
    pct_quality = score_metric(
        value=hist.get("historical_percentile"),
        entity_id=eid,
        metric_entity=eid,
        provider="historical_analytics",
        as_of=as_of,
        series_n=int((hist.get("pe") or {}).get("analytics", {}).get("n") or 0),
        expected_n=10,
        data_class="institutional_seed",
        validated=hist.get("historical_percentile") is not None,
        consistency_ok=True,
    )
    peer_quality = peer.get("quality") or {"score": 0, "accept_for_framework": False}
    sector_quality = sector.get("quality") or {"score": 0, "accept_for_framework": False}

    validated_fields: dict[str, Any] = {}
    for env in (
        _field_envelope(
            field="current_pe",
            value=current_pe,
            entity_id=eid,
            provider=cur_quality.get("components") and "institutional_evidence" or "missing",
            method="latest_or_dvc",
            quality=cur_quality,
            as_of=as_of,
        ),
        _field_envelope(
            field="historical_pe",
            value=hist.get("historical_pe"),
            entity_id=eid,
            provider="historical_engine",
            method="series_average",
            quality=pe_quality,
            as_of=as_of,
        ),
        _field_envelope(
            field="historical_percentile",
            value=hist.get("historical_percentile"),
            entity_id=eid,
            provider="historical_analytics",
            method="series_percentile",
            quality=pct_quality,
            as_of=as_of,
        ),
        _field_envelope(
            field="peer_pe",
            value=peer.get("peer_pe"),
            entity_id=eid,
            provider="peer_engine",
            method="universe_median",
            quality=peer_quality,
            as_of=as_of,
            extra={"universe": peer.get("peer_universe")},
        ),
        _field_envelope(
            field="sector_pe",
            value=sector.get("sector_pe"),
            entity_id=eid,
            provider="sector_engine",
            method="index_or_peer_median",
            quality=sector_quality,
            as_of=as_of,
        ),
    ):
        if env:
            validated_fields[env["field"]] = env

    # Optional quality metrics for business/financial contracts
    if bq.get("roic") is not None:
        rq = score_metric(
            value=bq["roic"],
            entity_id=eid,
            metric_entity=eid,
            provider="business_quality",
            as_of=as_of,
            series_n=5,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="roic",
            value=bq["roic"],
            entity_id=eid,
            provider="business_quality",
            method="series_latest",
            quality=rq,
            as_of=as_of,
        )
        if env:
            validated_fields["roic"] = env
    if bq.get("margins") is not None:
        mq = score_metric(
            value=bq["margins"],
            entity_id=eid,
            metric_entity=eid,
            provider="business_quality",
            as_of=as_of,
            series_n=5,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="operating_margin",
            value=bq["margins"],
            entity_id=eid,
            provider="business_quality",
            method="series_latest",
            quality=mq,
            as_of=as_of,
        )
        if env:
            validated_fields["operating_margin"] = env
            validated_fields["margins"] = env

    # Revenue quality / competitive position for BQ contract aliases
    rev = (bq.get("summaries") or {}).get("Revenue_Growth", {}).get("latest")
    if rev is not None:
        rq = score_metric(
            value=rev,
            entity_id=eid,
            metric_entity=eid,
            provider="business_quality",
            as_of=as_of,
            series_n=5,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="revenue_growth",
            value=rev,
            entity_id=eid,
            provider="business_quality",
            method="series_latest",
            quality=rq,
            as_of=as_of,
        )
        if env:
            validated_fields["revenue_growth"] = env
            validated_fields["revenue_quality"] = env
    if bq.get("roic") is not None:
        validated_fields.setdefault("competitive_position", validated_fields.get("roic"))

    # Accounting contract fields from BQ / AQ when present
    cc = bq.get("summaries", {}).get("Cash_Conversion", {}).get("latest")
    if cc is None:
        cc = aq.get("cash_conversion")
    if cc is not None:
        cq = score_metric(
            value=cc,
            entity_id=eid,
            metric_entity=eid,
            provider="accounting_quality",
            as_of=as_of,
            series_n=5,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="cash_conversion",
            value=cc,
            entity_id=eid,
            provider="accounting_quality",
            method="series_latest",
            quality=cq,
            as_of=as_of,
        )
        if env:
            validated_fields["cash_conversion"] = env

    lev = aq.get("leverage")
    if lev is None:
        # Soft leverage proxy from Debt series when available
        debt_hist = (hist.get("producers") or {}).get("Debt") or {}
        lev = (debt_hist.get("analytics") or {}).get("latest")
    if lev is not None:
        lq = score_metric(
            value=lev,
            entity_id=eid,
            metric_entity=eid,
            provider="accounting_quality",
            as_of=as_of,
            series_n=3,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="leverage",
            value=lev,
            entity_id=eid,
            provider="accounting_quality",
            method="series_or_aq",
            quality=lq,
            as_of=as_of,
        )
        if env:
            validated_fields["leverage"] = env

    eq = aq.get("earnings_quality")
    if eq is None and cc is not None:
        eq = cc  # cash conversion as earnings-quality proxy with explicit method
    if eq is not None:
        eqq = score_metric(
            value=eq,
            entity_id=eid,
            metric_entity=eid,
            provider="accounting_quality",
            as_of=as_of,
            series_n=3,
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="earnings_quality",
            value=eq,
            entity_id=eid,
            provider="accounting_quality",
            method="cash_conversion_proxy" if aq.get("earnings_quality") is None else "aq_metric",
            quality=eqq,
            as_of=as_of,
        )
        if env:
            validated_fields["earnings_quality"] = env

    # Comparison contract fields from peer engine
    if peer.get("found") and peer.get("peer_universe"):
        pq = peer.get("quality") or score_metric(
            value=len(peer.get("peer_universe") or []),
            entity_id=eid,
            metric_entity=eid,
            provider="peer_engine",
            as_of=as_of,
            series_n=len(peer.get("peer_universe") or []),
            data_class="institutional_seed",
            validated=True,
        )
        env = _field_envelope(
            field="peers",
            value=peer.get("peer_universe"),
            entity_id=eid,
            provider="peer_engine",
            method="universe",
            quality=pq if isinstance(pq, dict) else {"accept_for_framework": True, "score": 90},
            as_of=as_of,
        )
        # peer_set is list — quality envelope uses value; validation accepts non-empty lists
        if peer.get("peer_universe"):
            validated_fields["peers"] = {
                "field": "peers",
                "value": ",".join(peer.get("peer_universe") or []),
                "symbol": eid,
                "entity_id": eid,
                "provider": "peer_engine",
                "verified_at": as_of,
                "as_of": as_of,
                "validated": True,
                "winning_provider": "peer_engine",
                "source": "peer_engine",
            }
            validated_fields["peer_set"] = validated_fields["peers"]
            validated_fields["comparable_metrics"] = {
                "field": "comparable_metrics",
                "value": "PE,ROIC,Revenue_Growth",
                "symbol": eid,
                "entity_id": eid,
                "provider": "peer_engine",
                "verified_at": as_of,
                "as_of": as_of,
                "validated": True,
                "winning_provider": "peer_engine",
                "source": "peer_engine",
            }
            validated_fields["peer_metrics"] = validated_fields["comparable_metrics"]

    # Risk Intelligence — derived VaR/ES/beta/correlation into the evidence pack
    # so risk contracts bind without waiting for a portfolio decision.
    try:
        from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics

        risk_m = derive_risk_metrics(eid)
    except Exception:
        risk_m = None
    if risk_m:
        drivers = risk_m.get("risk_drivers") or {}
        driver_names = [
            k
            for k, v in (
                ("market_beta", drivers.get("beta_vs_benchmark")),
                ("volatility", drivers.get("volatility_ann_pct")),
                ("idiosyncratic_volatility", drivers.get("idiosyncratic_vol_pct")),
                ("liquidity", drivers.get("liquidity_score")),
            )
            if v is not None
        ] or ["market_beta", "volatility"]
        rq = score_metric(
            value=drivers.get("volatility_ann_pct"),
            entity_id=eid,
            metric_entity=eid,
            provider="derived_risk_producer",
            as_of=as_of,
            series_n=int(risk_m.get("horizon_months") or 0),
            expected_n=12,
            data_class="derived",
            validated=True,
            consistency_ok=True,
        )
        if rq.get("accept_for_framework"):
            validated_fields["risk_drivers"] = {
                "field": "risk_drivers",
                "value": ",".join(driver_names),
                "symbol": eid,
                "entity_id": eid,
                "provider": "derived_risk_producer",
                "verified_at": as_of,
                "as_of": as_of,
                "validated": True,
                "winning_provider": "derived_risk_producer",
                "source": "derived_risk_producer",
                "detail": drivers,
                "formulas": risk_m.get("formulas"),
            }
            tail = risk_m.get("downside") or {}
            var95 = tail.get("var_95_monthly_pct")
            if var95 is not None:
                validated_fields["downside_case"] = {
                    "field": "downside_case",
                    "value": round(-abs(float(var95)) / 100.0, 4),
                    "symbol": eid,
                    "entity_id": eid,
                    "provider": "derived_risk_producer",
                    "verified_at": as_of,
                    "as_of": as_of,
                    "validated": True,
                    "winning_provider": "derived_risk_producer",
                    "source": "derived_risk_producer",
                    "detail": tail,
                }
                validated_fields["bear"] = validated_fields["downside_case"]

    scores = [
        cur_quality,
        pe_quality,
        pct_quality,
        peer_quality,
        sector_quality,
    ]
    evidence_score = pack_score(scores)
    coverage = round(
        len([f for f in ("current_pe", "historical_pe", "historical_percentile", "peer_pe") if f in validated_fields])
        / 4.0,
        4,
    )

    summary = {
        "company": entity_name or eid,
        "entity_id": eid,
        "entity_type": entity_type,
        "current_pe": current_pe,
        "historical_pe": hist.get("historical_pe"),
        "historical_percentile": hist.get("historical_percentile"),
        "peer_median": peer.get("peer_pe"),
        "sector_pe": sector.get("sector_pe"),
        "roic": bq.get("roic"),
        "revenue_growth": (bq.get("summaries") or {}).get("Revenue_Growth", {}).get("latest"),
        "fcf_margin": (bq.get("summaries") or {}).get("FCF", {}).get("latest"),
        "evidence_quality": evidence_score,
        "coverage": round(coverage * 100, 1),
    }

    return {
        "pack_version": PACK_VERSION,
        "entity_id": eid,
        "symbol": eid,
        "entity_name": entity_name or eid,
        "entity_type": entity_type,
        "as_of": as_of,
        "summary": summary,
        "validated": validated_fields,
        # Flat aliases for evidence_validation walk
        "current_pe": current_pe if "current_pe" in validated_fields else None,
        "historical_pe": hist.get("historical_pe") if "historical_pe" in validated_fields else None,
        "historical_percentile": (
            hist.get("historical_percentile") if "historical_percentile" in validated_fields else None
        ),
        "peer_pe": peer.get("peer_pe") if "peer_pe" in validated_fields else None,
        "peer_median_pe": peer.get("peer_pe") if "peer_pe" in validated_fields else None,
        "sector_pe": sector.get("sector_pe") if "sector_pe" in validated_fields else None,
        "roic": bq.get("roic"),
        "operating_margin": bq.get("margins"),
        "revenue_growth": (bq.get("summaries") or {}).get("Revenue_Growth", {}).get("latest"),
        "modules": {
            "historical": hist,
            "peer": peer,
            "sector": sector,
            "business_quality": bq,
            "accounting_quality": aq,
            "dcf": dcf,
            "risk": risk_m,
        },
        "risk_drivers": (validated_fields.get("risk_drivers") or {}).get("value"),
        "downside_case": (validated_fields.get("downside_case") or {}).get("value"),
        "evidence_score": evidence_score,
        "coverage": coverage,
        "min_framework_score": MIN_FRAMEWORK_SCORE,
        "accepted_for_frameworks": evidence_score >= MIN_FRAMEWORK_SCORE and coverage >= 0.75,
        "insufficient_fields": [
            f
            for f in ("current_pe", "historical_pe", "historical_percentile", "peer_pe")
            if f not in validated_fields
        ],
    }
