"""Entity validator — canonical entity, ticker, active/historical/merged/delisted."""

from __future__ import annotations

from typing import Any

# Ambiguous brand tokens that need clarification
AMBIGUOUS_BRANDS: dict[str, list[dict[str, str]]] = {
    "tata": [
        {"name": "TCS", "ticker": "TCS"},
        {"name": "Titan", "ticker": "TITAN"},
        {"name": "Tata Motors", "ticker": "TATAMOTORS"},
        {"name": "Tata Power", "ticker": "TATAPOWER"},
        {"name": "Tata Steel", "ticker": "TATASTEEL"},
    ],
    "hdfc": [
        {"name": "HDFC Bank", "ticker": "HDFCBANK"},
        {"name": "HDFC Life", "ticker": "HDFCLIFE"},
        {"name": "HDFC AMC", "ticker": "HDFCAMC"},
        {"name": "HDFC Limited (Historical)", "ticker": "HDFC"},
    ],
    "adani": [
        {"name": "Adani Enterprises", "ticker": "ADANIENT"},
        {"name": "Adani Ports", "ticker": "ADANIPORTS"},
        {"name": "Adani Power", "ticker": "ADANIPOWER"},
    ],
}


def _is_comparison(q: str) -> bool:
    return "compare" in q or " vs " in q or " versus " in q


def validate_entity(question: str, entity_resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    q = (question or "").strip().lower()
    ere = entity_resolution or {}
    # unwrap soft-slice nesting
    if "entity_resolution" in ere and isinstance(ere["entity_resolution"], dict):
        ere = ere["entity_resolution"]

    canonical = ere.get("canonical_entity") or {}
    needs_clarification = bool(ere.get("needs_clarification"))
    possible = list(ere.get("possible_matches") or [])
    research_blocked = bool(ere.get("research_blocked"))
    ticker = ere.get("ticker") or canonical.get("ticker")
    status_ent = (canonical.get("status") or ere.get("status") or "").lower()
    confidence = float(ere.get("confidence") or (0.9 if canonical else 0.0))

    issues: list[str] = []
    score = 1.0
    matches: list[dict[str, str]] = []

    # Educational / macro / portfolio may not need a company entity
    educational = any(x in q for x in ("explain", "what is", "define", "teach", "means"))
    macro = any(x in q for x in ("rbi", "inflation", "macro", "rate cut", "fed", "policy"))
    portfolio = "portfolio" in q
    market = any(x in q for x in ("nifty", "sensex", "market open", "market close"))
    comparison = _is_comparison(q)

    for brand, opts in AMBIGUOUS_BRANDS.items():
        if f" {brand} " in f" {q} " or q.startswith(f"{brand} ") or q.endswith(f" {brand}") or q == brand:
            # specific company already named?
            if any(o["name"].lower() in q or o["ticker"].lower() in q for o in opts):
                continue
            if brand == "tata" and "tcs" in q:
                continue
            issues.append("ambiguous_entity")
            matches = opts
            score -= 0.6
            needs_clarification = True
            break

    if educational or macro or (portfolio and not any(b in q for b in AMBIGUOUS_BRANDS)):
        if not issues:
            score = 0.95 if educational or macro else 0.85
            return {
                "status": "valid",
                "score": score,
                "issues": [],
                "canonical_entity": canonical or None,
                "ticker": ticker,
                "entity_state": "not_required",
                "possible_matches": [],
                "needs_clarification": False,
            }

    if market and not issues:
        return {
            "status": "valid",
            "score": 0.92,
            "issues": [],
            "canonical_entity": canonical or {"canonical_name": "Index / Market", "entity_type": "Index"},
            "ticker": ticker,
            "entity_state": "index_or_market",
            "possible_matches": [],
            "needs_clarification": False,
        }

    # Comparison with multiple resolved candidates is valid (ERE multi_candidate)
    if comparison and len(possible) >= 2 and "ambiguous_entity" not in issues:
        return {
            "status": "valid",
            "score": 0.93,
            "issues": [],
            "canonical_entity": canonical or possible[0],
            "ticker": ticker or (possible[0].get("ticker") if isinstance(possible[0], dict) else None),
            "entity_state": "multi_entity_comparison",
            "possible_matches": possible,
            "needs_clarification": False,
            "comparison_entities": possible,
        }

    # Comparison with explicit vs/versus and two tokens — accept even if ERE sparse
    if comparison and (" vs " in q or " versus " in q) and "ambiguous_entity" not in issues:
        return {
            "status": "valid",
            "score": 0.9,
            "issues": [],
            "canonical_entity": canonical or None,
            "ticker": ticker,
            "entity_state": "comparison_pair",
            "possible_matches": possible,
            "needs_clarification": False,
        }

    if research_blocked or (needs_clarification and not canonical):
        # Don't hard-fail on ERE block when question names a clear company string
        known_tokens = ("hdfc bank", "infosys", "tcs", "wipro", "reliance", "icici", "titan", "itc", "sbi", "axis")
        if any(t in q for t in known_tokens) and "ambiguous_entity" not in issues:
            score = 0.82
            needs_clarification = False
            issues = [i for i in issues if i != "needs_clarification"]
        else:
            issues.append("needs_clarification")
            score = min(score, 0.25)

    if not canonical and not matches and not educational and needs_clarification:
        if not ticker and "needs_clarification" not in issues:
            issues.append("entity_unresolved")
            score = min(score, 0.2)

    if status_ent in {"historical", "merged", "delisted"}:
        issues.append(f"entity_{status_ent}")
        score -= 0.15  # warning, not block — research may continue with caveats

    if canonical and ticker:
        score = max(score, 0.85)
        if not issues:
            score = max(score, confidence)

    score = max(0.0, min(1.0, score))
    if "ambiguous_entity" in issues or "needs_clarification" in issues or "entity_unresolved" in issues:
        status = "invalid" if score < 0.4 else "clarification"
    elif issues:
        status = "warning"
    else:
        status = "valid"

    return {
        "status": status,
        "score": round(score, 4),
        "issues": issues,
        "canonical_entity": canonical or None,
        "ticker": ticker,
        "entity_state": status_ent or ("resolved" if canonical else "unresolved"),
        "possible_matches": matches or possible,
        "needs_clarification": bool(("ambiguous_entity" in issues) or ("needs_clarification" in issues)),
    }
