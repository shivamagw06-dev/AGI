"""Evidence fusion helpers — observed / derived / inferred + conflicts."""

from __future__ import annotations

from typing import Any, Optional

from intelligence_fusion_answer_composer.models import CONSENSUS_PROVIDERS, EnginePack


_MISSING_PHRASES = (
    "no historical conclusion",
    "holds no historical",
    "unavailable",
    "not enough",
    "insufficient",
    "hvie_empty",
    "no observations",
)


def as_pack(raw: Any) -> Optional[EnginePack]:
    """Normalise a ProviderResult / dict into EnginePack. Never crash on strings."""
    if raw is None:
        return None
    if isinstance(raw, EnginePack):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        return EnginePack(
            provider_id="unknown",
            summary=text,
            empty=False,
            ok=True,
            confidence=0.4,
        )
    if not isinstance(raw, dict):
        # duck-typed ProviderResult
        try:
            pid = str(getattr(raw, "provider_id", "") or "")
            summary = str(getattr(raw, "summary", "") or "")
            why = list(getattr(raw, "why", None) or [])
            conf = float(getattr(raw, "confidence", 0.0) or 0.0)
            empty = bool(getattr(raw, "empty", not bool(summary)))
            ok = bool(getattr(raw, "ok", True))
            evidence = list(getattr(raw, "evidence", None) or [])
            facts = list(getattr(raw, "facts", None) or [])
            raw_dict = getattr(raw, "raw", None)
            if not isinstance(raw_dict, dict):
                raw_dict = {}
            expl = {}
            for ev in evidence:
                if isinstance(ev, dict) and isinstance(ev.get("explainability"), dict):
                    expl = ev["explainability"]
                    break
            return EnginePack(
                provider_id=pid,
                summary=summary,
                why=[str(w) for w in why if w],
                confidence=conf,
                explainability=_norm_expl(expl),
                facts=[f for f in facts if isinstance(f, dict)],
                raw=raw_dict,
                empty=empty or not summary,
                ok=ok,
            )
        except Exception:
            return None

    pid = str(raw.get("provider_id") or raw.get("id") or "")
    summary = raw.get("summary")
    if not isinstance(summary, str):
        summary = str(summary or "")
    why_raw = raw.get("why") or []
    if isinstance(why_raw, str):
        why = [why_raw]
    elif isinstance(why_raw, list):
        why = [str(w) for w in why_raw if w]
    else:
        why = []
    expl = raw.get("explainability")
    if not isinstance(expl, dict):
        for ev in raw.get("evidence") or []:
            if isinstance(ev, dict) and isinstance(ev.get("explainability"), dict):
                expl = ev["explainability"]
                break
        else:
            expl = {}
    facts = raw.get("facts") or []
    if not isinstance(facts, list):
        facts = []
    raw_body = raw.get("raw")
    if not isinstance(raw_body, dict):
        raw_body = {}
    try:
        conf = float(raw.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    empty = bool(raw.get("empty", not bool(summary.strip())))
    return EnginePack(
        provider_id=pid,
        summary=summary.strip(),
        why=why,
        confidence=conf,
        explainability=_norm_expl(expl),
        facts=[f for f in facts if isinstance(f, dict)],
        raw=raw_body,
        empty=empty,
        ok=bool(raw.get("ok", True)),
    )


def _norm_expl(expl: Any) -> dict[str, list[str]]:
    if not isinstance(expl, dict):
        return {"observed": [], "derived": [], "inferred": []}
    out: dict[str, list[str]] = {"observed": [], "derived": [], "inferred": []}
    for key in out:
        val = expl.get(key) or []
        if isinstance(val, str):
            out[key] = [val] if val.strip() else []
        elif isinstance(val, list):
            out[key] = [str(v) for v in val if v][:8]
    return out


def merge_explainability(packs: list[EnginePack]) -> dict[str, list[str]]:
    merged = {"observed": [], "derived": [], "inferred": []}
    for pack in packs:
        expl = pack.explainability or {}
        for key in merged:
            for item in expl.get(key) or []:
                if item and item not in merged[key]:
                    merged[key].append(item)
        # Promote why lines into derived when explainability is empty.
        if not any(expl.values()) and pack.why:
            for line in pack.why[:3]:
                if line not in merged["derived"]:
                    merged["derived"].append(line)
    for key in merged:
        merged[key] = merged[key][:12]
    return merged


def missing_data_message(provider_id: str, summary: str = "", why: Optional[list[str]] = None) -> Optional[str]:
    """Rewrite sparse/unavailable engine output into an institutional explanation."""
    blob = " ".join([summary or "", " ".join(why or [])]).lower()
    if not any(p in blob for p in _MISSING_PHRASES) and summary.strip():
        return None
    if provider_id == "historical_valuation_intelligence" or "historical" in blob:
        return (
            "Historical valuation analysis is currently unavailable because reconstructed "
            "warehouse history has not yet reached the required observation threshold. "
            "Current valuation analysis remains available from UVE / Valuation Terminal."
        )
    if provider_id == "forecast_intelligence_engine":
        return (
            "Forward outlook detail is limited because forecast evidence in the warehouse "
            "is incomplete for this company. Supporting business and valuation context is shown below."
        )
    if provider_id == "macro_intelligence_engine":
        return (
            "Macro transmission detail is limited for this query. Sector-level context from "
            "Market Intelligence is used where available."
        )
    if not summary.strip():
        return explain_missing_intelligence(provider_id)
    return None


def is_consensus_headline(text: str) -> bool:
    low = (text or "").lower()
    return any(
        k in low
        for k in (
            "capital iq market consensus",
            "consensus target",
            "analysts covering",
            "implied upside",
            "broker recommendation split",
            "sell-side",
        )
    )


def is_low_quality_lead(pack: EnginePack) -> bool:
    """Skip raw dumps / risk-only blobs when richer institutional packs exist."""
    s = (pack.summary or "").strip()
    if not s:
        return True
    # Raw dict / JSON-ish engine leakage.
    if s.startswith("{") or s.startswith("[") or "': {" in s or '": {' in s:
        return True
    low = s.lower()
    # Generic / wrong-company template leads — never headline.
    if any(
        p in low
        for p in (
            "for unknown",
            "for commodity",
            "business type: unknown",
            "based on retrieved evidence for the subject",
            "indian stock market q&a",
            "no historical conclusion",
            "holds no historical",
        )
    ):
        return True
    # Sparse valuation dumps (Current PE / None tables) must not headline moat answers.
    if low.startswith("current pe") and ("none" in low or len(s) < 80):
        return True
    if low.count("none") >= 3 and any(k in low for k in ("percentile", "median", "regime")):
        return True
    if pack.provider_id == "forecast_intelligence_engine":
        outlookish = any(
            k in low
            for k in (
                "outlook",
                "base case",
                "bull",
                "bear",
                "forecast",
                "scenario",
                "growth",
                "revenue",
                "margin",
                "3–5",
                "3-5",
            )
        )
        riskish = any(k in low for k in ("risk", "monitor", "watch", "downside"))
        if riskish and not outlookish:
            return True
        if "risk_register" in low or "key_risks" in low:
            return True
    # Sparse VPAE model labels should not headline attribution answers.
    if pack.provider_id == "valuation_policy_engine" and low.startswith("primary valuation model"):
        return True
    return False


def explain_missing_intelligence(provider_id: str, *, section: str = "") -> str:
    """Institutional phrasing when an engine has no usable content."""
    label = {
        "historical_valuation_intelligence": (
            "Historical valuation intelligence is currently unavailable because "
            "reconstructed warehouse history has insufficient observations. "
            "Current valuation remains available where the unified valuation engine has coverage."
        ),
        "valuation_attribution_engine": (
            "Valuation attribution is unavailable because premium/discount drivers "
            "could not be reconstructed from warehouse observations."
        ),
        "forecast_intelligence_engine": (
            "Forward outlook intelligence is limited because forecast observations "
            "are incomplete for this question."
        ),
        "macro_intelligence_engine": (
            "Macro transmission context is limited for this question; company and "
            "sector intelligence remain available."
        ),
        "research_intelligence_engine": (
            "Institutional research memory did not return a usable dossier section "
            "for this question."
        ),
        "business_intelligence": (
            "Business-model intelligence is limited for this entity; identity and "
            "financial layers remain available where covered."
        ),
    }.get(provider_id)
    if label:
        return label
    sec = f" ({section})" if section else ""
    return (
        f"This intelligence layer{sec} is currently unavailable because warehouse "
        "or engine coverage is insufficient. Other sections remain available."
    )


def sanitize_summary(text: str, *, max_len: int = 480) -> str:
    """Strip raw structure dumps; keep first institutional prose paragraph."""
    s = (text or "").strip()
    if not s:
        return ""
    if s.startswith("{") or s.startswith("["):
        return ""
    # Drop trailing dict blobs accidentally appended to prose.
    for marker in (" {'", ' {"', "\n{", "\n["):
        if marker in s:
            s = s.split(marker, 1)[0].strip()
    line = s.split("\n")[0].strip()
    if len(line) > max_len:
        line = line[: max_len - 1].rstrip() + "…"
    return line


def pick_lead(packs_by_id: dict[str, EnginePack], order: list[str]) -> Optional[EnginePack]:
    """First non-empty institutional pack in priority order; never CapIQ consensus first."""
    fallback: Optional[EnginePack] = None
    for pid in order:
        if pid in CONSENSUS_PROVIDERS:
            continue
        pack = packs_by_id.get(pid)
        if not pack or pack.empty or not pack.summary:
            continue
        if is_consensus_headline(pack.summary) and pid in CONSENSUS_PROVIDERS:
            continue
        if is_consensus_headline(pack.summary) and pid not in {
            "research_intelligence_engine",
            "forecast_intelligence_engine",
            "valuation_attribution_engine",
            "historical_valuation_intelligence",
            "unified_valuation_engine",
            "macro_intelligence_engine",
            "market_intelligence_engine",
            "hedge_fund_screens",
            "business_intelligence",
            "investment_intelligence",
        }:
            continue
        # Skip pure consensus prose even if mis-attributed.
        if is_consensus_headline(pack.summary) and pid in {
            "historical_intelligence",
            "valuation_terminal",
        }:
            continue
        if is_low_quality_lead(pack):
            if fallback is None:
                fallback = pack
            continue
        return pack
    if fallback is not None:
        return fallback
    # Last resort: any non-consensus pack with text.
    for pid, pack in packs_by_id.items():
        if pid in CONSENSUS_PROVIDERS or pack.empty or not pack.summary:
            continue
        if is_consensus_headline(pack.summary):
            continue
        return pack
    return None


def detect_conflicts(packs_by_id: dict[str, EnginePack]) -> list[dict[str, Any]]:
    """Lightweight conflict signals across engines — explain, never suppress."""
    conflicts: list[dict[str, Any]] = []
    hvie = packs_by_id.get("historical_valuation_intelligence")
    fie = packs_by_id.get("forecast_intelligence_engine")
    mie = packs_by_id.get("macro_intelligence_engine")
    uve = packs_by_id.get("unified_valuation_engine")

    def _blob(pack: Optional[EnginePack]) -> str:
        if not pack:
            return ""
        return " ".join([pack.summary] + list(pack.why or [])).lower()

    h, f, m, u = _blob(hvie), _blob(fie), _blob(mie), _blob(uve)
    cheap = any(k in h or k in u for k in ("cheap", "discount", "below median", "historically low"))
    expensive = any(k in h or k in u for k in ("expensive", "premium", "above median", "rich"))
    slowing = any(k in f for k in ("slow", "decelerat", "margin pressure", "bear", "weak"))
    tightening = any(k in m for k in ("tight", "rate hike", "rising rates", "hawkish", "liquidity stress"))

    if cheap and slowing:
        conflicts.append(
            {
                "stance": "Balanced",
                "reason": (
                    "Historically attractive valuation is offset by a more cautious business / "
                    "forecast outlook."
                ),
                "engines": ["historical_valuation_intelligence", "forecast_intelligence_engine"],
            }
        )
    if expensive and not slowing and not tightening:
        conflicts.append(
            {
                "stance": "Constructive but priced",
                "reason": (
                    "Valuation screens as expensive versus history or peers while forecast / macro "
                    "signals are not clearly offsetting that premium."
                ),
                "engines": [e for e in ("unified_valuation_engine", "historical_valuation_intelligence", "forecast_intelligence_engine") if e in packs_by_id],
            }
        )
    if cheap and tightening:
        conflicts.append(
            {
                "stance": "Balanced",
                "reason": (
                    "Attractive valuation context coincides with tighter macro / rate conditions — "
                    "the discount may reflect transmission risk rather than opportunity alone."
                ),
                "engines": ["historical_valuation_intelligence", "macro_intelligence_engine"],
            }
        )
    return conflicts


def aggregate_confidence(packs: list[EnginePack], *, primary: Optional[str] = None) -> dict[str, Any]:
    scored = [(p.provider_id, p.confidence) for p in packs if not p.empty and p.confidence]
    if not scored:
        return {"overall": None, "level": "Unknown", "by_engine": {}, "note": "No engine confidence available."}
    by_engine = {pid: round(c * 100.0, 1) if c <= 1 else round(c, 1) for pid, c in scored}
    # Weight primary higher.
    weights = []
    for pid, c in scored:
        w = 2.0 if primary and pid == primary else 1.0
        # CapIQ consensus never dominates overall confidence.
        if pid in CONSENSUS_PROVIDERS:
            w = 0.25
        weights.append((c if c <= 1 else c / 100.0, w))
    total_w = sum(w for _, w in weights) or 1.0
    overall = sum(c * w for c, w in weights) / total_w
    level = "High" if overall >= 0.75 else "Medium" if overall >= 0.55 else "Low"
    return {
        "overall": round(overall * 100.0, 1),
        "level": level,
        "by_engine": by_engine,
        "primary_engine": primary,
    }
