"""Continuous learning — material MKOs generate institutional learning events."""

from __future__ import annotations

from continuous_macro_knowledge.schema import LearningEvent, MacroKnowledgeObject


def generate_learning(mko: MacroKnowledgeObject, *, materiality: dict) -> LearningEvent | None:
    if not materiality.get("learn") or materiality.get("tier") == "Ignore":
        return None

    delta = materiality.get("delta")
    topic = f"{mko.country} {mko.indicator} ({mko.release_date})"

    if "repo" in mko.indicator.lower() or "federal funds" in mko.indicator.lower():
        direction = "cut" if (delta or 0) < 0 else "hike"
        bps = abs(float(delta or 0)) * 100
        observation = f"{mko.indicator} {direction} of {bps:.0f} bps to {mko.current_value}."
        learning = (
            f"Material monetary policy change ({direction}). "
            "Transmission channels (banks, duration, FX) require institutional refresh."
        )
        guidance = (
            "Increase weight of rate-sensitive sector / bank NIM scenarios; "
            "trigger forecast refresh for financials and rate-sensitive cyclicals."
        )
        forecast_refresh = True
    elif "cpi" in mko.indicator.lower() or "wpi" in mko.indicator.lower():
        surprise = mko.normalized.get("surprise_vs_consensus")
        observation = (
            f"{mko.indicator} printed {mko.current_value}{mko.unit} "
            f"(prev {mko.previous_value}, consensus {mko.consensus}, surprise {surprise})."
        )
        learning = "Inflation print carries material information for real rates and policy path."
        guidance = "Refresh inflation → RBI path → banks / discretionary demand scenarios."
        forecast_refresh = True
    elif "gdp" in mko.indicator.lower() or "gva" in mko.indicator.lower() or "iip" in mko.indicator.lower():
        observation = f"{mko.indicator} at {mko.current_value}{mko.unit} (prev {mko.previous_value})."
        learning = "Growth impulse update — sector earnings sensitivity may shift."
        guidance = "Revisit growth-sensitive sector outlooks; keep Base case anchored to official print."
        forecast_refresh = True
    elif "fiscal" in mko.indicator.lower() or "gst" in mko.indicator.lower() or "budget" in mko.indicator.lower():
        observation = f"{mko.indicator} update from {mko.source}."
        learning = "Fiscal path update affects borrowing, duration and state-linked demand."
        guidance = "Monitor gilt supply / deficit path for financial market scenarios."
        forecast_refresh = materiality.get("tier") in {"High", "Critical"}
    else:
        observation = f"{mko.indicator} materiality={materiality.get('tier')} score={materiality.get('score')}."
        learning = materiality.get("reason") or "Material macro update recorded."
        guidance = "Incorporate into Macro Knowledge Store; refresh dependent research only if High+."
        forecast_refresh = materiality.get("tier") in {"High", "Critical"}

    return LearningEvent(
        mko_id=mko.mko_id,
        topic=topic,
        observation=observation,
        learning=learning,
        future_guidance=guidance,
        materiality_tier=mko.materiality_tier,
        category=mko.category,
        indicator=mko.indicator,
        country=mko.country,
        forecast_refresh_hint=forecast_refresh,
        history_rewritten=False,
    )
