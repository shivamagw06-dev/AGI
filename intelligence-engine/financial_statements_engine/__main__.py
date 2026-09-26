"""CLI: python -m financial_statements_engine --health|TCS|--dashboard|..."""

from __future__ import annotations

import json
import sys

from financial_statements_engine.production import (
    coverage_report,
    dashboard,
    get_statements,
    health,
    ingest_and_publish,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: python -m financial_statements_engine "
            "--health|--dashboard|--coverage|--registry|"
            "--cfdm-health|--metric-registry|--resolve-metric NAME|"
            "--parsing-health|--parsing-dashboard|--parse-bytes TICKER --format FMT --file PATH|"
            "--quality-health|--quality-dashboard|--certify|--benchmark|"
            "--coverage-health|--coverage-dashboard|--coverage-analytics|"
            "--coverage-matrices TICKER|--coverage-history TICKER [--document-hash HASH]|"
            "--pcc-health|--pcc-dashboard|--pcc-analytics|--pcc-certify [--sector SECTOR]|--pcc-cases|"
            "--validation-health|--validation-dashboard|--validate-draft PATH|--validate-ticker TICKER|"
            "--warehouse-health|--warehouse-dashboard|--warehouse-latest TICKER|"
            "--warehouse-contract CONTRACT TICKER|--warehouse-view TICKER VIEW [--as-of TS]|"
            "--dme-health|--dme-dashboard|--dme-calculate TICKER|"
            "--ecd-health|--ecd-dashboard [universe]|--ecd-company TICKER|"
            "--orch-health|--orch-dashboard|--orch-queue|--orch-history|--orch-dlq|"
            "--orch-status|--orch-workflows|--orch-workflow ID|"
            "--orch-retry ID|--orch-replay ID [--from-stage STAGE]|"
            "--verify-dashboard|--verify-workflow [ID]|--verify-company TICKER|"
            "--verify-universe [LIST]|--workflow-report ID|--workflow-provenance ID|"
            "--fdo-dashboard|--fdo-coverage [universe]|--coverage-company TICKER|"
            "--fdo-schedule|--source-health|--fdo-alerts|"
            "--schema-evolution-health|--schema-resolve LABEL|"
            "--collection-health|--collection-dashboard|--ingest-dashboard|"
            "--source-coverage|--source-registry|--collect-official TICKER|"
            "--collect TICKER [--mode live|historical]|TICKER [--publish]"
        )
        return 0

    cmd = args[0]
    if cmd == "--health":
        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--coverage":
        universe = args[1] if len(args) > 1 else "gold"
        print(json.dumps(coverage_report(universe), indent=2, default=str))
        return 0
    if cmd == "--registry":
        from financial_statements_engine.registry import registry_manifest

        print(json.dumps(registry_manifest(), indent=2, default=str))
        return 0
    if cmd == "--cfdm-health":
        from financial_statements_engine.cfdm.production import health as cfdm_health

        print(json.dumps(cfdm_health(), indent=2, default=str))
        return 0
    if cmd == "--metric-registry":
        from financial_statements_engine.metric_registry.production import health as mr_health

        print(json.dumps(mr_health(), indent=2, default=str))
        return 0
    if cmd == "--resolve-metric":
        from financial_statements_engine.metric_registry.production import resolve_payload

        if len(args) < 2:
            print("metric name required", file=sys.stderr)
            return 2
        print(json.dumps(resolve_payload(" ".join(args[1:])), indent=2, default=str))
        return 0
    if cmd == "--parsing-health":
        from financial_statements_engine.parsing.production import health as parsing_health

        print(json.dumps(parsing_health(), indent=2, default=str))
        return 0
    if cmd == "--parsing-dashboard":
        from financial_statements_engine.parsing.production import dashboard as parsing_dashboard

        print(json.dumps(parsing_dashboard(), indent=2, default=str))
        return 0
    if cmd == "--parse-bytes":
        from financial_statements_engine.parsing.production import parse_file

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        ticker = args[1].upper()
        fmt = "xbrl"
        path = None
        period_end = None
        if "--format" in args:
            i = args.index("--format")
            if i + 1 < len(args):
                fmt = args[i + 1]
        if "--file" in args:
            i = args.index("--file")
            if i + 1 < len(args):
                path = args[i + 1]
        if "--period-end" in args:
            i = args.index("--period-end")
            if i + 1 < len(args):
                period_end = args[i + 1]
        if not path:
            print("--file PATH required", file=sys.stderr)
            return 2
        print(
            json.dumps(
                parse_file(ticker, path, document_type=fmt, period_end=period_end, period_type="annual"),
                indent=2,
                default=str,
            )
        )
        return 0
    if cmd == "--quality-health":
        from financial_statements_engine.parsing.quality.production import health as q_health

        print(json.dumps(q_health(), indent=2, default=str))
        return 0
    if cmd == "--quality-dashboard":
        from financial_statements_engine.parsing.quality.production import dashboard as q_dash

        print(json.dumps(q_dash(), indent=2, default=str))
        return 0
    if cmd == "--certify":
        from financial_statements_engine.parsing.quality.production import run_certification

        print(json.dumps(run_certification(), indent=2, default=str))
        return 0
    if cmd == "--benchmark":
        from financial_statements_engine.parsing.quality.production import run_benchmark_suite

        print(json.dumps(run_benchmark_suite(), indent=2, default=str))
        return 0
    if cmd == "--coverage-health":
        from financial_statements_engine.parsing.coverage.production import health as cov_health

        print(json.dumps(cov_health(), indent=2, default=str))
        return 0
    if cmd == "--coverage-dashboard":
        from financial_statements_engine.parsing.coverage.production import dashboard as cov_dash

        print(json.dumps(cov_dash(), indent=2, default=str))
        return 0
    if cmd == "--coverage-analytics":
        from financial_statements_engine.parsing.coverage.production import analytics as cov_analytics

        print(json.dumps(cov_analytics(), indent=2, default=str))
        return 0
    if cmd == "--coverage-matrices":
        from financial_statements_engine.parsing.coverage.production import matrices_for

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        print(json.dumps(matrices_for(args[1]), indent=2, default=str))
        return 0
    if cmd == "--coverage-history":
        from financial_statements_engine.parsing.coverage.production import history_for

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        doc_hash = None
        if "--document-hash" in args:
            i = args.index("--document-hash")
            if i + 1 < len(args):
                doc_hash = args[i + 1]
        print(json.dumps(history_for(args[1], document_hash=doc_hash), indent=2, default=str))
        return 0
    if cmd == "--pcc-health":
        from financial_statements_engine.parsing.pcc.production import health as pcc_health

        print(json.dumps(pcc_health(), indent=2, default=str))
        return 0
    if cmd == "--pcc-dashboard":
        from financial_statements_engine.parsing.pcc.production import dashboard as pcc_dash

        print(json.dumps(pcc_dash(), indent=2, default=str))
        return 0
    if cmd == "--pcc-analytics":
        from financial_statements_engine.parsing.pcc.production import analytics as pcc_analytics

        print(json.dumps(pcc_analytics(), indent=2, default=str))
        return 0
    if cmd == "--pcc-certify":
        from financial_statements_engine.parsing.pcc.production import run_certification as pcc_certify

        sector = None
        if "--sector" in args:
            i = args.index("--sector")
            if i + 1 < len(args):
                sector = args[i + 1]
        print(json.dumps(pcc_certify(sector=sector), indent=2, default=str))
        return 0
    if cmd == "--pcc-cases":
        from financial_statements_engine.parsing.pcc.production import cases as pcc_cases

        sector = args[1] if len(args) > 1 else None
        print(json.dumps(pcc_cases(sector=sector), indent=2, default=str))
        return 0
    if cmd == "--validation-health":
        from financial_statements_engine.validation.production import health as v_health

        print(json.dumps(v_health(), indent=2, default=str))
        return 0
    if cmd == "--validation-dashboard":
        from financial_statements_engine.validation.production import dashboard as v_dash

        print(json.dumps(v_dash(), indent=2, default=str))
        return 0
    if cmd == "--validate-draft":
        from financial_statements_engine.validation.production import run_validation_file

        if len(args) < 2:
            print("draft path required", file=sys.stderr)
            return 2
        publish = "--no-publish" not in args
        print(json.dumps(run_validation_file(args[1], publish=publish), indent=2, default=str))
        return 0
    if cmd == "--validate-ticker":
        from pathlib import Path

        from financial_statements_engine.store import ensure_dirs
        from financial_statements_engine.validation.production import run_validation_file

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        ticker = args[1].upper().strip()
        latest = ensure_dirs() / "parsing" / "drafts" / ticker / "latest.json"
        if not latest.exists():
            print(f"no draft for {ticker}", file=sys.stderr)
            return 2
        meta = json.loads(latest.read_text(encoding="utf-8"))
        path = meta.get("path")
        if not path or not Path(path).exists():
            print("draft path missing", file=sys.stderr)
            return 2
        publish = "--no-publish" not in args
        print(json.dumps(run_validation_file(str(path), publish=publish), indent=2, default=str))
        return 0
    if cmd == "--warehouse-health":
        from financial_statements_engine.financial_warehouse.production import health as wh_health

        print(json.dumps(wh_health(), indent=2, default=str))
        return 0
    if cmd == "--warehouse-dashboard":
        from financial_statements_engine.financial_warehouse.production import dashboard as wh_dash

        print(json.dumps(wh_dash(), indent=2, default=str))
        return 0
    if cmd == "--warehouse-latest":
        from financial_statements_engine.financial_warehouse.production import get_latest

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        print(json.dumps(get_latest(args[1]), indent=2, default=str))
        return 0
    if cmd == "--warehouse-contract":
        from financial_statements_engine.financial_warehouse.production import contract as wh_contract

        if len(args) < 3:
            print("contract_id and ticker required", file=sys.stderr)
            return 2
        print(json.dumps(wh_contract(args[1], args[2]), indent=2, default=str))
        return 0
    if cmd == "--warehouse-view":
        from financial_statements_engine.financial_warehouse.production import time_travel

        if len(args) < 3:
            print("ticker and view required", file=sys.stderr)
            return 2
        as_of = None
        if "--as-of" in args:
            i = args.index("--as-of")
            if i + 1 < len(args):
                as_of = args[i + 1]
        print(json.dumps(time_travel(args[1], args[2], as_of=as_of), indent=2, default=str))
        return 0
    if cmd == "--dme-health":
        from financial_statements_engine.derived_metrics.production import health as dme_health

        print(json.dumps(dme_health(), indent=2, default=str))
        return 0
    if cmd == "--dme-dashboard":
        from financial_statements_engine.derived_metrics.production import dashboard as dme_dash

        print(json.dumps(dme_dash(), indent=2, default=str))
        return 0
    if cmd == "--dme-calculate":
        from financial_statements_engine.derived_metrics.production import calculate as dme_calc

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        persist = "--no-persist" not in args
        print(json.dumps(dme_calc(args[1], persist=persist), indent=2, default=str))
        return 0
    if cmd == "--dme-formulas":
        from financial_statements_engine.derived_metrics.production import formulas as dme_formulas

        cat = None
        if "--category" in args:
            i = args.index("--category")
            if i + 1 < len(args):
                cat = args[i + 1]
        print(json.dumps(dme_formulas(category=cat), indent=2, default=str))
        return 0
    if cmd == "--dme-contract":
        from financial_statements_engine.derived_metrics.production import contract as dme_contract

        if len(args) < 3:
            print("contract_id and ticker required", file=sys.stderr)
            return 2
        print(json.dumps(dme_contract(args[1], args[2]), indent=2, default=str))
        return 0
    if cmd == "--dme-lineage":
        from financial_statements_engine.derived_metrics.production import lineage as dme_lineage

        if len(args) < 2:
            print("metric_name required", file=sys.stderr)
            return 2
        print(json.dumps(dme_lineage(args[1]), indent=2, default=str))
        return 0
    if cmd == "--ecd-health":
        from financial_statements_engine.evidence_coverage.production import health as ecd_health

        print(json.dumps(ecd_health(), indent=2, default=str))
        return 0
    if cmd == "--ecd-dashboard":
        from financial_statements_engine.evidence_coverage.production import dashboard as ecd_dash

        universe = args[1] if len(args) > 1 else "nifty500"
        include_rows = "--rows" in args
        print(json.dumps(ecd_dash(universe, include_rows=include_rows), indent=2, default=str))
        return 0
    if cmd == "--ecd-company":
        from financial_statements_engine.evidence_coverage.production import company as ecd_company

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        print(json.dumps(ecd_company(args[1]), indent=2, default=str))
        return 0
    if cmd in ("--orch-health", "--orch-status"):
        from financial_statements_engine.orchestrator.production import health as orch_health

        print(json.dumps(orch_health(), indent=2, default=str))
        return 0
    if cmd == "--orch-dashboard":
        from financial_statements_engine.orchestrator.production import dashboard as orch_dash

        print(json.dumps(orch_dash(), indent=2, default=str))
        return 0
    if cmd == "--orch-queue":
        from financial_statements_engine.orchestrator.production import queue as orch_queue

        print(json.dumps(orch_queue(), indent=2, default=str))
        return 0
    if cmd == "--orch-history":
        from financial_statements_engine.orchestrator.production import history as orch_hist

        print(json.dumps(orch_hist(), indent=2, default=str))
        return 0
    if cmd == "--orch-dlq":
        from financial_statements_engine.orchestrator.production import dlq as orch_dlq

        print(json.dumps(orch_dlq(), indent=2, default=str))
        return 0
    if cmd == "--orch-workflows":
        from financial_statements_engine.orchestrator.production import workflows as orch_wfs

        state = None
        if "--state" in args:
            i = args.index("--state")
            if i + 1 < len(args):
                state = args[i + 1]
        print(json.dumps(orch_wfs(state=state), indent=2, default=str))
        return 0
    if cmd == "--orch-workflow":
        from financial_statements_engine.orchestrator.production import workflow_detail

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        print(json.dumps(workflow_detail(args[1]), indent=2, default=str))
        return 0
    if cmd == "--orch-retry":
        from financial_statements_engine.orchestrator.production import retry as orch_retry

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        print(json.dumps(orch_retry(args[1]), indent=2, default=str))
        return 0
    if cmd == "--orch-replay":
        from financial_statements_engine.orchestrator.production import replay as orch_replay

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        from_stage = None
        if "--from-stage" in args:
            i = args.index("--from-stage")
            if i + 1 < len(args):
                from_stage = args[i + 1]
        print(json.dumps(orch_replay(args[1], from_stage=from_stage), indent=2, default=str))
        return 0

    if cmd == "--verify-dashboard":
        from financial_statements_engine.verification.production import dashboard as verify_dashboard

        print(json.dumps(verify_dashboard(), indent=2, default=str))
        return 0
    if cmd == "--fdo-dashboard":
        from financial_statements_engine.fdo.production import dashboard as fdo_dashboard

        universe = args[1] if len(args) > 1 else "gold"
        print(json.dumps(fdo_dashboard(universe), indent=2, default=str))
        return 0
    if cmd == "--fdo-coverage":
        from financial_statements_engine.fdo.production import coverage as fdo_coverage

        universe = args[1] if len(args) > 1 else "gold"
        print(json.dumps(fdo_coverage(universe), indent=2, default=str))
        return 0
    if cmd == "--coverage-company":
        from financial_statements_engine.fdo.production import coverage_company

        if len(args) < 2:
            print("company ticker required", file=sys.stderr)
            return 2
        print(json.dumps(coverage_company(args[1].upper()), indent=2, default=str))
        return 0
    if cmd == "--fdo-schedule":
        from financial_statements_engine.fdo.production import schedule as fdo_schedule

        universe = args[1] if len(args) > 1 else "gold"
        print(json.dumps(fdo_schedule(universe), indent=2, default=str))
        return 0
    if cmd == "--source-health":
        from financial_statements_engine.fdo.production import source_health

        print(json.dumps(source_health(), indent=2, default=str))
        return 0
    if cmd == "--fdo-alerts":
        from financial_statements_engine.fdo.production import alerts as fdo_alerts

        universe = args[1] if len(args) > 1 else "gold"
        print(json.dumps(fdo_alerts(universe), indent=2, default=str))
        return 0
    if cmd == "--verify-workflow":
        from financial_statements_engine.verification.runner import verify_workflow

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        print(json.dumps(verify_workflow(args[1]), indent=2, default=str))
        return 0
    if cmd == "--verify-company":
        from financial_statements_engine.verification.production import run_company

        if len(args) < 2:
            print("company ticker required", file=sys.stderr)
            return 2
        print(json.dumps(run_company(args[1].upper()), indent=2, default=str))
        return 0
    if cmd == "--verify-universe":
        from financial_statements_engine.verification.production import run_universe

        universe = args[1] if len(args) > 1 else None
        print(json.dumps(run_universe(universe), indent=2, default=str))
        return 0
    if cmd == "--workflow-report":
        from financial_statements_engine.verification.production import workflow_report

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        print(json.dumps(workflow_report(args[1]), indent=2, default=str))
        return 0
    if cmd == "--workflow-provenance":
        from financial_statements_engine.verification.production import workflow_provenance

        if len(args) < 2:
            print("workflow_id required", file=sys.stderr)
            return 2
        print(json.dumps(workflow_provenance(args[1]), indent=2, default=str))
        return 0

    if cmd == "--schema-evolution-health":
        from financial_statements_engine.schema_evolution.production import health as se_health

        print(json.dumps(se_health(), indent=2, default=str))
        return 0
    if cmd == "--schema-resolve":
        from financial_statements_engine.schema_evolution.production import resolve_payload as se_resolve

        if len(args) < 2:
            print("label required", file=sys.stderr)
            return 2
        print(json.dumps(se_resolve(" ".join(args[1:])), indent=2, default=str))
        return 0

    if cmd == "--collection-health":
        from financial_statements_engine.collection.production import health as collection_health

        print(json.dumps(collection_health(), indent=2, default=str))
        return 0
    if cmd == "--collection-dashboard":
        from financial_statements_engine.collection.production import dashboard as collection_dashboard

        print(json.dumps(collection_dashboard(), indent=2, default=str))
        return 0
    if cmd == "--ingest-dashboard":
        from financial_statements_engine.collection.production import ingest_dashboard

        print(json.dumps(ingest_dashboard(), indent=2, default=str))
        return 0
    if cmd == "--source-coverage":
        from financial_statements_engine.collection.production import source_coverage

        print(json.dumps(source_coverage(), indent=2, default=str))
        return 0
    if cmd == "--source-registry":
        from financial_statements_engine.collection.production import source_registry

        print(json.dumps(source_registry(), indent=2, default=str))
        return 0
    if cmd == "--collect-official":
        from financial_statements_engine.collection.production import collect_official

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        print(json.dumps(collect_official(args[1].upper()), indent=2, default=str))
        return 0
    if cmd == "--collect":
        from financial_statements_engine.collection.production import collect_ticker

        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        ticker = args[1].upper()
        mode = "live"
        if "--mode" in args:
            i = args.index("--mode")
            if i + 1 < len(args):
                mode = args[i + 1]
        print(json.dumps(collect_ticker(ticker, mode=mode), indent=2, default=str))
        return 0
    if cmd == "--collect-universe":
        from financial_statements_engine.collection.production import run_universe

        universe = args[1] if len(args) > 1 else "gold"
        mode = "live"
        if "--mode" in args:
            i = args.index("--mode")
            if i + 1 < len(args):
                mode = args[i + 1]
        print(json.dumps(run_universe(universe, mode=mode), indent=2, default=str))
        return 0

    ticker = cmd.lstrip("-").upper()
    publish = "--publish" in args
    if publish:
        print(json.dumps(ingest_and_publish(ticker, publish=True), indent=2, default=str))
    else:
        print(json.dumps(get_statements(ticker), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
