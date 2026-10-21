"""Temporal Integrity Report (markdown)."""

from __future__ import annotations

from typing import Any


def build_markdown(cert: dict[str, Any], board: dict[str, Any] | None = None) -> str:
    board = board or {}
    lines = [
        "# AGI Temporal Integrity Report (TIRC)",
        "",
        f"**Company:** AGI",
        f"**Version:** {cert.get('tirc_version')}",
        f"**Certification:** {cert.get('certification_result')}",
        "",
        "## Metrics",
        "",
        f"- Objects checked: {cert.get('objects_checked')}",
        f"- Objects rejected: {cert.get('objects_rejected')}",
        f"- Future leakage count: {cert.get('future_leakage_count')}",
        f"- Replay accuracy: {cert.get('replay_accuracy_pct')}%",
        f"- Coverage (IEL pass): {(cert.get('coverage') or {}).get('iel_pass_pct')}",
        f"- Rejected sources: {', '.join(cert.get('rejected_sources') or []) or '—'}",
        "",
        "## Remaining risks",
        "",
    ]
    risks = cert.get("remaining_risks") or ["None"]
    for r in risks:
        lines.append(f"- {r}")
    lines.extend(
        [
            "",
            "## Replay health",
            "",
            f"- Status: {board.get('replay_health')}",
            f"- Institutional guarantee: {board.get('institutional_guarantee')}",
            "",
        ]
    )
    return "\n".join(lines)
