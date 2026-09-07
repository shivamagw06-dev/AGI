"""IAX — Institutional Answer Experience enrichment (no engine name exposure)."""

from __future__ import annotations

import html
import re
from typing import Any

from app.ui.sanitize import pick_label, pick_number, public_source, scrub, scrub_text

_STANCE_BULL_RE = re.compile(r"\b(bullish|overweight|upgrade|buy)\b", re.I)
_STANCE_BEAR_RE = re.compile(r"\b(bearish|underweight|downgrade|sell)\b", re.I)
_CAUTIOUS_RE = re.compile(
    r"weak growth|slow(?:er)? growth|slower deal|macro challenge|headwind|"
    r"demand weakness|muted|soft demand|productivity (?:pressure|demands)|"
    r"\bpressure\b|\bunderweight\b|\bdowngrade\b",
    re.I,
)
_CONSTRUCTIVE_RE = re.compile(
    r"\bupgrade\b|\boverweight\b|acceleration|strong demand|reacceleration|\bbeats?\b",
    re.I,
)


def normalize_stance(label: Any = None) -> str:
    """Return Bullish / Neutral / Bearish — never treat field names like bull_case as stance."""
    if label is None or label == "":
        return "Neutral"
    if isinstance(label, dict):
        return stance_from_historical(label)
    t = str(label).strip()
    # Stringified HistoricalView / object dumps must not be parsed via substring "bull".
    if t.startswith("{") or "document_id" in t or "bull_case" in t or "bear_case" in t:
        thesis_m = re.search(r"['\"]thesis['\"]\s*:\s*['\"](.+?)['\"]", t)
        blob = thesis_m.group(1) if thesis_m else t
        return stance_from_text(html.unescape(blob))
    low = t.lower()
    if low in {"bull", "bullish", "overweight", "buy", "strong buy", "strongly bullish"}:
        return "Bullish"
    if low in {"bear", "bearish", "underweight", "sell", "strong sell", "strongly bearish"}:
        return "Bearish"
    if low in {"neutral", "hold", "market perform", "equal weight"}:
        return "Neutral"
    if _STANCE_BEAR_RE.search(t) and not _STANCE_BULL_RE.search(t):
        return "Bearish"
    if _STANCE_BULL_RE.search(t) and not _STANCE_BEAR_RE.search(t):
        return "Bullish"
    return stance_from_text(t)


def stance_from_text(text: str | None) -> str:
    blob = html.unescape(text or "")
    if not blob.strip():
        return "Neutral"
    cautious = bool(_CAUTIOUS_RE.search(blob))
    constructive = bool(_CONSTRUCTIVE_RE.search(blob))
    if cautious and not constructive:
        return "Bearish"
    if constructive and not cautious:
        return "Bullish"
    return "Neutral"


def stance_from_historical(view: dict[str, Any] | None) -> str:
    """Infer institutional stance from a HistoricalView-shaped dict / thesis text."""
    if not isinstance(view, dict):
        return "Neutral"
    bulls = [str(x) for x in (view.get("bull_case") or []) if x]
    bears = [str(x) for x in (view.get("bear_case") or []) if x]
    if bears and not bulls:
        return "Bearish"
    if bulls and not bears:
        return "Bullish"
    blob = " ".join(
        [
            str(view.get("thesis") or ""),
            " ".join(bulls),
            " ".join(bears),
        ]
    )
    return stance_from_text(blob)


def synthesize_thesis_points(thesis: str | None) -> dict[str, list[str]]:
    """Build bull/bear/risk/catalyst bullets from free-text sector notes when structured cases are empty."""
    text = html.unescape(re.sub(r"\s+", " ", thesis or "")).strip()
    if not text:
        return {"bull_case": [], "bear_case": [], "risks": [], "catalysts": []}
    parts = [p.strip(" -•\t") for p in re.split(r"(?<=[.:;])\s+|\n+", text) if p and len(p.strip()) > 25]
    bull: list[str] = []
    bear: list[str] = []
    risks: list[str] = []
    catalysts: list[str] = []
    for part in parts:
        low = part.lower()
        if any(w in low for w in ("risk", "concern", "freeze", "cut")):
            risks.append(part[:220])
        if any(w in low for w in ("catalyst", "guidance", "trigger", "reaccel")):
            catalysts.append(part[:220])
        if _CAUTIOUS_RE.search(part) or any(
            w in low for w in ("muted", "weakness", "challenge", "slower", "soft")
        ):
            bear.append(part[:220])
        elif _CONSTRUCTIVE_RE.search(part) or any(
            w in low for w in ("improve", "pipeline", "intact", "resilien", "better performance")
        ):
            bull.append(part[:220])
    return {
        "bull_case": _uniq_points(bull)[:4],
        "bear_case": _uniq_points(bear)[:4],
        "risks": _uniq_points(risks)[:4],
        "catalysts": _uniq_points(catalysts)[:4],
    }


