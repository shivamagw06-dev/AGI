"""AGI Intelligence panel — never overwritten by CapIQ market consensus.

Soft-reads existing AGI engines. Missing scores stay null (never fabricated).
"""

from __future__ import annotations

from typing import Any, Optional


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def agi_panel(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    panel: dict[str, Any] = {
        "source": "agi",
        "ticker": t,
        "label": "AGI Intelligence",
        "business_quality": None,
        "financial_quality": None,
        "industry_quality": None,
        "investment_quality": None,
        "research_coverage": None,
        "evidence_confidence": None,
        "monitoring_status": None,
        "latest_research": None,
        "agi_score": None,
        "links": {
            "ask_agi": f"/ask?q={t}",
            "investment_intelligence": f"/admin/investment-intelligence?ticker={t}",
            "business_intelligence": f"/admin/institutional-intelligence?ticker={t}",
            "industry_intelligence": f"/admin/institutional-stack?ticker={t}",
            "research_intelligence": f"/admin/research-execution?ticker={t}",
            "financial_intelligence": f"/admin/financial-statements?ticker={t}",
            "company_workspace": f"/agi/company/{t}",
            "open_full_intelligence": f"/ask?q=Open%20full%20intelligence%20for%20{t}",
        },
        "note": (
            "AGI Institutional Intelligence — distinct from CapIQ Market Consensus. "
            "Never overwritten by CIQ."
        ),
    }
    if not t:
        return panel

    # Investment Intelligence soft read
    inv = _safe(
        lambda: __import__("investment_intelligence.production", fromlist=["analyse"]).analyse(t)
    )
    if isinstance(inv, dict):
        q = inv.get("quality") or inv.get("scores") or {}
        if isinstance(q, dict):
            panel["investment_quality"] = q.get("investment_quality") or q.get("overall")
            panel["business_quality"] = q.get("business_quality") or panel["business_quality"]
            panel["financial_quality"] = q.get("financial_quality") or panel["financial_quality"]
        panel["evidence_confidence"] = inv.get("evidence_confidence") or inv.get("confidence")
        if inv.get("summary"):
            panel["latest_research"] = {
                "title": "Investment Intelligence",
                "summary": str(inv.get("summary"))[:400],
                "source": "investment_intelligence",
            }

    # Business Intelligence soft read (optional APIs differ by version)
    for attr in ("company_card", "analyse", "dossier"):
        bi_mod = _safe(lambda a=attr: __import__("business_intelligence.production", fromlist=[a]))
        if bi_mod is None:
            continue
        fn = getattr(bi_mod, attr, None)
        if not callable(fn):
            continue
        bi = _safe(lambda f=fn: f(t))
        if isinstance(bi, dict):
            panel["business_quality"] = (
                bi.get("business_quality") or bi.get("quality_score") or panel["business_quality"]
            )
            break

    ii = _safe(lambda: __import__("industry_intelligence.production", fromlist=["health"]).health())
    if isinstance(ii, dict) and ii.get("status") in {"ok", "ready", "healthy"}:
        panel["industry_quality"] = panel["industry_quality"] or "available"

    for attr in ("list_for_ticker", "company_documents", "memory_for"):
        ri_mod = _safe(lambda a=attr: __import__("research_intelligence.production", fromlist=[a]))
        if ri_mod is None:
            continue
        fn = getattr(ri_mod, attr, None)
        if not callable(fn):
            continue
        research = _safe(lambda f=fn: f(t))
        if isinstance(research, dict):
            items = research.get("items") or research.get("documents") or []
            panel["research_coverage"] = (
                len(items) if isinstance(items, list) else research.get("count")
            )
            if isinstance(items, list) and items and not panel["latest_research"]:
                first = items[0] if isinstance(items[0], dict) else {"title": str(items[0])}
                panel["latest_research"] = {
                    "title": first.get("title") or "Research",
                    "summary": str(first.get("summary") or first.get("abstract") or "")[:400],
                    "source": "research_intelligence",
                }
            break
        if isinstance(research, list):
            panel["research_coverage"] = len(research)
            break

    mon = _safe(
        lambda: __import__("company_monitor.production", fromlist=["status_for"]).status_for(t)
    )
    if isinstance(mon, dict):
        panel["monitoring_status"] = mon.get("status") or mon.get("state")

    scores = [
        v
        for v in (
            panel["business_quality"],
            panel["financial_quality"],
            panel["investment_quality"],
        )
        if isinstance(v, (int, float))
    ]
    if scores:
        panel["agi_score"] = round(sum(scores) / len(scores), 2)

    return panel


def soft_consensus_facts(row: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Market-consensus facts for Ask — CapIQ observations, never AGI advice."""
    if not isinstance(row, dict):
        return []
    facts: list[dict[str, Any]] = []
    mapping = (
        ("cmp", "current_price"),
        ("target_price", "consensus_target"),
        ("target_high", "target_high"),
        ("target_low", "target_low"),
        ("upside", "consensus_upside_pct"),
        ("buy_count", "broker_buy_count"),
        ("outperform_count", "broker_outperform_count"),
        ("hold_count", "broker_hold_count"),
        ("sell_count", "broker_sell_count"),
        ("coverage", "analyst_coverage"),
        ("market_cap", "market_cap"),
        ("enterprise_value", "enterprise_value"),
        ("revenue", "revenue"),
        ("ebitda", "ebitda"),
        ("sector", "sector"),
        ("industry", "industry"),
    )
    for src, name in mapping:
        v = row.get(src)
        if v is not None and v != "":
            facts.append(
                {
                    "field": name,
                    "value": v,
                    "source": "capital_iq_market_consensus",
                    "layer": "market_consensus",
                }
            )
    return facts
