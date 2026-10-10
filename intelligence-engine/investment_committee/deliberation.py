"""ICI deliberation pipeline — opinions in, committee intelligence out."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from investment_committee.objects import (
    committee_accuracy,
    committee_challenge,
    committee_conflict,
    committee_consensus,
    committee_decision,
    committee_minutes,
    committee_question,
    committee_vote,
    minority_opinion,
)
from investment_committee.schema import ANALYST_ROLES, VOTE_LABELS
from investment_committee import store as ici_store

_INTERNAL = re.compile(
    r"\b(CID|LEO|IRP|DVC|ECP|Yahoo|Groww|IndianAPI|MarketDataClient|Capital IQ|"
    r"Company Analysis|Financial Intelligence|Academy|provider|API|engine)\b",
    re.I,
)


def _scrub(text: Any, *, limit: int = 280) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _INTERNAL.sub("institutional research", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def _list(value: Any, *, limit: int = 6) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = _scrub(value, limit=200)
        return [item] if item else []
    out: list[str] = []
    for item in value:
        piece = _scrub(item, limit=200)
        if piece and piece not in out:
            out.append(piece)
        if len(out) >= limit:
            break
    return out


def _stance(op: dict[str, Any]) -> str:
    s = str(op.get("stance") or "Neutral")
    if s not in {"Bullish", "Neutral", "Bearish"}:
        return "Neutral"
    return s


def _overall_conf(op: dict[str, Any], default: float = 0.55) -> float:
    c = op.get("confidence")
    try:
        if isinstance(c, dict):
            n = float(c.get("overall") or default)
        else:
            n = float(c if c is not None else default)
    except Exception:
        n = default
    if n > 1:
        n = n / 100.0
    return max(0.05, min(0.99, round(n, 4)))


def _coverage(op: dict[str, Any], default: float = 0.55) -> float:
    c = op.get("confidence")
    if isinstance(c, dict):
        try:
            n = float(c.get("coverage") or c.get("evidence") or default)
            if n > 1:
                n = n / 100.0
            return max(0.05, min(0.99, n))
        except Exception:
            return default
    return default


def _present(opinions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for r in ANALYST_ROLES:
        op = opinions.get(r)
        if isinstance(op, dict) and (op.get("summary") or op.get("headline")):
            out[r] = op
    return out


# --- Stage 1: Consensus Engine -------------------------------------------------


def stage_consensus(present: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stances = {r: (_stance(present[r]) if r in present else "Missing") for r in ANALYST_ROLES}
    by_stance: dict[str, list[str]] = {"Bullish": [], "Neutral": [], "Bearish": []}
    for r, s in stances.items():
        if s in by_stance:
            by_stance[s].append(r)

    agreements: list[str] = []
    for s, roles in by_stance.items():
        if len(roles) >= 3:
            labels = ", ".join(r.replace("_", " ") for r in roles[:5])
            agreements.append(f"{s} lean shared across {labels}")

    disagreements: list[str] = []
    if by_stance["Bullish"] and by_stance["Bearish"]:
        disagreements.append(
            "Specialists split between supportive and cautious stances — quality/entry or risk tension likely."
        )
    if stances.get("business") == "Bullish" and stances.get("valuation") == "Bearish":
        disagreements.append("Business quality constructive while valuation remains demanding.")
    if stances.get("financial") == "Bullish" and stances.get("risk") == "Bearish":
        disagreements.append("Financial trajectory improving while risk desk stays cautious.")

    weak: list[str] = []
    review: list[str] = []
    for r, op in present.items():
        cov = _coverage(op)
        label = op.get("analyst") or r.replace("_", " ").title()
        if cov < 0.55 or len(_list(op.get("evidence"), limit=3)) < 2:
            weak.append(f"{label}: evidence file still thin")
            review.append(f"{label} file needs fuller substantiation before conviction rises")
        for q in _list(op.get("unanswered_questions"), limit=1):
            review.append(q)

    if not agreements:
        agreements.append("Specialists cover distinct mandates without collapsing into one narrative.")
    if not disagreements:
        disagreements.append("No hard polarity — residual debate is intensity of conviction, not direction.")

    return committee_consensus(
        agreements=agreements[:6],
        disagreements=disagreements[:6],
        weak_evidence=weak[:6],
        needing_review=review[:8],
        stances=stances,
    )


# --- Stage 2: Conflict Engine --------------------------------------------------


def stage_conflicts(stances: dict[str, str], present: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    biz, val = stances.get("business"), stances.get("valuation")
    if biz == "Bullish" and val == "Bearish":
        conflicts.append(
            committee_conflict(
                topic="Franchise quality versus entry price",
                left={
                    "analyst": "Business Analyst",
                    "view": "The franchise is exceptionally strong.",
                },
                right={
                    "analyst": "Valuation Analyst",
                    "view": "The market already prices in most future growth.",
                },
                assessment="High-quality company. Limited valuation upside.",
                confidence_impact="Recommendation confidence reduced until valuation cushion improves.",
            )
        )
    fin, risk = stances.get("financial"), stances.get("risk")
    if fin == "Bullish" and risk == "Bearish":
        conflicts.append(
            committee_conflict(
                topic="Improving financials versus left-tail risk",
                left={
                    "analyst": "Financial Analyst",
                    "view": "Financial trajectory is improving.",
                },
                right={
                    "analyst": "Risk Analyst",
                    "view": "Downside risks remain material.",
                },
                assessment="Better prints, elevated left-tail risk.",
                confidence_impact="Confidence capped until leading risk indicators stabilise.",
            )
        )
    mkt, val2 = stances.get("market"), stances.get("valuation")
    if mkt == "Bullish" and val2 == "Bearish":
        conflicts.append(
            committee_conflict(
                topic="Tape versus value",
                left={"analyst": "Market Analyst", "view": "Tape is constructive."},
                right={"analyst": "Valuation Analyst", "view": "Multiples leave limited cushion."},
                assessment="Momentum supportive; valuation cushion thin.",
                confidence_impact="Timing overlay not allowed to override valuation discipline.",
            )
        )
    mgmt, own = stances.get("management"), stances.get("ownership")
    if mgmt == "Bullish" and own == "Bearish":
        conflicts.append(
            committee_conflict(
                topic="Trust versus ownership signals",
                left={"analyst": "Management Analyst", "view": "Governance and execution look trustable."},
                right={"analyst": "Ownership Analyst", "view": "Ownership trend is less supportive."},
                assessment="Operators trusted; ownership alignment needs watch.",
                confidence_impact="Alignment risk trims conviction at the margin.",
            )
        )
    if not conflicts:
        bulls = [r for r, s in stances.items() if s == "Bullish"]
        bears = [r for r, s in stances.items() if s == "Bearish"]
        if bulls and bears:
            b, r = bulls[0], bears[0]
            conflicts.append(
                committee_conflict(
                    topic=f"{b.replace('_', ' ').title()} versus {r.replace('_', ' ').title()}",
                    left={
                        "analyst": (present.get(b) or {}).get("analyst") or b,
                        "view": _scrub((present.get(b) or {}).get("summary"), limit=140),
                    },
                    right={
                        "analyst": (present.get(r) or {}).get("analyst") or r,
                        "view": _scrub((present.get(r) or {}).get("summary"), limit=140),
                    },
                    assessment="Specialists disagree on the balance of opportunity and risk.",
                    confidence_impact="Conviction held at moderate until the conflict resolves.",
                )
            )
    return conflicts[:5]


# --- Stage 3: Evidence Challenge ----------------------------------------------


def stage_challenges(present: dict[str, dict[str, Any]], stances: dict[str, str]) -> list[dict[str, Any]]:
    challenges: list[dict[str, Any]] = []

    fin = present.get("financial") or {}
    if fin:
        claim = _list(fin.get("strengths"), limit=1)
        claim_text = claim[0] if claim else "Margins / earnings quality improving."
        challenges.append(
            committee_challenge(
                target_role="financial",
                target_analyst="Financial Analyst",
                claim=_scrub(claim_text, limit=160),
                challenge=(
                    "Are the improvements driven by durable operating leverage, "
                    "or by temporary cost decline / one-offs?"
                ),
                need="Next-quarter confirmation of margin and cash conversion durability.",
            )
        )

    biz = present.get("business") or {}
    if biz and stances.get("business") == "Bullish":
        claim = _list(biz.get("strengths"), limit=1)
        claim_text = claim[0] if claim else "Strong competitive position / moat."
        challenges.append(
            committee_challenge(
                target_role="business",
                target_analyst="Business Analyst",
                claim=_scrub(claim_text, limit=160),
                challenge=(
                    "Is market share actually increasing, or is industry growth lifting everyone?"
                ),
                need="Share / volume evidence versus industry growth over the next print cycle.",
            )
        )

    val = present.get("valuation") or {}
    if val:
        challenges.append(
            committee_challenge(
                target_role="valuation",
                target_analyst="Valuation Analyst",
                claim=_scrub((_list(val.get("weaknesses"), limit=1) or ["Valuation already demanding."])[0], limit=160),
                challenge="What earnings path is required to earn today's multiple without multiple compression?",
                need="Clearer expected-return bridge under base and bear earnings paths.",
            )
        )

    risk = present.get("risk") or {}
    if risk and stances.get("risk") == "Bearish":
        challenges.append(
            committee_challenge(
                target_role="risk",
                target_analyst="Risk Analyst",
                claim=_scrub((_list(risk.get("weaknesses"), limit=1) or ["Material downside risks."])[0], limit=160),
                challenge="Which single risk, if realised, most impairs franchise returns — and what is the leading indicator?",
                need="Named invalidation indicator and monitoring cadence.",
            )
        )

    mgmt = present.get("management") or {}
    if mgmt:
        challenges.append(
            committee_challenge(
                target_role="management",
                target_analyst="Management Analyst",
                claim=_scrub((_list(mgmt.get("strengths"), limit=1) or ["Governance looks solid."])[0], limit=160),
                challenge="Is capital allocation consistent across the cycle, or only in benign conditions?",
                need="Cycle-aware capital allocation evidence from recent disclosures.",
            )
        )

    return challenges[:6]


# --- Stage 4: Confidence Recalibration ----------------------------------------


def stage_recalibrate(
    present: dict[str, dict[str, Any]],
    conflicts: list[dict[str, Any]],
    challenges: list[dict[str, Any]],
    consensus: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    challenged_roles = {c.get("target_role") for c in challenges}
    conflict_analysts = set()
    for c in conflicts:
        for side in (c.get("left"), c.get("right")):
            if isinstance(side, dict) and side.get("analyst"):
                conflict_analysts.add(str(side["analyst"]).lower())
    weak_labels = " ".join(consensus.get("areas_with_weak_evidence") or []).lower()

    out: dict[str, dict[str, Any]] = {}
    for role, op in present.items():
        submitted = _overall_conf(op)
        delta = 0.0
        reasons: list[str] = []
        if role in challenged_roles:
            delta -= 0.06
            reasons.append("Evidence challenge raised in committee.")
        analyst = str(op.get("analyst") or "").lower()
        if analyst and analyst in conflict_analysts:
            delta -= 0.04
            reasons.append("Role sits on an active committee conflict.")
        if role.replace("_", " ") in weak_labels or (op.get("analyst") or "").lower() in weak_labels:
            delta -= 0.05
            reasons.append("Weak evidence file noted by consensus engine.")
        # Supportive agreement can slightly lift
        if _stance(op) == "Bullish" and any("Bullish lean" in a for a in (consensus.get("areas_of_agreement") or [])):
            delta += 0.02
            reasons.append("Stance reinforced by multi-analyst agreement.")
        recalibrated = max(0.15, min(0.95, round(submitted + delta, 4)))
        out[role] = {
            "analyst": op.get("analyst"),
            "submitted": submitted,
            "recalibrated": recalibrated,
            "delta": round(recalibrated - submitted, 4),
            "reasons": reasons or ["No material committee adjustment."],
        }
    return out


# --- Stage 5: Committee Vote ---------------------------------------------------


def stage_vote(stances: dict[str, str], recalibrated: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ballots: dict[str, str] = {}
    for role in ANALYST_ROLES:
        raw = stances.get(role, "Missing")
        ballots[(recalibrated.get(role) or {}).get("analyst") or role.replace("_", " ").title()] = VOTE_LABELS.get(
            raw, "Abstain"
        )

    constructive = sum(1 for v in ballots.values() if v == "Constructive")
    neutral = sum(1 for v in ballots.values() if v == "Neutral")
    cautious = sum(1 for v in ballots.values() if v == "Cautious")
    abstain = sum(1 for v in ballots.values() if v == "Abstain")
    active = constructive + neutral + cautious

    if constructive >= cautious and constructive >= neutral and constructive > 0:
        consensus = "Constructive"
        top = constructive
    elif cautious > constructive and cautious >= neutral:
        consensus = "Cautious"
        top = cautious
    else:
        consensus = "Neutral"
        top = max(neutral, 1)

    # Conviction from concentration + recalibrated confidence
    confs = [row["recalibrated"] for row in recalibrated.values()] or [0.55]
    avg_conf = sum(confs) / len(confs)
    share = top / active if active else 0
    if share >= 0.67 and avg_conf >= 0.7:
        conviction = "High"
    elif share >= 0.45 and avg_conf >= 0.55:
        conviction = "Moderate"
    else:
        conviction = "Low"

    tally = f"{top} / {active}" if active else "0 / 0"
    return committee_vote(
        ballots=ballots,
        consensus=consensus,
        conviction=conviction,
        tally=tally,
        constructive=constructive,
        neutral=neutral,
        cautious=cautious,
        abstain=abstain,
    )


# --- Stage 7: Minority Opinions ------------------------------------------------


def stage_minority(vote: dict[str, Any], conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    consensus = vote.get("consensus")
    ballots = vote.get("ballots") or {}
    minority: list[dict[str, Any]] = []

    if consensus == "Constructive":
        dissenters = [a for a, v in ballots.items() if v == "Cautious"]
        if dissenters:
            minority.append(
                minority_opinion(
                    view="Valuation leaves insufficient upside / downside not priced.",
                    supporters=dissenters,
                )
            )
        # Classic quality vs price minority framing
        if any("entry price" in (c.get("topic") or "").lower() or "valuation" in (c.get("topic") or "").lower() for c in conflicts):
            minority.append(
                minority_opinion(
                    view="Valuation leaves insufficient upside even if business quality is excellent.",
                    supporters=[a for a, v in ballots.items() if v in {"Cautious", "Neutral"}][:3] or ["Valuation Analyst"],
                )
            )
    elif consensus == "Cautious":
        dissenters = [a for a, v in ballots.items() if v == "Constructive"]
        if dissenters:
            minority.append(
                minority_opinion(
                    view="Business quality justifies staying constructive despite near-term caution.",
                    supporters=dissenters,
                )
            )
    else:
        bulls = [a for a, v in ballots.items() if v == "Constructive"]
        bears = [a for a, v in ballots.items() if v == "Cautious"]
        if bulls:
            minority.append(minority_opinion(view="Quality and financial trajectory support a constructive lean.", supporters=bulls))
        if bears:
            minority.append(minority_opinion(view="Entry price and risk skew argue for staying defensive.", supporters=bears))

    # Deduplicate by view
    seen = set()
    out = []
    for m in minority:
        v = m.get("view")
        if v not in seen:
            seen.add(v)
            out.append(m)
    return out[:3]


# --- Stage 10: Decision (vote output, not Buy/Hold/Sell) -----------------------


def _quality_label(stance: str) -> str:
    return {"Bullish": "Excellent", "Neutral": "Adequate", "Bearish": "Weak", "Missing": "Unreviewed"}.get(stance, "Adequate")


def _fin_label(stance: str) -> str:
    return {"Bullish": "Strong", "Neutral": "Stable", "Bearish": "Soft", "Missing": "Unreviewed"}.get(stance, "Stable")


def _val_label(stance: str) -> str:
    return {"Bullish": "Attractive", "Neutral": "Neutral", "Bearish": "Demanding", "Missing": "Unreviewed"}.get(stance, "Neutral")


def _risk_label(stance: str) -> str:
    return {"Bullish": "Contained", "Neutral": "Moderate", "Bearish": "Elevated", "Missing": "Unreviewed"}.get(stance, "Moderate")


def stage_decision(
    stances: dict[str, str],
    vote: dict[str, Any],
    recalibrated: dict[str, dict[str, Any]],
    conflicts: list[dict[str, Any]],
    present_count: int,
) -> dict[str, Any]:
    confs = [row["recalibrated"] for row in recalibrated.values()] or [0.55]
    conf = round(sum(confs) / len(confs), 4)
    if conflicts:
        conf = max(0.2, round(conf - 0.03 * min(len(conflicts), 3), 4))

    readiness = "Institutional Grade" if present_count >= 7 and vote.get("conviction") in {"High", "Moderate"} else "Research Note Complete"
    if present_count < 6:
        readiness = "Incomplete Committee File"

    return committee_decision(
        business_quality=_quality_label(stances.get("business", "Neutral")),
        financials=_fin_label(stances.get("financial", "Neutral")),
        valuation=_val_label(stances.get("valuation", "Neutral")),
        risk=_risk_label(stances.get("risk", "Neutral")),
        macro=_val_label(stances.get("macro", "Neutral")) if stances.get("macro") != "Bullish" else "Supportive",
        market={"Bullish": "Constructive", "Neutral": "Neutral", "Bearish": "Fragile"}.get(stances.get("market", "Neutral"), "Neutral"),
        committee_position=str(vote.get("consensus") or "Neutral"),
        recommendation_readiness=readiness,
        confidence=conf,
    )


# --- Stage 6: Minutes + Stage 8/9 hooks ---------------------------------------


def _extract_predictions(present: dict[str, dict[str, Any]], company: str) -> list[dict[str, Any]]:
    """Soft expectations the committee can later score (prediction accountability)."""
    preds: list[dict[str, Any]] = []
    fin = present.get("financial") or {}
    sections = fin.get("sections") if isinstance(fin.get("sections"), dict) else {}
    for key, metric in (("revenue", "revenue_growth"), ("roe", "roe"), ("margins", "margins")):
        val = sections.get(key)
        if val and val != "n/a":
            # Only keep numeric-ish expectations
            m = re.search(r"(-?\d+(?:\.\d+)?)\s*%?", str(val))
            if m:
                preds.append({"metric": metric, "expected": float(m.group(1)), "source_analyst": "Financial Analyst", "company": company})
    if not preds:
        preds.append(
            {
                "metric": "loan_growth_or_revenue_growth",
                "expected": 15.0,
                "unit": "pct",
                "source_analyst": "Committee",
                "company": company,
                "note": "Placeholder growth expectation pending clearer quantitative guidance.",
            }
        )
    return preds[:4]


def build_minutes(
    *,
    query: str,
    company: str,
    ticker: str | None,
    stances: dict[str, str],
    vote: dict[str, Any],
    decision: dict[str, Any],
    conflicts: list[dict[str, Any]],
    challenges: list[dict[str, Any]],
    minority: list[dict[str, Any]],
    open_requests: list[dict[str, Any]],
    meeting_id: str,
) -> dict[str, Any]:
    discussion = {
        "business": _scrub((f"{_quality_label(stances.get('business', 'Neutral'))} franchise.").capitalize(), limit=120),
        "financials": _fin_label(stances.get("financial", "Neutral")),
        "valuation": _val_label(stances.get("valuation", "Neutral")),
        "macro": {"Bullish": "Supportive", "Neutral": "Neutral", "Bearish": "Headwind"}.get(stances.get("macro", "Neutral"), "Neutral"),
        "risk": _risk_label(stances.get("risk", "Neutral")),
        "market": decision.get("market"),
        "sector": {"Bullish": "Attractive", "Neutral": "Neutral", "Bearish": "Challenged"}.get(stances.get("sector", "Neutral"), "Neutral"),
        "management": {"Bullish": "Trusted", "Neutral": "Adequate", "Bearish": "Watch"}.get(stances.get("management", "Neutral"), "Adequate"),
        "ownership": {"Bullish": "Aligned", "Neutral": "Stable", "Bearish": "Watch"}.get(stances.get("ownership", "Neutral"), "Stable"),
    }
    decision_text = (
        f"Continue {str(decision.get('committee_position') or 'Neutral').lower()} stance"
    )
    if stances.get("valuation") == "Bearish":
        decision_text += ", but require stronger valuation support before increasing conviction."
    else:
        decision_text += "; reassess on material evidence change."

    open_q = [_scrub(r.get("request"), limit=160) for r in open_requests if r.get("request")]
    open_q = [q for q in open_q if q][:6]
    if not open_q:
        open_q = ["Upcoming earnings", "Demand / growth confirmation", "Valuation cushion"]

    return committee_minutes(
        title="Investment Committee Minutes",
        meeting_id=meeting_id,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        company=company,
        ticker=ticker,
        question=query,
        discussion=discussion,
        decision=decision_text,
        decision_stance=decision.get("committee_position"),
        committee_position=decision.get("committee_position"),
        conviction=vote.get("conviction"),
        vote_tally=vote.get("tally"),
        ballots=vote.get("ballots"),
        conflicts_noted=[c.get("committee_assessment") or c.get("topic") for c in conflicts][:4],
        challenges_noted=[c.get("challenge") for c in challenges][:4],
        minority_views=[m.get("view") for m in minority][:3],
        open_questions=open_q,
        follow_up=open_q[0] if open_q else "Need confirmation after next earnings.",
        recommendation_readiness=decision.get("recommendation_readiness"),
        confidence=decision.get("confidence"),
    )


# --- Orchestrator --------------------------------------------------------------


def deliberate(
    opinions: dict[str, dict[str, Any]],
    *,
    query: str = "",
    company: str = "",
    ticker: str | None = None,
) -> dict[str, Any]:
    """Full ICI meeting: consensus → conflict → challenge → recalibrate → vote → minutes → CIO pack."""
    present = _present(opinions)
    meeting_id = str(uuid4())
    name = company or ticker or "the company"

    consensus = stage_consensus(present)
    stances = consensus.get("stances") or {}
    conflicts = stage_conflicts({r: s for r, s in stances.items() if s != "Missing"}, present)
    challenges = stage_challenges(present, stances)
    recalibrated = stage_recalibrate(present, conflicts, challenges, consensus)
    vote = stage_vote(stances, recalibrated)
    minority = stage_minority(vote, conflicts)
    decision = stage_decision(stances, vote, recalibrated, conflicts, len(present))

    open_requests = [c.get("open_evidence_request") for c in challenges if c.get("open_evidence_request")]
    questions = [
        committee_question(text=r.get("request"), owner=r.get("for_analyst") or "committee", priority="high")
        for r in open_requests
        if r.get("request")
    ]

    minutes = build_minutes(
        query=query or f"Committee review of {name}",
        company=name,
        ticker=ticker,
        stances=stances,
        vote=vote,
        decision=decision,
        conflicts=conflicts,
        challenges=challenges,
        minority=minority,
        open_requests=open_requests,
        meeting_id=meeting_id,
    )

    # Persist forever (process-local)
    stored_minutes = ici_store.put_minutes(ticker, minutes)
    preds = _extract_predictions(present, name)
    ici_store.put_predictions(ticker, meeting_id, preds)
    history = ici_store.list_minutes(ticker, limit=12)
    timeline = ici_store.timeline(ticker, limit=12)
    prior_acc = ici_store.latest_accuracy(ticker)
    accuracy = committee_accuracy(
        accuracy_pct=(prior_acc or {}).get("committee_accuracy_pct"),
        predictions_scored=int((prior_acc or {}).get("predictions_scored") or 0),
    )

    # Legacy-compatible summary fields for IAF/CIO
    reason = (
        conflicts[0].get("committee_assessment")
        if conflicts
        else f"Committee vote {vote.get('tally')} → {vote.get('consensus')} with {str(vote.get('conviction')).lower()} conviction."
    )
    if conflicts and "entry" in (conflicts[0].get("topic") or "").lower():
        reason = "High-quality business but valuation already discounts much of the expected growth."

    conf = float(decision.get("confidence") or 0.55)
    readiness_map = {
        "Institutional Grade": "ready",
        "Research Note Complete": "partial",
        "Incomplete Committee File": "not_ready",
    }

    return {
        "enabled": True,
        "programme": "AGIB_INVESTMENT_COMMITTEE_INTELLIGENCE_V1",
        "version": "ici-v1.0.0",
        "not_an_engine": True,
        "orchestration_only": True,
        "meeting": True,
        "meeting_id": meeting_id,
        "owner": "committee",
        "analyst": "Investment Committee",
        "question": query or "What is the coordinated institutional view?",
        "company": name,
        "ticker": ticker,
        # Typed objects
        "consensus": consensus,
        "conflicts": conflicts,
        "challenges": challenges,
        "questions": questions,
        "open_evidence_requests": open_requests,
        "confidence_recalibration": recalibrated,
        "vote": vote,
        "minority_opinions": minority,
        "minutes": stored_minutes,
        "decision": decision,
        "accuracy": accuracy,
        "history": history,
        "timeline": timeline,
        "predictions": preds,
        # Stage aliases for UI / IAF adapters
        "stage_1_consensus": stances,
        "stage_1_detail": consensus,
        "stage_2_conflicts": conflicts,
        "stage_3_challenges": challenges,
        "stage_3_missing_evidence": [_scrub(r.get("request"), limit=180) for r in open_requests if r.get("request")],
        "stage_4_confidence": recalibrated,
        "stage_5_vote": vote,
        "stage_6_minutes": stored_minutes,
        "stage_7_minority": minority,
        "stage_8_timeline": timeline,
        "stage_9_accuracy": accuracy,
        "stage_10_decision": decision,
        "disagreement_matrix": {
            "analyst_stances": {
                (present[r].get("analyst") if r in present else r.replace("_", " ").title()): stances.get(r, "Missing")
                for r in ANALYST_ROLES
            },
            "committee_stance": vote.get("consensus"),
            "conviction": vote.get("conviction"),
            "vote": vote.get("tally"),
            "reason": reason,
        },
        "committee_summary": _scrub(
            f"Investment Committee deliberated, challenged assumptions, recalibrated confidence, and voted. "
            f"Position: {decision.get('committee_position')}. Conviction: {vote.get('conviction')}. "
            f"Vote: {vote.get('tally')}. {reason}",
            limit=360,
        ),
        "committee_stance": vote.get("consensus"),
        "committee_reason": reason,
        "confidence": conf,
        "recommendation_readiness": readiness_map.get(str(decision.get("recommendation_readiness")), "partial"),
        "recommendation_readiness_label": decision.get("recommendation_readiness"),
        "opinions_count": len(present),
        "analyst_roles_present": list(present.keys()),
        "agreements": consensus.get("areas_of_agreement") or [],
        "disagreements": [c.get("committee_assessment") or c.get("topic") for c in conflicts],
        "missing_evidence": [_scrub(r.get("request"), limit=180) for r in open_requests if r.get("request")],
        "cio_signals": {
            "stances": stances,
            "committee_stance": vote.get("consensus"),
            "conviction": vote.get("conviction"),
            "vote": vote.get("tally"),
            "reason": reason,
            "conflicts": [
                {
                    "topic": c.get("topic"),
                    "tension": c.get("committee_assessment") or c.get("tension"),
                    "confidence_impact": c.get("recommendation_confidence_impact"),
                }
                for c in conflicts
            ],
            "challenges": [{"analyst": c.get("target_analyst"), "challenge": c.get("challenge"), "need": c.get("need")} for c in challenges],
            "missing_evidence": [_scrub(r.get("request"), limit=160) for r in open_requests if r.get("request")][:5],
            "minority": [m.get("view") for m in minority],
            "decision": decision,
            "recalibrated_confidence": {r: row.get("recalibrated") for r, row in recalibrated.items()},
            "risk_items": _list((present.get("risk") or {}).get("weaknesses"), limit=5),
            "what_changed": [
                {
                    "analyst": (present[r].get("analyst") if r in present else r),
                    "notes": ((present[r].get("what_changed") or {}).get("notes") if r in present else []),
                }
                for r in ANALYST_ROLES
                if r in present and (present[r].get("what_changed") or {}).get("changed")
            ],
        },
        # Compact per-desk blurbs for CIO (stance labels, not analyst prose dumps)
        "desk_views": {
            "business": f"{stances.get('business')} — {decision.get('business_quality')}",
            "financial": f"{stances.get('financial')} — {decision.get('financials')}",
            "valuation": f"{stances.get('valuation')} — {decision.get('valuation')}",
            "market": f"{stances.get('market')} — {decision.get('market')}",
            "sector": stances.get("sector"),
            "macro": f"{stances.get('macro')} — {decision.get('macro')}",
            "risks": _list((present.get("risk") or {}).get("weaknesses"), limit=5) or ["Execution", "Earnings", "Multiple compression"],
            "management": stances.get("management"),
            "ownership": stances.get("ownership"),
        },
    }
