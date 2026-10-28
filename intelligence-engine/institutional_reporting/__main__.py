"""CLI: python -m institutional_reporting --ticker AXISBANK [--show-reasons]"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_reporting",
        description="IRE-02 Institutional Reporting Engine + Reason Composer (deterministic, no LLM)",
    )
    parser.add_argument("--ticker", required=False, help="Ticker for fixture-based report")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit full JSON report")
    parser.add_argument(
        "--show-reasons",
        action="store_true",
        help="Print Reason Graph and Diagnostics after the Institutional Report",
    )
    parser.add_argument(
        "--input-json",
        default="",
        help="Path to InstitutionalReportInput JSON (overrides fixture)",
    )
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_reporting.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_reporting.composer import compose_report
    from institutional_reporting.fixtures import get_fixture
    from institutional_reporting.models import InstitutionalReportInput
    from institutional_reporting.renderer import render_diagnostics_text

    if args.input_json:
        with open(args.input_json, encoding="utf-8") as fh:
            payload = json.load(fh)
        report = compose_report(InstitutionalReportInput.from_dict(payload))
    else:
        ticker = (args.ticker or "").strip()
        if not ticker:
            parser.error("--ticker is required unless --health or --input-json is provided")
        fixture = get_fixture(ticker)
        if not fixture:
            print(f"No fixture for ticker={ticker}", file=sys.stderr)
            return 2
        report = compose_report(fixture)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        if report.rejected:
            print("Report rejected", file=sys.stderr)
            print(json.dumps(report.validation_errors, indent=2), file=sys.stderr)
            return 1
        print(report.text)
        if args.show_reasons:
            print()
            print(report.reason_graph_text or "")
            print(render_diagnostics_text(report.diagnostics or {}))
    return 0 if report.ok and not report.rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
