"""Contradiction detector — surface competing theses for committee debate."""

from __future__ import annotations

from typing import Any

_OPPOSED_PAIRS = (
    (("advantage", "durable", "superior"), ("narrowing", "already reflects", "priced", "compress")),
    (("benign", "structurally"), ("risk", "invalidate", "slow")),
    (("above", "premium"), ("below", "limited", "already priced")),
)


def detect_contradictions(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = []
    texts = [(h.get("id"), str(h.get("statement") or "").lower(), h.get("type")) for h in hypotheses]
    for i, (id_a, text_a, type_a) in enumerate(texts):
        for id_b, text_b, type_b in texts[i + 1 :]:
            score = 0
            reasons = []
            # Valuation quality already priced vs durable advantage
            if type_a != type_b or True:
                for pos, neg in _OPPOSED_PAIRS:
                    a_pos = any(p in text_a for p in pos)
                    b_neg = any(n in text_b for n in neg)
                    b_pos = any(p in text_b for p in pos)
                    a_neg = any(n in text_a for n in neg)
                    if (a_pos and b_neg) or (b_pos and a_neg):
                        score += 1
                        reasons.append(f"tension between {id_a} and {id_b}")
            # Explicit: Business advantage vs Valuation already reflects
            if ("advantage" in text_a and "already reflects" in text_b) or (
                "advantage" in text_b and "already reflects" in text_a
            ):
                score += 2
                reasons.append("quality thesis vs priced-in thesis")
            if ("narrowing" in text_a and "durable" in text_b) or ("narrowing" in text_b and "durable" in text_a):
                score += 2
                reasons.append("durable advantage vs competitive convergence")
            if score >= 2:
                pairs.append(
                    {
                        "hypothesis_a": id_a,
                        "hypothesis_b": id_b,
                        "types": [type_a, type_b],
                        "tension_score": score,
                        "reasons": sorted(set(reasons)),
                        "resolution": "Committee / CIO must weigh competing interpretations before publication",
                    }
                )
    return {
        "contradiction_count": len(pairs),
        "pairs": pairs,
        "requires_internal_debate": len(pairs) > 0,
    }
