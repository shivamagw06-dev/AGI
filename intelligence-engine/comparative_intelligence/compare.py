"""Side-by-side comparison helpers — pass-through values only; never re-score."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _payload(wrap: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not wrap or not wrap.get("ok"):
        return {}
    p = wrap.get("payload")
    return p if isinstance(p, dict) else {}


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _pillar_score(payload: Dict[str, Any], pillar_name: str) -> Optional[float]:
    pillars = _as_list(payload.get("pillars") or payload.get("pillar_scores"))
    target = pillar_name.lower().replace(" ", "_")
    for p in pillars:
        if not isinstance(p, dict):
            continue
        name = str(p.get("pillar") or p.get("name") or p.get("id") or "").lower().replace(" ", "_")
        if name == target or target in name or name in target:
            for k in ("score", "value", "quality_score"):
                if isinstance(p.get(k), (int, float)):
                    return float(p[k])
    # dict form pillar_scores
    ps = payload.get("pillar_scores")
    if isinstance(ps, dict):
        for k, v in ps.items():
            if target in str(k).lower().replace(" ", "_"):
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, dict) and isinstance(v.get("score"), (int, float)):
                    return float(v["score"])
    return None


def _overall_quality(payload: Dict[str, Any]) -> Optional[float]:
    for k in ("overall_score", "quality_score", "score"):
        if isinstance(payload.get(k), (int, float)):
            return float(payload[k])
    overall = payload.get("overall")
    if isinstance(overall, dict) and isinstance(overall.get("score"), (int, float)):
        return float(overall["score"])
    if isinstance(overall, (int, float)):
        return float(overall)
    return None


def _trend_snippets(payload: Dict[str, Any], hints: Sequence[str], limit: int = 4) -> List[str]:
    out: List[str] = []
    for t in _as_list(payload.get("trends") or payload.get("items") or payload.get("findings")):
        if not isinstance(t, dict):
            continue
        metric = str(t.get("metric") or t.get("name") or t.get("series") or "").lower()
        if hints and not any(h in metric for h in hints):
            continue
        direction = t.get("direction") or t.get("trend") or t.get("label") or "observed"
        out.append(f"{t.get('metric') or t.get('name') or metric}: {direction}")
        if len(out) >= limit:
            break
    if not out and payload.get("summary"):
        out.append(str(payload["summary"])[:200])
    return out


def _execution_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    objs = _as_list(payload.get("objectives") or payload.get("assessments") or payload.get("items"))
    counts: Dict[str, int] = {}
    samples: List[str] = []
    for o in objs:
        if not isinstance(o, dict):
            continue
        status = str(o.get("status") or o.get("execution_status") or o.get("label") or "assessed")
        counts[status] = counts.get(status, 0) + 1
        title = o.get("title") or o.get("objective") or o.get("text")
        if title and len(samples) < 3:
            samples.append(f"{title}: {status}")
    return {"status_counts": counts, "samples": samples, "n": len(objs)}


def _evidence_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    assessments = _as_list(
        payload.get("assessments") or payload.get("claims") or payload.get("items") or payload.get("findings")
    )
    counts: Dict[str, int] = {}
    samples: List[str] = []
    for a in assessments:
        if not isinstance(a, dict):
            continue
        status = str(a.get("status") or a.get("consistency") or a.get("label") or "assessed")
        counts[status] = counts.get(status, 0) + 1
        claim = a.get("claim") or a.get("statement") or a.get("text")
        if claim and len(samples) < 3:
            samples.append(f"{claim}: {status}")
    return {"status_counts": counts, "samples": samples, "n": len(assessments)}


def evidence_ids(module: str, payload: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    seen = set()

    def add(x: Any) -> None:
        if x is None:
            return
        s = str(x).strip()
        if not s or s in seen:
            return
        seen.add(s)
        ids.append(s)

    for item in _as_list(payload.get("evidence_ids")):
        add(item)
    for key in ("trends", "relationships", "facts", "assessments", "objectives", "pillars", "claims", "items"):
        for row in _as_list(payload.get(key)):
            if isinstance(row, dict):
                add(row.get("id") or row.get("evidence_id") or row.get("objective_id"))
                for e in _as_list(row.get("evidence_ids")):
                    add(e)
    if not ids and payload:
        add(f"{module}:{payload.get('ticker') or 'unknown'}")
    return ids


def company_dimension_row(
    ticker: str,
    collected: Dict[str, Dict[str, Any]],
    *,
    dimension: str,
) -> Dict[str, Any]:
    """Extract a comparable row for one company/dimension — values pass through only."""
    fire01 = _payload(collected.get("FIRE-01"))
    fire02 = _payload(collected.get("FIRE-02"))
    fire04 = _payload(collected.get("FIRE-04"))
    fire05 = _payload(collected.get("FIRE-05"))
    fire06 = _payload(collected.get("FIRE-06"))

    row: Dict[str, Any] = {"ticker": ticker, "dimension": dimension, "available": True}

    if dimension == "business_quality_comparison":
        score = _overall_quality(fire06)
        row.update(
            {
                "module": "FIRE-06",
                "score": score,
                "label": fire06.get("overall_label") or fire06.get("label"),
                "confidence": fire06.get("confidence"),
                "period": fire06.get("period") or fire06.get("reporting_period"),
                "evidence_ids": evidence_ids("FIRE-06", fire06),
                "text": f"{ticker} business quality score={score} label={fire06.get('overall_label') or fire06.get('label')}",
            }
        )
        row["available"] = score is not None or bool(fire06)
    elif dimension == "growth":
        score = _pillar_score(fire06, "growth")
        snippets = _trend_snippets(fire01, ("revenue", "growth"))
        row.update(
            {
                "module": "FIRE-06" if score is not None else "FIRE-01",
                "score": score,
                "snippets": snippets,
                "confidence": (fire06.get("confidence") if score is not None else fire01.get("confidence")),
                "period": fire06.get("period") or fire01.get("period"),
                "evidence_ids": evidence_ids("FIRE-06", fire06)[:5] + evidence_ids("FIRE-01", fire01)[:5],
                "text": f"{ticker} growth pillar={score}; trends={'; '.join(snippets) or 'n/a'}",
            }
        )
    elif dimension == "margins":
        score = _pillar_score(fire06, "profitability") or _pillar_score(fire06, "profit")
        snippets = _trend_snippets(fire01, ("margin",))
        row.update(
            {
                "module": "FIRE-01",
                "score": score,
                "snippets": snippets,
                "confidence": fire01.get("confidence") or fire06.get("confidence"),
                "period": fire01.get("period") or fire06.get("period"),
                "evidence_ids": evidence_ids("FIRE-01", fire01)[:8],
                "text": f"{ticker} margins: {'; '.join(snippets) or ('pillar=' + str(score) if score is not None else 'n/a')}",
            }
        )
    elif dimension == "cash_flow":
        score = _pillar_score(fire06, "cash")
        snippets = _trend_snippets(fire01, ("cash", "fcf", "free_cash", "operating_cash"))
        row.update(
            {
                "module": "FIRE-06" if score is not None else "FIRE-01",
                "score": score,
                "snippets": snippets,
                "confidence": fire06.get("confidence") or fire01.get("confidence"),
                "period": fire06.get("period") or fire01.get("period"),
                "evidence_ids": evidence_ids("FIRE-06", fire06)[:5] + evidence_ids("FIRE-01", fire01)[:5],
                "text": f"{ticker} cash flow pillar={score}; {'; '.join(snippets) or 'n/a'}",
            }
        )
    elif dimension == "balance_sheet":
        score = _pillar_score(fire06, "balance_sheet") or _pillar_score(fire06, "balance")
        snippets = []
        for r in _as_list(fire02.get("relationships") or fire02.get("items")):
            if not isinstance(r, dict):
                continue
            name = str(r.get("name") or r.get("relationship") or "").lower()
            if any(h in name for h in ("debt", "leverage", "liquidity", "balance", "solvency")) or not snippets:
                snippets.append(f"{r.get('name') or name}: {r.get('status') or r.get('label')}")
            if len(snippets) >= 4:
                break
        row.update(
            {
                "module": "FIRE-06" if score is not None else "FIRE-02",
                "score": score,
                "snippets": snippets,
                "confidence": fire06.get("confidence") or fire02.get("confidence"),
                "period": fire06.get("period") or fire02.get("period"),
                "evidence_ids": evidence_ids("FIRE-06", fire06)[:5] + evidence_ids("FIRE-02", fire02)[:5],
                "text": f"{ticker} balance sheet pillar={score}; {'; '.join(snippets) or 'n/a'}",
            }
        )
    elif dimension == "capital_allocation":
        score = _pillar_score(fire06, "capital_allocation") or _pillar_score(fire06, "capital")
        snippets = _trend_snippets(fire01, ("capex", "dividend", "buyback", "allocation"))
        row.update(
            {
                "module": "FIRE-06",
                "score": score,
                "snippets": snippets,
                "confidence": fire06.get("confidence"),
                "period": fire06.get("period"),
                "evidence_ids": evidence_ids("FIRE-06", fire06),
                "text": f"{ticker} capital allocation pillar={score}; {'; '.join(snippets) or 'n/a'}",
            }
        )
    elif dimension == "management_execution":
        summary = _execution_summary(fire05)
        row.update(
            {
                "module": "FIRE-05",
                "summary": summary,
                "confidence": fire05.get("confidence"),
                "period": fire05.get("period"),
                "evidence_ids": evidence_ids("FIRE-05", fire05),
                "text": f"{ticker} execution n={summary['n']} statuses={summary['status_counts']}",
            }
        )
        row["available"] = bool(fire05)
    elif dimension == "evidence_alignment":
        summary = _evidence_summary(fire04)
        row.update(
            {
                "module": "FIRE-04",
                "summary": summary,
                "confidence": fire04.get("confidence"),
                "period": fire04.get("period"),
                "evidence_ids": evidence_ids("FIRE-04", fire04),
                "text": f"{ticker} evidence n={summary['n']} statuses={summary['status_counts']}",
            }
        )
        row["available"] = bool(fire04)
    else:
        row["available"] = False
        row["text"] = f"{ticker}: dimension {dimension} not mapped"
        row["module"] = "CIO-01"
        row["evidence_ids"] = []
        row["confidence"] = 0.0

    # Normalize confidence
    c = row.get("confidence")
    if isinstance(c, (int, float)):
        row["confidence"] = float(c)
    else:
        row["confidence"] = 0.0
    return row


def side_by_side(
    tickers: Sequence[str],
    universe: Dict[str, Dict[str, Dict[str, Any]]],
    dimension: str,
) -> Dict[str, Any]:
    rows = [company_dimension_row(t, universe.get(t) or {}, dimension=dimension) for t in tickers]
    # Relative ordering by score when all numeric — comparison presentation only
    scored = [(r["ticker"], r["score"]) for r in rows if isinstance(r.get("score"), (int, float))]
    ranking = sorted(scored, key=lambda x: x[1], reverse=True) if scored else []
    return {
        "dimension": dimension,
        "rows": rows,
        "ranking_by_passthrough_score": [{"ticker": t, "score": s} for t, s in ranking],
        "note": "Ranking uses pass-through FIRE scores only; CIO-01 does not re-score.",
    }


def key_differences(tickers: Sequence[str], universe: Dict[str, Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Surface largest score gaps across quality pillars — no new scoring."""
    diffs: List[Dict[str, Any]] = []
    if len(tickers) < 2:
        return diffs
    dimensions = (
        "business_quality_comparison",
        "growth",
        "cash_flow",
        "balance_sheet",
        "capital_allocation",
    )
    for dim in dimensions:
        board = side_by_side(tickers, universe, dim)
        scored = [
            (r["ticker"], float(r["score"]), r)
            for r in board["rows"]
            if isinstance(r.get("score"), (int, float))
        ]
        if len(scored) < 2:
            continue
        scored.sort(key=lambda x: x[1], reverse=True)
        top, bottom = scored[0], scored[-1]
        gap = top[1] - bottom[1]
        if gap <= 0:
            continue
        diffs.append(
            {
                "dimension": dim,
                "higher": top[0],
                "lower": bottom[0],
                "higher_score": top[1],
                "lower_score": bottom[1],
                "gap": round(gap, 6),
                "module": top[2].get("module"),
                "evidence_ids": list(
                    dict.fromkeys(
                        list(top[2].get("evidence_ids") or []) + list(bottom[2].get("evidence_ids") or [])
                    )
                )[:12],
                "confidence": min(float(top[2].get("confidence") or 0), float(bottom[2].get("confidence") or 0)),
                "text": (
                    f"{dim}: {top[0]} ({top[1]}) vs {bottom[0]} ({bottom[1]}) — "
                    f"gap={gap:.3f} (pass-through FIRE scores)"
                ),
            }
        )
    diffs.sort(key=lambda d: d["gap"], reverse=True)
    return diffs[:10]
