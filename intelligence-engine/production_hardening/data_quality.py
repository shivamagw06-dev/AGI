"""Data quality — freshness SLAs, provenance, duplicates, confidence per source."""

from __future__ import annotations

from typing import Any

from production_hardening.schema import DATA_SOURCES, FRESHNESS_SLA_DAYS, GOLD_REGRESSION_UNIVERSE
from production_hardening.util import age_days, as_float, now_iso, soft_call


def run_data_quality(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tickers = list(universe) if universe else list(GOLD_REGRESSION_UNIVERSE)
    rows = []
    failures = []
    cache_hits = 0
    cache_total = 0

    for t in tickers:
        inj = (injected_by_ticker or {}).get(t)
        pack = inj or soft_call("collect", _collect, t)
        mem = pack.get("memory") if isinstance(pack.get("memory"), dict) else {}
        oie = pack.get("opportunity") if isinstance(pack.get("opportunity"), dict) else {}
        graph = pack.get("knowledge_graph") if isinstance(pack.get("knowledge_graph"), dict) else {}

        cache_total += 1
        if mem.get("ok"):
            cache_hits += 1

        freshness = _freshness_checks(mem, oie)
        provenance = _provenance(mem, oie, graph)
        duplicates = _duplicate_checks(oie, mem)
        confidence = _confidence(mem, oie)

        row = {
            "ticker": t,
            "entity": pack.get("entity") or oie.get("entity") or t,
            "ok": bool(pack.get("ok") or oie.get("ok")),
            "freshness": freshness,
            "provenance": provenance,
            "duplicates": duplicates,
            "confidence": confidence,
            "sla_pass": all(f.get("within_sla") is not False for f in freshness),
        }
        rows.append(row)
        for f in freshness:
            if f.get("within_sla") is False:
                failures.append({"ticker": t, "type": "freshness_sla", "detail": f})
        for d in duplicates:
            if d.get("duplicate"):
                failures.append({"ticker": t, "type": "duplicate", "detail": d})
        if not provenance.get("sources"):
            failures.append({"ticker": t, "type": "provenance_missing", "detail": provenance})

    return {
        "as_of": now_iso(),
        "sources_catalog": list(DATA_SOURCES),
        "freshness_sla_days": dict(FRESHNESS_SLA_DAYS),
        "n": len(rows),
        "sla_pass_n": sum(1 for r in rows if r.get("sla_pass")),
        "cache_hit_rate_pct": round(100.0 * cache_hits / max(1, cache_total), 1),
        "failures": failures,
        "freshness": {
            "rows": [
                {
                    "ticker": r["ticker"],
                    "checks": r["freshness"],
                    "sla_pass": r["sla_pass"],
                }
                for r in rows
            ]
        },
        "rows": rows,
        "recommendation_policy": "hardening_diagnostics_only_no_buy_sell",
    }


def _freshness_checks(mem: dict[str, Any], oie: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    mem_ts = mem.get("compiled_at") or (oie.get("freshness") or {}).get("memory_compiled_at")
    age = age_days(mem_ts)
    sla = FRESHNESS_SLA_DAYS["company_memory"]
    checks.append(
        {
            "source": "company_memory",
            "timestamp": mem_ts,
            "age_days": round(age, 2) if age is not None else None,
            "sla_days": sla,
            "within_sla": (age is None) or (age <= sla),
        }
    )
    oie_ts = (oie.get("freshness") or {}).get("as_of") or oie.get("generated_at")
    age_o = age_days(oie_ts)
    sla_o = FRESHNESS_SLA_DAYS["opportunity_intelligence"]
    checks.append(
        {
            "source": "opportunity_intelligence",
            "timestamp": oie_ts,
            "age_days": round(age_o, 2) if age_o is not None else None,
            "sla_days": sla_o,
            "within_sla": (age_o is None) or (age_o <= sla_o),
        }
    )
    return checks


def _provenance(mem: dict[str, Any], oie: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    sources = []
    if mem.get("ok") or mem.get("memory_version") is not None:
        sources.append(
            {
                "source": "company_memory",
                "memory_version": mem.get("memory_version"),
                "engine": mem.get("engine") or mem.get("version"),
            }
        )
    if oie.get("ok"):
        sources.append(
            {
                "source": "opportunity_intelligence",
                "engine": oie.get("engine"),
                "version": oie.get("version"),
                "provenance": (oie.get("opportunity") or {}).get("provenance") or oie.get("provenance"),
            }
        )
    if graph.get("n_nodes"):
        sources.append(
            {
                "source": "investment_knowledge_graph",
                "n_nodes": graph.get("n_nodes"),
                "n_edges": graph.get("n_edges"),
            }
        )
    return {"sources": sources, "source_count": len(sources)}


def _duplicate_checks(oie: dict[str, Any], mem: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    # Duplicate catalyst names
    names = [c.get("name") for c in (oie.get("catalysts") or []) if c.get("name")]
    seen = set()
    dups = []
    for n in names:
        key = str(n).lower().strip()
        if key in seen:
            dups.append(n)
        seen.add(key)
    out.append({"field": "catalysts", "duplicate": bool(dups), "values": dups[:5]})

    # Duplicate blocker codes
    codes = [b.get("code") for b in (oie.get("blockers") or []) if b.get("code")]
    code_dups = [c for c in codes if codes.count(c) > 1]
    out.append({"field": "blockers", "duplicate": bool(code_dups), "values": sorted(set(code_dups))})
    return out


def _confidence(mem: dict[str, Any], oie: dict[str, Any]) -> dict[str, Any]:
    mem_c = as_float(mem.get("confidence"))
    oie_c = as_float(oie.get("confidence"))
    if mem_c is not None and mem_c <= 1:
        mem_c *= 100
    if oie_c is not None and oie_c <= 1:
        oie_c *= 100
    return {
        "company_memory": mem_c,
        "opportunity_intelligence": oie_c,
        "agreement": (
            None
            if mem_c is None or oie_c is None
            else round(100.0 - abs(mem_c - oie_c), 1)
        ),
    }


def _collect(ticker: str) -> dict[str, Any]:
    from investment_operations.collect import collect_company

    return collect_company(ticker, persist_memory=False, include_soft_reasoning=False)
