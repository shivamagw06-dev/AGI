"""Generate LIVE_DATA_CERTIFICATION_REPORT.md from verification results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from live_data import store
from live_data.verification.schema import CERTIFIED_CONSECUTIVE_LIVE_RUNS, VERIFY_VERSION


def readiness_score(report: dict[str, Any]) -> dict[str, Any]:
    """0–10 institutional live-data readiness. Honest — CERTIFIED rarity reflected."""
    collectors = report.get("collectors") or []
    n = max(len(collectors), 1)
    live = sum(1 for c in collectors if c.get("mode") == "LIVE")
    snap = sum(1 for c in collectors if c.get("mode") == "SNAPSHOT")
    fixture = sum(1 for c in collectors if c.get("FIXTURE"))
    certs = report.get("certification_summary") or {}
    levels = certs.get("levels") or {}
    certified = int(levels.get("CERTIFIED") or 0)
    prod_ready = int(levels.get("PRODUCTION_READY") or 0)
    staging = int(levels.get("STAGING") or 0)

    probe = report.get("probe_summary") or {}
    reachable = int(probe.get("reachable") or 0)
    download_ok = int(probe.get("download_ok") or 0)
    total_p = max(int(probe.get("total") or n), 1)

    checklist_rates = [float((c.get("checklist") or {}).get("pass_rate") or 0) for c in collectors]
    avg_checklist = sum(checklist_rates) / len(checklist_rates) if checklist_rates else 0

    platform = report.get("platform") or {}
    platform_ok = sum(
        1
        for k in ("scheduler", "research_office", "ask_pipeline", "mission_control", "reasoning")
        if (platform.get(k) or {}).get("ok")
    )

    # Weighted score
    score = 0.0
    score += 2.5 * (reachable / total_p)  # endpoint reachability
    score += 2.0 * (download_ok / total_p)  # successful download signal
    score += 2.0 * avg_checklist  # checklist completeness
    score += 1.5 * (platform_ok / 5.0)  # platform soft integration
    score += 1.0 * ((staging + prod_ready + certified) / n)  # certification progress
    score += 1.0 * (certified / n)  # full certification bonus
    if fixture:
        score -= 2.0
    if report.get("replay", {}).get("ok"):
        score += 0.5
    score = max(0.0, min(10.0, round(score, 1)))

    return {
        "score": score,
        "live_collectors": live,
        "snapshot_collectors": snap,
        "fixture_collectors": fixture,
        "certified": certified,
        "production_ready": prod_ready,
        "staging": staging,
        "avg_checklist_pass_rate": round(avg_checklist, 4),
        "platform_checks_ok": platform_ok,
        "interpretation": _interpret(score, certified, live, n),
    }


def _interpret(score: float, certified: int, live: int, n: int) -> str:
    if certified == n:
        return "All collectors CERTIFIED — live institutional data is production-proven."
    if live == n and score >= 8:
        return "All collectors LIVE in this run; consecutive-day certification still required."
    if score >= 6:
        return "Architecture and soft-wires ready; live source access / structured exports remain the bottleneck."
    if score >= 4:
        return "Partial live readiness — probes or lifecycle incomplete for one or more collectors."
    return "Not production-ready — collectors not consuming certified live institutional data."


def render_markdown(report: dict[str, Any]) -> str:
    rs = readiness_score(report)
    collectors = report.get("collectors") or []
    certs = report.get("certification_summary") or {}
    qg = report.get("quality_gates") or {}
    platform = report.get("platform") or {}
    probe = report.get("probe_summary") or {}

    lines: list[str] = []
    lines.append("# LIVE DATA CERTIFICATION REPORT")
    lines.append("")
    lines.append(f"**Programme:** AGIB v3.0 – Live Collector Activation & Production Verification  ")
    lines.append(f"**Version:** `{VERIFY_VERSION}`  ")
    lines.append(f"**Run ID:** `{report.get('run_id')}`  ")
    lines.append(f"**Generated:** `{report.get('finished_at')}`  ")
    lines.append(f"**Overall Live Data Readiness Score:** **{rs['score']}/10** — {rs['interpretation']}")
    lines.append("")
    lines.append("## Freeze locks")
    lines.append("")
    lines.append("Reasoning, Knowledge Factory, Ask Pipeline, Institutional Scheduler, and Research Office remain **frozen**. Track 2 only activates/verifies/certifies LIDI collectors.")
    lines.append("")
    lines.append("## Collector Summary")
    lines.append("")
    lines.append("| Collector | Official Source | Mode | Certification | Records Accepted | Validation Rate | Freshness | Replay |")
    lines.append("|---|---|---|---|---:|---:|---|---|")
    for c in collectors:
        lines.append(
            f"| {c.get('collector')} | {c.get('official_source')} | {c.get('mode')} | "
            f"{c.get('status')} | {c.get('records_accepted')} | {c.get('validation_rate')} | "
            f"{c.get('freshness')} | {c.get('replay_status')} |"
        )
    lines.append("")
    lines.append("## Production Status")
    lines.append("")
    levels = certs.get("levels") or {}
    lines.append(f"- Collectors: **{certs.get('collectors')}**")
    lines.append(f"- CERTIFIED: **{levels.get('CERTIFIED', 0)}** (requires {CERTIFIED_CONSECUTIVE_LIVE_RUNS} consecutive LIVE days)")
    lines.append(f"- PRODUCTION_READY: **{levels.get('PRODUCTION_READY', 0)}**")
    lines.append(f"- STAGING: **{levels.get('STAGING', 0)}**")
    lines.append(f"- TESTING: **{levels.get('TESTING', 0)}**")
    lines.append(f"- DEVELOPMENT: **{levels.get('DEVELOPMENT', 0)}**")
    lines.append(f"- All certified: **{certs.get('all_certified')}**")
    lines.append("")
    lines.append("## Validation Statistics")
    lines.append("")
    for c in collectors:
        ch = c.get("checklist") or {}
        lines.append(
            f"- **{c.get('collector')}**: retrieved={ch.get('records_retrieved')}, "
            f"accepted={ch.get('records_accepted')}, rejected={ch.get('records_rejected')}, "
            f"checklist={ch.get('passed')}/{ch.get('total')} ({ch.get('pass_rate')})"
        )
    lines.append("")
    lines.append("## Live Endpoint Probes")
    lines.append("")
    lines.append(f"- Reachable: **{probe.get('reachable')}/{probe.get('total')}**")
    lines.append(f"- Download OK signal: **{probe.get('download_ok')}/{probe.get('total')}**")
    for sid, row in (probe.get("by_source") or {}).items():
        err = row.get("error") or ""
        lines.append(
            f"- `{sid}`: reachable={row.get('reachable')}, download_ok={row.get('download_ok')}, "
            f"latency_ms={row.get('latency_ms')}"
            + (f", error=`{err[:120]}`" if err else "")
        )
    lines.append("")
    lines.append("## Knowledge Coverage")
    lines.append("")
    pub = (report.get("ingestion") or {}).get("publish") or {}
    lines.append(f"- Object counts: `{pub.get('object_counts')}`")
    lines.append(f"- Pack IDs: `{pub.get('pack_ids')}`")
    lines.append(f"- Fixture collectors disabled for LIDI sources: `{pub.get('fixture_collectors_disabled_for_lidi_sources')}`")
    lines.append("")
    lines.append("## Evidence Coverage")
    lines.append("")
    lines.append(f"- Pack count: **{pub.get('pack_count')}**")
    lines.append(f"- Knowledge Factory soft emit: `{pub.get('knowledge_factory_soft')}`")
    lines.append("")
    lines.append("## Replay Status")
    lines.append("")
    rp = report.get("replay") or {}
    lines.append(f"- Deterministic checksum replay: **{'PASS' if rp.get('ok') else 'FAIL'}**")
    lines.append(f"- Detail: `{rp}`")
    lines.append("")
    lines.append("## Platform Integration")
    lines.append("")
    for name, key in (
        ("Scheduler", "scheduler"),
        ("Research Office", "research_office"),
        ("Ask Pipeline", "ask_pipeline"),
        ("Mission Control", "mission_control"),
        ("Reasoning untouched", "reasoning"),
    ):
        row = platform.get(key) or {}
        lines.append(f"- **{name}**: {'OK' if row.get('ok') else 'FAIL/DEGRADED'} — `{ {k: row.get(k) for k in list(row)[:6]} }`")
    lines.append("")
    mv = report.get("morning_verification") or {}
    lines.append("## Morning Verification")
    lines.append("")
    lines.append(f"- OK: **{mv.get('ok')}**")
    lines.append(f"- Dry run: `{mv.get('dry_run')}`")
    lines.append(f"- State: `{mv.get('state')}`")
    lines.append(f"- System ready: `{mv.get('system_ready')}`")
    lines.append("")
    lines.append("## Quality Gates")
    lines.append("")
    lines.append(f"- Passed: **{qg.get('passed')}**")
    lines.append(f"- Failures: `{qg.get('failures')}`")
    lines.append("")
    lines.append("## Outstanding Failures")
    lines.append("")
    failures = list(qg.get("failures") or [])
    for c in collectors:
        if c.get("mode") != "LIVE":
            failures.append(f"not_live:{c.get('source_id')}:{c.get('mode')}")
        if c.get("probe", {}).get("error"):
            failures.append(f"probe_error:{c.get('source_id')}")
        if (c.get("certification") or {}).get("level") not in {"PRODUCTION_READY", "CERTIFIED"}:
            failures.append(f"uncertified:{c.get('source_id')}:{(c.get('certification') or {}).get('level')}")
    if not failures:
        lines.append("- None")
    else:
        for f in sorted(set(failures)):
            lines.append(f"- `{f}`")
    lines.append("")
    lines.append("## Recommended Fixes")
    lines.append("")
    lines.append("1. **NSE session/cookies** — Bhavcopy archives and announcement APIs frequently return 403 without a browser-like cookie jar; add an official NSE session bootstrap (still no raw→reasoning).")
    lines.append("2. **BSE structured export** — Homepage reachability ≠ corporate-actions CSV; implement the official tabular download adapter.")
    lines.append("3. **RBI DBIE series API** — Prefer documented DBIE SDMX/CSV endpoints over HTML home; handle TLS hostname carefully with pinned certs.")
    lines.append("4. **Company IR adapters** — Per-issuer HTML→filing extractors (results, presentations, guidance) with checksummed PDF capture.")
    lines.append(f"5. **Certification clock** — Run production morning ingestion for **{CERTIFIED_CONSECUTIVE_LIVE_RUNS} consecutive LIVE days** with zero fixture/snapshot fallback to reach CERTIFIED.")
    lines.append("6. **Disable KF fixture collectors in production** when LIDI mode=LIVE for the same source family (already soft-flagged).")
    lines.append("")
    lines.append("## Snapshot Policy (enforced)")
    lines.append("")
    lines.append("If live collection fails → latest **validated LIDI snapshot** → mark **STALE** → transparent insufficiency. **Never fixture. Never silent substitute.**")
    lines.append("")
    lines.append("## Exit Gate Assessment")
    lines.append("")
    all_certified = bool(certs.get("all_certified"))
    lines.append(f"- Every collector production certified: **{all_certified}**")
    lines.append(f"- No fixture collector active in this verification: **{rs['fixture_collectors'] == 0}**")
    lines.append(f"- Evidence packs present: **{bool(pub.get('pack_ids'))}**")
    lines.append(f"- Morning scheduler verification: **{mv.get('ok')}**")
    lines.append(f"- Replay deterministic: **{rp.get('ok')}**")
    lines.append(f"- Reasoning unchanged: **{(platform.get('reasoning') or {}).get('ok')}**")
    lines.append("")
    lines.append("> Track 2 exit gate is **not** claimed complete until every collector is CERTIFIED via consecutive LIVE production days.")
    lines.append("")
    lines.append("---")
    lines.append(f"_Generated by LIDI Track 2 verifier `{VERIFY_VERSION}`_")
    return "\n".join(lines) + "\n"


def write_certification_report(
    report: dict[str, Any] | None = None,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    report = report or store.get_report("last_verification") or {}
    if not report:
        return {"ok": False, "error": "no_verification_report"}
    md = render_markdown(report)
    out = Path(
        path
        or Path(__file__).resolve().parents[2].parent
        / "docs"
        / "LIVE_DATA_CERTIFICATION_REPORT.md"
    )
    # Prefer repo docs/
    repo_docs = Path(__file__).resolve().parents[3] / "docs" / "LIVE_DATA_CERTIFICATION_REPORT.md"
    target = Path(path) if path else repo_docs
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    # Also store under LIDI reports
    store.put_report("LIVE_DATA_CERTIFICATION_REPORT", {"markdown": md, "path": str(target)})
    rs = readiness_score(report)
    return {"ok": True, "path": str(target), "readiness": rs, "bytes": len(md.encode("utf-8"))}
