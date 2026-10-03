#!/usr/bin/env python3
"""Institutional Data Warehouse — acceptance suite.

Proves the contract the warehouse promises, against a real database populated
from the live collectors on this machine:

  1. fourteen tabs exist as physical tables
  2. the refresh pipeline runs every stage and records the run
  3. imported values keep provenance and are never destroyed by an edit
  4. calculated columns reject manual edits and recompute server-side
  5. every change is versioned, diffable and restorable
  6. every action is audited with a named actor
  7. validation rejects impossible rows before they are stored
  8. global search reaches every sheet from one query
  9. intelligence modules can read a company through the warehouse contract

Run:
    cd intelligence-engine
    INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_acceptance PYTHONPATH=. \
        python3 scripts/warehouse_acceptance_v1.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from institutional_warehouse import db, importer, production, refresh, store, validation  # noqa: E402
from institutional_warehouse.schema import TABS  # noqa: E402

ACTOR = "acceptance@agi"
RESULTS: list[dict[str, Any]] = []


def check(name: str, fn: Callable[[], tuple[bool, Any]]) -> bool:
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as exc:  # a raised error is a failed case, not a crashed suite
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    RESULTS.append(
        {
            "case": name,
            "pass": bool(ok),
            "detail": detail,
            "ms": int((time.perf_counter() - t0) * 1000),
        }
    )
    return bool(ok)


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


def case_schema() -> tuple[bool, Any]:
    info = db.info()
    missing = [t.id for t in TABS if t.id not in info["row_counts"]]
    return not missing and len(TABS) == 14, {"tabs": len(TABS), "missing": missing}


def case_refresh() -> tuple[bool, Any]:
    result = refresh.run(actor=ACTOR, limit=120, days=5)
    stages = {k: bool(v.get("ok")) for k, v in result["stages"].items()}
    counts = result["row_counts"]
    populated = [k for k, v in counts.items() if v]
    return (
        result["ok"] and len(populated) >= 8,
        {"stages": stages, "populated_tabs": len(populated), "total_rows": sum(counts.values())},
    )


def case_provenance() -> tuple[bool, Any]:
    rows = store.fetch("company_master", limit=1)["rows"]
    if not rows:
        return False, "company_master is empty"
    row = rows[0]
    return bool(row.get("source") and row.get("last_updated")), {
        "symbol": row.get("symbol"),
        "source": row.get("source"),
        "last_updated": row.get("last_updated"),
    }


def case_override_layer() -> tuple[bool, Any]:
    row = store.fetch("company_master", limit=1)["rows"][0]
    original = row.get("sector")
    result = production.edit(
        "company_master",
        [{"row_id": row["row_id"], "column": "sector", "value": "Override Sector"}],
        actor=ACTOR, reason="acceptance", recalc=False,
    )
    effective = store.get("company_master", row["row_id"])
    base = store.raw_row("company_master", row["row_id"])
    ok = (
        result.get("applied") == 1
        and effective["sector"] == "Override Sector"
        and base.get("sector") == original
        and "sector" in effective["_meta"]["overridden"]
    )
    production.clear_override("company_master", row["row_id"], "sector", actor=ACTOR)
    reverted = store.get("company_master", row["row_id"])["sector"]
    return ok and reverted == original, {
        "imported_value_kept": base.get("sector"),
        "override_applied": "Override Sector",
        "reverted_to": reverted,
    }


def case_computed_columns() -> tuple[bool, Any]:
    ratios = store.fetch("historical_ratios", limit=1)["rows"]
    if not ratios:
        return False, "no calculated ratios present"
    attempt = production.edit(
        "historical_ratios",
        [{"row_id": ratios[0]["row_id"], "column": "roe", "value": 999}],
        actor=ACTOR,
    )
    recalc = production.recompute(actor=ACTOR, stages=["ratios"])
    return (
        attempt.get("ok") is False and recalc.get("ok") is True,
        {"edit_refused": attempt.get("error"), "recalculated": recalc.get("ok")},
    )


def case_versions() -> tuple[bool, Any]:
    row = store.fetch("company_master", limit=1)["rows"][0]
    production.edit("company_master", [{"row_id": row["row_id"], "column": "city", "value": "Mumbai"}],
                    actor=ACTOR, reason="v-a", recalc=False)
    production.edit("company_master", [{"row_id": row["row_id"], "column": "city", "value": "Delhi"}],
                    actor=ACTOR, reason="v-b", recalc=False)
    history = production.history("company_master", row["row_id"])
    versions = [int(v["version"]) for v in history["versions"]]
    if not versions:
        return False, "no snapshots recorded"
    diff = production.compare("company_master", row["row_id"], min(versions))
    restored = production.restore("company_master", row["row_id"], version=min(versions), actor=ACTOR)
    return (
        len(history["cells"]) >= 2 and diff.get("ok") and restored.get("ok"),
        {
            "cell_changes": len(history["cells"]),
            "versions": len(versions),
            "diff_changes": len(diff.get("changes") or []),
            "restored": restored.get("restored_version"),
        },
    )


def case_audit() -> tuple[bool, Any]:
    log = production.audit_log(limit=200)
    actions = {entry["action"] for entry in log["entries"]}
    unnamed = [e for e in log["entries"] if not e.get("actor")]
    required = {"edit", "refresh", "restore"}
    return (
        required <= actions and not unnamed,
        {"actions": sorted(actions), "entries": log["total"], "unnamed": len(unnamed)},
    )


def case_validation() -> tuple[bool, Any]:
    symbol = (store.fetch("company_master", limit=1)["rows"][0] or {}).get("symbol") or "AAA"
    staged = importer.stage(
        "daily_market_history",
        rows=[
            {"symbol": symbol, "date": "2026-07-31", "open": 10, "high": 5, "low": 8, "close": 9},
            {"symbol": symbol, "date": "2026-07-30", "close": 100},
            {"symbol": symbol, "date": "2026-07-30", "close": 101},
            {"symbol": "", "date": "2026-07-29", "close": 5},
        ],
        actor=ACTOR,
    )
    board = production.validate()
    return (
        staged["rejected"] == 3 and staged["accepted"] == 1 and "tabs" in board,
        {
            "rejected": staged["rejected"],
            "accepted": staged["accepted"],
            "failing_tables": board.get("failed"),
        },
    )


def case_paste_import() -> tuple[bool, Any]:
    symbol = (store.fetch("company_master", limit=1)["rows"][0] or {}).get("symbol") or "AAA"
    pasted = f"Symbol\tDate\tClose\tVolume\n{symbol}\t28-Jul-2026\t1,234.50\t900000\n"
    staged = importer.stage("daily_market_history", text=pasted, actor=ACTOR, source="acceptance_paste")
    committed = importer.commit(staged["import_id"], actor=ACTOR, recalculate=False)
    stored = store.fetch("daily_market_history",
                         filters={"symbol": symbol, "date": "2026-07-28"})["rows"]
    return (
        staged["accepted"] == 1 and committed.get("ok") and stored and stored[0]["close"] == 1234.5,
        {
            "mapped": staged["mapping"].get("mapped_count"),
            "stored_close": stored[0]["close"] if stored else None,
        },
    )


def case_search() -> tuple[bool, Any]:
    master = store.fetch("company_master", limit=1)["rows"][0]
    name = master.get("company_name") or master.get("symbol")
    hits = production.global_search(name, per_tab=2)
    tabs = {t["tab"] for t in hits.get("tabs") or []}
    return (
        hits.get("ok") and hits.get("symbol") == master["symbol"] and len(tabs) >= 3,
        {"query": name, "resolved": hits.get("symbol"), "tabs_hit": sorted(tabs)},
    )


def case_engine_contract() -> tuple[bool, Any]:
    symbol = store.fetch("company_master", limit=1)["rows"][0]["symbol"]
    record = production.read_company(symbol)
    filled = [k for k in ("master", "valuation", "ratios", "factors", "latest_price")
              if record.get(k)]
    from knowledge_unification.providers.institutional_warehouse import (
        InstitutionalWarehouseProvider,
    )
    from knowledge_unification.schema import QueryPlan

    provider = InstitutionalWarehouseProvider()
    consulted = provider.consult(
        QueryPlan(question=f"Is {symbol} expensive?", question_types=["valuation"], ticker_hint=symbol)
    )
    return (
        record.get("ok") and len(filled) >= 3 and consulted.ok and not consulted.empty,
        {
            "symbol": symbol,
            "sections": filled,
            "provider_facts": len(consulted.facts),
            "provider_summary": consulted.summary[:160],
        },
    )


CASES: tuple[tuple[str, Callable[[], tuple[bool, Any]]], ...] = (
    ("schema_fourteen_tabs", case_schema),
    ("daily_refresh_pipeline", case_refresh),
    ("imported_values_keep_provenance", case_provenance),
    ("override_layer_never_destroys_imports", case_override_layer),
    ("calculated_columns_are_server_owned", case_computed_columns),
    ("versions_diff_and_restore", case_versions),
    ("audit_trail_names_every_actor", case_audit),
    ("validation_rejects_before_publish", case_validation),
    ("excel_paste_maps_and_commits", case_paste_import),
    ("global_search_spans_sheets", case_search),
    ("engines_read_through_the_warehouse", case_engine_contract),
)


def main() -> int:
    db.init(force=True)
    for name, fn in CASES:
        check(name, fn)

    passed = sum(1 for r in RESULTS if r["pass"])
    summary = {
        "suite": "warehouse_acceptance_v1",
        "cases": len(RESULTS),
        "passed": passed,
        "failed": len(RESULTS) - passed,
        "pass_rate_pct": round(100.0 * passed / max(len(RESULTS), 1), 1),
        "database": db.info().get("url"),
        "total_rows": db.info().get("total_rows"),
    }
    print(json.dumps(summary, indent=2))
    for result in RESULTS:
        mark = "PASS" if result["pass"] else "FAIL"
        print(f"  [{mark}] {result['case']} ({result['ms']}ms) {json.dumps(result['detail'], default=str)[:300]}")

    out = Path("/tmp/warehouse_acceptance_v1.json")
    out.write_text(json.dumps({"summary": summary, "results": RESULTS}, indent=2, default=str))
    print(f"wrote {out}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
