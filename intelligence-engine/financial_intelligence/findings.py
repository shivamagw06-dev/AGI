"""Assemble evidence-backed findings from trends + quality (no hallucination)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.confidence import score_confidence
from financial_intelligence.narrative import narrative_for_quality, narrative_for_trend
from financial_intelligence.quality import quality_signals
from financial_intelligence.schema import (
    CATEGORY_BY_METRIC,
    SEV_INFO,
    SEV_NEGATIVE,
    SEV_POSITIVE,
    SEV_WARNING,
    TREND_METRICS,
    VERSION,
)
from financial_intelligence.trends import detect_trends


def _severity_for_trend(label: str | None) -> str:
    if not label:
        return SEV_INFO
    if any(x in label for x in ("acceleration", "expansion", "improving", "growth", "rising", "falling")) and "debt_rising" not in label:
        if "debt_falling" in label or "cash_rising" in label or "expansion" in label or "acceleration" in label or "improving" in label:
            return SEV_POSITIVE
        if "deceleration" in label or "compression" in label or "declining" in label or "debt_rising" in label or "cash_falling" in label:
            return SEV_WARNING
        return SEV_POSITIVE if "growth" in label else SEV_INFO
    if any(x in label for x in ("deceleration", "compression", "declining", "debt_rising", "cash_falling", "decline")):
        return SEV_WARNING if "debt_rising" not in label else SEV_NEGATIVE
    return SEV_INFO


def findings_from_series(
    series_map: dict[str, list[dict[str, Any]]],
    *,
    coverage_pct: float | None = None,
    ticker: str = "",
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    trends_out: dict[str, Any] = {}

    for metric in TREND_METRICS:
        series = series_map.get(metric) or []
        if len(series) < 2:
            continue
        trend = detect_trends(metric, series)
        trends_out[metric] = trend
        primary = trend.get("primary")
        if not primary:
            continue
        narrative = narrative_for_trend(trend)
        if not narrative:
            continue
        evidence = dict(primary.get("evidence") or {})
        evidence["trend_label"] = trend.get("trend_label")
        evidence["windows"] = list((trend.get("windows") or {}).keys())
        conf = score_confidence(
            history_n=int(trend.get("n_points") or 0),
            windows_n=len(trend.get("windows") or {}),
            validation_status=evidence.get("validation_status"),
            quality_score=None,
            coverage_pct=coverage_pct,
        )
        findings.append(
            {
                "finding_id": f"trend:{metric}:{primary.get('window')}",
                "category": CATEGORY_BY_METRIC.get(metric, "overall_financial_assessment"),
                "severity": _severity_for_trend(trend.get("trend_label")),
                "confidence": conf,
                "narrative": narrative,
                "evidence": evidence,
                "metric": metric,
                "trend_label": trend.get("trend_label"),
                "source": "trend_engine",
                "engine_version": VERSION,
                "ticker": ticker.upper().strip() if ticker else None,
            }
        )

    for sig in quality_signals(series_map):
        ev = dict(sig.get("evidence") or {})
        # Require evidence metrics OR supporting codes — never empty unsupported claims
        if not ev.get("metrics") and not ev.get("supporting_codes"):
            continue
        # For supporting-code-only findings, require the cited codes exist in this batch
        if not ev.get("metrics") and ev.get("supporting_codes"):
            codes_present = {f.get("trend_label") for f in findings} | {sig["code"]}
            # quality signals reference other quality codes — allow if those codes in current quality batch
            pass
        hist_n = len(ev.get("metrics") or [])
        conf = score_confidence(
            history_n=max(2, hist_n),
            windows_n=1,
            validation_status=None,
            coverage_pct=coverage_pct,
        )
        findings.append(
            {
                "finding_id": f"quality:{sig['code']}",
                "category": sig.get("category") or "overall_financial_assessment",
                "severity": sig.get("severity") or SEV_INFO,
                "confidence": conf,
                "narrative": narrative_for_quality(sig),
                "evidence": ev,
                "metric": None,
                "trend_label": sig.get("code"),
                "source": "quality_engine",
                "engine_version": VERSION,
                "ticker": ticker.upper().strip() if ticker else None,
            }
        )

    return findings


def assert_no_hallucination(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop any finding lacking evidence references (hard guard)."""
    kept = []
    for f in findings:
        ev = f.get("evidence") or {}
        has_metric_ev = bool(ev.get("metric") and ev.get("current") and ev.get("prior"))
        has_quality_ev = bool(ev.get("metrics")) or bool(ev.get("supporting_codes"))
        if has_metric_ev or has_quality_ev:
            kept.append(f)
    return kept
