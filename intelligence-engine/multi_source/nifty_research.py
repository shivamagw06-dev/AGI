"""Nifty500 research adapter — AGI research scores via Node API or Supabase."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from multi_source.protocol import EvidenceItem

SOURCE_ID = "nifty_research"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _api_base() -> str:
    return (
        os.environ.get("AGIB_API_BASE_URL")
        or os.environ.get("NODE_API_BASE_URL")
        or "http://127.0.0.1:3001"
    ).rstrip("/")


def _http_get(url: str, *, timeout: float = 2.5) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _supabase_stock(symbol: str) -> dict[str, Any] | None:
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key or not symbol:
        return None
    try:
        # Current published run
        run_q = (
            f"{url}/rest/v1/nifty500_research_runs"
            f"?select=id,generated_at,published_at,run_name"
            f"&status=eq.published&is_current=eq.true&limit=1"
        )
        req = urllib.request.Request(
            run_q,
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            runs = json.loads(resp.read().decode("utf-8"))
        if not runs:
            return None
        run = runs[0]
        stock_q = (
            f"{url}/rest/v1/nifty500_stock_research"
            f"?select=symbol,overall_sentiment,agi_research_score,ai_confidence_percent,"
            f"research_summary,supporting_factors,risk_factors,key_observations,last_updated"
            f"&run_id=eq.{urllib.parse.quote(str(run['id']))}"
            f"&symbol=eq.{urllib.parse.quote(symbol)}&limit=1"
        )
        req2 = urllib.request.Request(
            stock_q,
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req2, timeout=2.5) as resp2:
            rows = json.loads(resp2.read().decode("utf-8"))
        if not rows:
            return None
        return {"run": run, "research": rows[0]}
    except Exception:
        return None


class NiftyResearchSource:
    source_id = SOURCE_ID

    def last_updated(self) -> str | None:
        return _now()

    def search(self, query: str, *, ticker: str | None = None) -> list[EvidenceItem]:
        hits: list[EvidenceItem] = []
        symbol = (ticker or "").upper().strip()

        # Prefer Node research API; fall back to direct Supabase
        payload = None
        if symbol:
            payload = _http_get(f"{_api_base()}/api/research/nifty500/stocks/{urllib.parse.quote(symbol)}")
            if not payload:
                payload = _supabase_stock(symbol)

        if payload and payload.get("research"):
            r = payload["research"]
            # Node publicRecord uses camelCase; Supabase raw uses snake_case
            score = r.get("agiResearchScore", r.get("agi_research_score"))
            sentiment = r.get("overallSentiment", r.get("overall_sentiment"))
            conf = r.get("aiConfidencePercent", r.get("ai_confidence_percent"))
            summary = r.get("researchSummary", r.get("research_summary")) or (
                f"{symbol} AGI research score {score}, sentiment {sentiment}."
            )
            supports = r.get("supportingFactors", r.get("supporting_factors")) or []
            risks = r.get("riskFactors", r.get("risk_factors")) or []
            if supports:
                summary = f"{summary} Supports: {', '.join(str(s) for s in supports[:3])}."
            if risks:
                summary = f"{summary} Risks: {', '.join(str(s) for s in risks[:3])}."

            hits.append(
                EvidenceItem(
                    source=SOURCE_ID,
                    entity=str(r.get("symbol") or symbol),
                    summary=str(summary)[:560],
                    confidence=min(float(conf or 60) / 100.0, 0.95) if conf is not None else 0.7,
                    timestamp=r.get("lastUpdated") or r.get("last_updated") or _now(),
                    score=float(score or 0),
                    freshness="research_run",
                    reason="Nifty500 institutional research score",
                    metrics={
                        "agi_research_score": score,
                        "overall_sentiment": sentiment,
                        "ai_confidence_percent": conf,
                    },
                    path=f"/research/nifty500/{symbol}" if symbol else "/research/nifty500",
                )
            )
            return hits

        # Leaderboard-style questions without a ticker
        q = (query or "").lower()
        if any(k in q for k in ("highest", "best", "top", "bullish", "quality", "momentum", "ranking")):
            summary_payload = _http_get(f"{_api_base()}/api/research/nifty500/summary")
            if summary_payload:
                for row in (summary_payload.get("topBullish") or [])[:5]:
                    hits.append(
                        EvidenceItem(
                            source=SOURCE_ID,
                            entity=str(row.get("symbol")),
                            summary=(
                                f"{row.get('symbol')}: score {row.get('agiResearchScore')}, "
                                f"sentiment {row.get('overallSentiment')}"
                            ),
                            confidence=0.65,
                            timestamp=row.get("lastUpdated") or _now(),
                            score=float(row.get("agiResearchScore") or 0),
                            freshness="research_run",
                            reason="Nifty500 top bullish ranking",
                            metrics={
                                "agi_research_score": row.get("agiResearchScore"),
                                "overall_sentiment": row.get("overallSentiment"),
                            },
                            path="/research/nifty500",
                        )
                    )
        return hits[:8]
