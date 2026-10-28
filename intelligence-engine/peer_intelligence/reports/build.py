"""Institutional peer intelligence report."""

from __future__ import annotations

from typing import Any

from peer_intelligence.commentary.engine import commentary_for
from peer_intelligence.scorecards.build import scorecard
from peer_intelligence.schema import PIL_VERSION


def build_report(ticker: str) -> dict[str, Any]:
    card = scorecard(ticker)
    comment = commentary_for(ticker)
    if not card.get("found"):
        return {"ticker": ticker, "found": False, "text": "No peer pack resolved."}

    lines = [
        f"Peer Intelligence Report — {card['ticker']}",
        f"PIL {PIL_VERSION} | Sector: {card.get('sector')}",
        "",
        "PRIMARY QUESTION",
        "How does this company compare to the best and most relevant peers?",
        "",
        "NARRATIVE",
        comment.get("narrative") or "",
        "",
        "TRAJECTORY",
        comment.get("trajectory_insight") or "n/a",
        "",
        "TOP RANKS",
    ]
    for r in (card.get("metric_ranks") or [])[:8]:
        lines.append(
            f"- {r['metric']}: rank {r['rank']}/{r['n']} (pctl {r['percentile']}) value={r['value']}"
        )
    lines += [
        "",
        "OUTLIERS",
    ]
    for o in card.get("outliers") or []:
        lines.append(f"- {o['metric']}: pctl {o['percentile']} rank {o['rank']}")
    if not card.get("outliers"):
        lines.append("- none")
    conf = card.get("confidence") or {}
    lines += [
        "",
        "CONFIDENCE",
        conf.get("explain") or "",
        f"Missing: {', '.join(card.get('missing_peer_data') or [])}",
        "",
        "RULE",
        "Every conclusion references peer, history, or sector ranking before judgement.",
    ]
    return {
        "ticker": card["ticker"],
        "found": True,
        "pil_version": PIL_VERSION,
        "text": "\n".join(lines),
        "scorecard": card,
        "commentary": comment,
    }