def _uniq_points(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def clean_thesis_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("thesis") or value.get("summary") or ""
    text = html.unescape(str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def flatten_house_view(house: dict[str, Any] | None) -> dict[str, Any]:
    """Expose thesis / cases / stance at top-level for IAX cards."""
    if not isinstance(house, dict):
        return {}
    out = dict(house)
    cv = house.get("current_view")
    if isinstance(cv, dict):
        thesis = clean_thesis_text(cv.get("thesis") or "")
        out["thesis"] = thesis or out.get("thesis") or ""
        out["summary"] = out.get("thesis") or ""
        out["bull_case"] = [str(x) for x in (cv.get("bull_case") or out.get("bull_case") or []) if x]
        out["bear_case"] = [str(x) for x in (cv.get("bear_case") or out.get("bear_case") or []) if x]
        out.setdefault("valuation", cv.get("valuation") or "")
        out.setdefault("target_prices", list(cv.get("target_prices") or []))
        # Prefer thesis-derived stance over any leaked object/label.
        out["stance"] = stance_from_historical(
            {
                "thesis": out.get("thesis"),
                "bull_case": out.get("bull_case"),
                "bear_case": out.get("bear_case"),
            }
        )
        out["label"] = out["stance"]
        out["current_view_label"] = out["stance"]
    elif isinstance(cv, str):
        out["stance"] = normalize_stance(house.get("stance") or cv)
        out["label"] = out["stance"]
        out["current_view_label"] = out["stance"]
    else:
        if out.get("thesis"):
            out["thesis"] = clean_thesis_text(out.get("thesis")) or ""
            out["stance"] = stance_from_text(out.get("thesis"))
        else:
            out["stance"] = normalize_stance(house.get("stance") or house.get("label"))
        out["label"] = out["stance"]
        out["current_view_label"] = out["stance"]
    if out.get("confidence") is None and house.get("research_confidence") is not None:
        out["confidence"] = house.get("research_confidence")
    # Never leave nested objects in fields the UI may stringify.
    if not isinstance(out.get("stance"), str):
        out["stance"] = "Neutral"
        out["label"] = "Neutral"
        out["current_view_label"] = "Neutral"
    return out


def evidence_items(raw_items: list[Any], *, default_type: str = "research") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in raw_items or []:
        if isinstance(item, str):
            out.append(
                {
                    "id": item,
                    "title": scrub_text(item),
                    "source": "institutional",
                    "type": default_type,
                    "date": None,
                    "reliability": "medium",
                    "summary": scrub_text(item),
                    "confidence": None,
                    "href": None,
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        dtype = str(item.get("document_type") or item.get("type") or default_type)
        raw_id = item.get("id") or item.get("document_id") or item.get("title")
        out.append(
            {
                "id": scrub_text(str(raw_id)) if raw_id is not None else None,
                "title": scrub_text(item.get("title") or item.get("id")),
                "source": public_source(item.get("source") or item.get("broker") or "knowledge"),
                "type": dtype,
                "date": item.get("date") or item.get("published_at") or item.get("as_of"),
                "reliability": item.get("reliability") or _reliability(dtype),
                "summary": scrub_text(item.get("snippet") or item.get("summary") or item.get("title")),
                "confidence": item.get("confidence") or item.get("score"),
                "href": item.get("href") or item.get("url"),
                "tickers": [
                    str(t).upper()
                    for t in (item.get("tickers") or [])
                    if str(t).upper().endswith("BANK")
                    or (
                        2 <= len(str(t)) <= 12
                        and str(t).upper().isalpha()
                        and str(t).upper()
                        not in {
                            "SERVICES",
                            "GLOBAL",
                            "UPDATE",
                            "OUTLOOK",
                            "REVIEW",
                            "EARNINGS",
                            "CONTINUES",
                            "RESEARCH",
                            "INDIA",
                            "INDIAN",
                            "MARKET",
                            "SECTOR",
                            "GROWTH",
                            "WEEK",
                            "NOTE",
                            "AMP",
                            "HIS",
                            "IMPLICATIONS",
                            "TAKEAWAYS",
                            "PRESSURE",
                            "DEMAND",
                            "MACRO",
                        }
                    )
                ][:8],
            }
        )
    return out[:20]


def _reliability(dtype: str) -> str:
    d = dtype.lower()
    if "agi" in d or "filing" in d:
        return "high"
    if "broker" in d:
        return "medium"
    if "news" in d:
        return "medium"
    return "medium"


def whats_changed(
    *,
    house: dict[str, Any] | None,
    prior_house: dict[str, Any] | None = None,
    conf: float | None = None,
    prior_conf: float | None = None,
    thesis: str | None = None,
) -> dict[str, Any]:
    """Compare current institutional view vs previous — never make users hunt for deltas."""
    house = flatten_house_view(house)
    prior = flatten_house_view(prior_house)
    changes: list[dict[str, str]] = []

    cur_stance = normalize_stance(
        house.get("stance") or house.get("current_view_label") or house.get("label")
    )
    prior_stance = normalize_stance(
        prior.get("stance") or prior.get("current_view_label") or prior.get("label")
    )
    if prior and cur_stance != prior_stance:
        changes.append(
            {
                "kind": "stance",
                "label": "House view changed",
                "detail": f"{prior_stance} → {cur_stance}",
            }
        )

    for item in house.get("thesis_evolution") or house.get("changed_assumptions") or []:
        changes.append({"kind": "research", "label": "Thesis / assumption update", "detail": scrub_text(str(item)) or ""})

    for item in house.get("failed_assumptions") or []:
        changes.append({"kind": "risk", "label": "Assumption failed / new risk", "detail": scrub_text(str(item)) or ""})

    for item in house.get("catalysts_occurred") or []:
        changes.append({"kind": "catalyst", "label": "Catalyst update", "detail": scrub_text(str(item)) or ""})

    if conf is not None and prior_conf is not None:
        try:
            delta = float(conf) - float(prior_conf)
            if abs(delta) >= 0.05:
                direction = "up" if delta > 0 else "down"
                changes.append(
                    {
                        "kind": "confidence",
                        "label": f"Confidence moved {direction}",
                        "detail": f"{prior_conf} → {conf}",
                    }
                )
        except (TypeError, ValueError):
            pass

    if thesis and prior.get("thesis") and scrub_text(thesis) != scrub_text(prior.get("thesis")):
        changes.append(
            {
                "kind": "valuation",
                "label": "Investment thesis revised",
                "detail": "Current thesis differs from the previous AGI view.",
            }
        )

    # Soft buckets for UI sections
    buckets = {
        "new_risks": [c["detail"] for c in changes if c["kind"] == "risk"][:6],
        "new_catalysts": [c["detail"] for c in changes if c["kind"] == "catalyst"][:6],
        "changed_valuation": [c["detail"] for c in changes if c["kind"] == "valuation"][:4],
        "changed_macro": [c["detail"] for c in changes if c["kind"] == "macro"][:4],
        "changed_sentiment": [c["detail"] for c in changes if c["kind"] == "sentiment"][:4],
        "changed_research": [c["detail"] for c in changes if c["kind"] in {"research", "stance"}][:6],
        "changed_confidence": [c["detail"] for c in changes if c["kind"] == "confidence"][:4],
    }

    if not changes:
        changes.append(
            {
                "kind": "stable",
                "label": "No material change detected",
                "detail": "Current AGI view is consistent with the latest stored house view.",
            }
        )

    return {
        "summary": changes[0]["detail"] if changes else "Stable",
        "items": changes[:12],
        "buckets": buckets,
        "prior_stance": prior_stance if prior else None,
        "current_stance": cur_stance,
    }


def _public_explanation(value: Any, fallback: str) -> str:
    if isinstance(value, dict):
        for key in ("summary", "explanation", "note", "label", "status"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return scrub_text(nested) or fallback
        return fallback
    if isinstance(value, str) and value.strip():
        return scrub_text(value) or fallback
    return fallback


def market_intelligence_summary(company_ws: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Public market/business/risk/momentum summaries — never expose engine codes."""
    ws = company_ws or {}
    mapping = [
        ("Market", ws.get("macro") or ws.get("market_regime"), "regime", "Market regime context"),
        ("Business", ws.get("fundamental") or ws.get("fundamentals"), "score", "Business / fundamental quality"),
        ("Risk", ws.get("risk") or ws.get("market_risk"), "risk_level", "Market and idiosyncratic risk"),
        ("Momentum", ws.get("trend") or ws.get("technical"), "label", "Price / trend momentum"),
        ("Events", ws.get("events"), "label", "Near-term event risk"),
        ("Sentiment", ws.get("sentiment"), "label", "Sentiment backdrop"),
        ("Volatility", ws.get("volatility"), "label", "Volatility regime"),
    ]
    out: list[dict[str, Any]] = []
    for name, state, key, fallback in mapping:
        st = scrub(state) if isinstance(state, dict) else None
        status = pick_label(st, key, "label", "status", "regime", "risk_level") or ("Available" if st else "Limited")
        conf = pick_number(st, "confidence")
        explanation = _public_explanation(st, fallback) if st else fallback
        out.append(
            {
                "dimension": name,
                "status": scrub_text(str(status)),
                "explanation": explanation,
                "confidence": conf,
            }
        )
    return out


def related_ideas(
    *,
    related_companies: list[str],
    related_sectors: list[str],
    related_themes: list[str],
    stance: str | None,
) -> dict[str, Any]:
    similar = related_companies[:4]
    opposite_note = "Explore peers with a contrasting house view in the same sector."
    return {
        "similar_thesis": similar,
        "opposite_thesis": related_companies[4:8] or [],
        "same_sector": related_sectors[:6],
        "same_macro_exposure": related_themes[:6],
        "same_valuation_style": [],
        "notes": [opposite_note] if stance else [],
    }


def build_charts(
    *,
    ticker: str | None,
    predictions: list[dict[str, Any]] | None = None,
    timeline: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Chart descriptors only — values filled when series exist; never invent prices."""
    charts: list[dict[str, Any]] = []
    if ticker:
        charts.append(
            {
                "id": "research_timeline",
                "title": f"{ticker} research timeline",
                "kind": "timeline",
                "answers": "When did AGI and the market update the view?",
                "points": [
                    {
                        "as_of": p.get("as_of") or p.get("date") or p.get("published_at"),
                        "label": p.get("title") or p.get("label") or p.get("type"),
                    }
                    for p in (timeline or [])[:12]
                    if isinstance(p, dict)
                ],
            }
        )
    if predictions:
        charts.append(
            {
                "id": "prediction_timeline",
                "title": "Prediction timeline",
                "kind": "timeline",
                "answers": "How have AGI predictions evolved?",
                "points": [
                    {
                        "as_of": p.get("predicted_at") or p.get("as_of"),
                        "label": p.get("thesis") or p.get("ticker") or "Prediction",
                        "value": p.get("target") or p.get("expected_return"),
                    }
                    for p in predictions[:12]
                    if isinstance(p, dict)
                ],
            }
        )
    return charts


def enrich_timeline(events: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in events or []:
        if isinstance(e, str):
            out.append({"as_of": None, "type": "note", "title": scrub_text(e), "source": "knowledge"})
            continue
        if not isinstance(e, dict):
            continue
        out.append(
            {
                "as_of": e.get("as_of") or e.get("date") or e.get("published_at"),
                "type": e.get("type") or e.get("kind") or e.get("document_type") or "event",
                "title": scrub_text(e.get("title") or e.get("label") or e.get("summary")),
                "summary": scrub_text(e.get("summary") or e.get("snippet")),
                "source": public_source(e.get("source")),
                "tickers": e.get("tickers") or [],
            }
        )
    # newest first when dates present
    out.sort(key=lambda x: str(x.get("as_of") or ""), reverse=True)
    return out[:40]


def knowledge_graph_view(graph: dict[str, Any] | None, ticker: str | None) -> dict[str, Any]:
    g = scrub(graph) if graph else {}
    if not isinstance(g, dict):
        g = {}
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []
    buckets: dict[str, list[str]] = {
        "company": [],
        "suppliers": [],
        "customers": [],
        "competitors": [],
        "industry": [],
        "sector": [],
        "macro_themes": [],
        "commodities": [],
        "currencies": [],
        "related_companies": [],
    }
    for n in nodes:
        if not isinstance(n, dict):
            continue
        kind = str(n.get("kind") or n.get("type") or "").lower()
        label = str(n.get("label") or n.get("node_id") or "")
        if not label:
            continue
        if kind in {"company", "ticker"}:
            buckets["related_companies"].append(label)
        elif kind in {"theme", "macro"}:
            buckets["macro_themes"].append(label)
        elif kind in {"industry"}:
            buckets["industry"].append(label)
        elif kind in {"sector"}:
            buckets["sector"].append(label)
        elif kind in {"commodity"}:
            buckets["commodities"].append(label)
        elif kind in {"currency", "fx"}:
            buckets["currencies"].append(label)
        elif kind in {"supplier"}:
            buckets["suppliers"].append(label)
        elif kind in {"customer"}:
            buckets["customers"].append(label)
        elif kind in {"competitor"}:
            buckets["competitors"].append(label)
    for e in edges:
        if not isinstance(e, dict):
            continue
        rel = str(e.get("relation") or e.get("type") or "").upper()
        tgt = str(e.get("to") or e.get("target") or e.get("label") or "")
        if "COMPET" in rel and tgt:
            buckets["competitors"].append(tgt)
        if "SUPPL" in rel and tgt:
            buckets["suppliers"].append(tgt)
        if "CUSTOM" in rel and tgt:
            buckets["customers"].append(tgt)
    # de-dupe
    for k, vals in list(buckets.items()):
        buckets[k] = sorted({v for v in vals if v and v.upper() != (ticker or "").upper()})[:12]
    return {
        "center": ticker,
        "buckets": buckets,
        "nodes": nodes[:40] if isinstance(nodes, list) else [],
        "edges": edges[:60] if isinstance(edges, list) else [],
    }


def house_view_card(house: dict[str, Any] | None, conf: float | None) -> dict[str, Any]:
    house = flatten_house_view(house)
    stance = normalize_stance(
        house.get("stance")
        or house.get("current_view_label")
        or house.get("label")
        or (house.get("current_view") if isinstance(house.get("current_view"), str) else None)
    )
    conf_val = conf if conf is not None else house.get("confidence")
    return {
        "stance": stance,
        "bullish": stance == "Bullish",
        "neutral": stance == "Neutral",
        "bearish": stance == "Bearish",
        "confidence": conf_val,
        "investment_horizon": house.get("horizon") or house.get("investment_horizon") or "medium-term",
        "conviction": house.get("conviction") or _conviction(conf_val if isinstance(conf_val, (int, float)) else conf),
        "change_since_last_update": house.get("change_since_last_update")
        or (house.get("thesis_evolution") or [None])[0],
        "label": stance,
    }


def _conviction(conf: float | None) -> str:
    if conf is None:
        return "forming"
    c = float(conf)
    if c > 1:
        c = c / 100.0
    if c >= 0.75:
        return "high"
    if c >= 0.5:
        return "moderate"
    return "low"


def research_panel(
    *,
    agi: list[dict[str, Any]],
    broker: list[dict[str, Any]],
    filings: list[dict[str, Any]],
    earnings: list[dict[str, Any]],
    historical: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "latest_agi_research": agi[:8],
        "most_relevant_research": agi[:6] or broker[:6],
        "historical_research": historical[:8],
        "latest_broker_research": broker[:8],
        "latest_filings": filings[:6],
        "latest_earnings": earnings[:6],
    }
