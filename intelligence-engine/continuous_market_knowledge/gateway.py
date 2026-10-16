"""Read-only Market Knowledge Retrieval Gateway — never builds on Ask."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge import traces
from continuous_market_knowledge.schema import canonicalize
from continuous_market_knowledge.store import STORE


def retrieve_all(*, limit: int = 100) -> dict[str, Any]:
    span = traces.begin("market_retrieval", meta={"scope": "list"})
    rows = STORE.list_all(limit=limit)
    out = {
        "n": len(rows),
        "domains": [r.to_public_dict() for r in rows],
        "coverage": STORE.coverage(),
        "providers_queried": [],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "constructed_on_request": False,
        "gateway": "CMKTP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_domain(domain: str) -> dict[str, Any]:
    key = canonicalize(domain) or domain.lower().replace(" ", "_")
    span = traces.begin("market_retrieval", meta={"scope": "domain", "domain": key})
    tip = STORE.latest(key)
    if not tip:
        out = {
            "found": False,
            "domain": key,
            "collected_on_request": False,
            "ask_triggers_collection": False,
            "constructed_on_request": False,
            "reason": "not_published_in_market_knowledge_store",
            "gateway": "CMKTP_KRIG",
            "providers_queried": [],
        }
        traces.end(span, ok=False, output=out)
        return out
    versions = STORE.versions(key)
    out = {
        "found": True,
        "domain": key,
        "latest": tip.to_public_dict(),
        "versions": [v.to_public_dict() for v in versions],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "constructed_on_request": False,
        "gateway": "CMKTP_KRIG",
        "providers_queried": [],
    }
    traces.end(span, output={"found": True, "version": tip.version})
    return out


def retrieve_composite() -> dict[str, Any]:
    """Assemble full Market Knowledge Object from published domain tips."""
    span = traces.begin("market_retrieval", meta={"scope": "composite"})
    tips = {r.domain_key: r for r in STORE.list_all(limit=50)}
    if not tips:
        out = {
            "found": False,
            "collected_on_request": False,
            "ask_triggers_collection": False,
            "constructed_on_request": False,
            "reason": "market_knowledge_not_published",
            "gateway": "CMKTP_KRIG",
            "providers_queried": [],
        }
        traces.end(span, ok=False, output=out)
        return out

    india = tips.get("india_equity")
    health = tips.get("market_health")
    breadth = tips.get("breadth")
    liquidity = tips.get("liquidity")
    volatility = tips.get("volatility")
    flows = tips.get("institutional_flows")
    leadership = tips.get("leadership")
    cross = tips.get("cross_asset")
    risk = tips.get("risk_sentiment")

    composite = {
        "market_regime": (india.market_regime if india else None)
        or (health.market_regime if health else "Unknown"),
        "breadth": (breadth.breadth if breadth else {}) or {},
        "liquidity": (liquidity.liquidity if liquidity else {}) or {},
        "volatility": (volatility.volatility if volatility else {}) or {},
        "institutional_flows": (flows.institutional_flows if flows else {}) or {},
        "leadership": (leadership.leadership if leadership else {}) or {},
        "cross_asset_state": (cross.cross_asset_state if cross else {}) or {},
        "risk_sentiment": (risk.risk_sentiment if risk else None)
        or (india.risk_sentiment if india else "Unknown"),
        "market_health": (health.market_health if health else {})
        or {"score": health.health_score if health else None},
        "health_score": (health.health_score if health else None)
        or (india.health_score if india else None),
        "confidence": round(
            sum(t.confidence for t in tips.values()) / max(1, len(tips)), 3
        ),
        "knowledge_freshness": {
            "domains_published": len(tips),
            "versions_total": STORE.coverage().get("versions_total"),
        },
        "domains": {k: v.to_public_dict() for k, v in tips.items()},
        "version": max((t.version for t in tips.values()), default=1),
    }
    out = {
        "found": True,
        "market": composite,
        "coverage": STORE.coverage(),
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "constructed_on_request": False,
        "gateway": "CMKTP_KRIG",
        "providers_queried": [],
        "programme_short": "CMKTP",
    }
    traces.end(span, output={"domains": len(tips), "health_score": composite.get("health_score")})
    return out
