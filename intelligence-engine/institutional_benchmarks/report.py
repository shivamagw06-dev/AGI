"""Generic institutional report assembly from raw corpus + module outputs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from institutional_benchmarks.schema import REPORT_SECTIONS


def _cite(eid: str, corpus: Mapping[str, Any]) -> dict[str, Any]:
    for d in corpus.get("documents") or []:
        if d.get("evidence_id") == eid:
            return {
                "evidence_id": d.get("evidence_id"),
                "evidence_source": d.get("source"),
                "evidence_date": d.get("date"),
                "evidence_type": d.get("evidence_type"),
                "confidence_contribution": d.get("confidence_contribution"),
            }
    return {
        "evidence_id": eid,
        "evidence_source": None,
        "evidence_date": None,
        "evidence_type": None,
        "confidence_contribution": 0.0,
        "missing": True,
    }


def _para(text: str, eids: Sequence[str], corpus: Mapping[str, Any], *, kind: str = "fact") -> dict[str, Any]:
    return {
        "text": text,
        "kind": kind,
        "evidence_ids": list(eids),
        "citations": [_cite(e, corpus) for e in eids],
        "orphan": not bool(eids),
    }


def _by_type(corpus: Mapping[str, Any], *types: str) -> list[dict[str, Any]]:
    return [d for d in (corpus.get("documents") or []) if d.get("evidence_type") in types]


def _ids(docs: Sequence[Mapping[str, Any]], n: int = 3) -> list[str]:
    return [str(d.get("evidence_id")) for d in docs[:n] if d.get("evidence_id")]


def _conf_num(payload: Mapping[str, Any]) -> float:
    c = payload.get("confidence")
    if isinstance(c, (int, float)):
        return float(c)
    if isinstance(c, Mapping):
        for key in ("mean_confidence", "score", "value"):
            if isinstance(c.get(key), (int, float)):
                return float(c[key])
    return 0.55


def assemble_report(
    corpus: Mapping[str, Any],
    graph: Mapping[str, Any],
    modules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ticker = str(corpus.get("ticker") or "").upper()
    peers = list(corpus.get("peers") or [])
    title = str(corpus.get("title") or ticker)
    window = str(corpus.get("time_window") or "")
    sector = str(corpus.get("sector") or "")

    events = _by_type(corpus, "regulatory_filing", "exchange_announcement", "corporate_action", "macro")
    calls = _by_type(corpus, "earnings_call")
    fins = _by_type(corpus, "financial_statement", "quarterly_report", "annual_report")
    peers_d = _by_type(corpus, "peer_financial")
    prices = _by_type(corpus, "historical_price")
    ppts = _by_type(corpus, "investor_presentation")

    e_event = _ids(events, 2)
    e_call = _ids(calls, 2)
    e_fin = _ids(fins, 3)
    e_peer = _ids(peers_d, 3)
    e_px = _ids(prices, 1)
    e_ppt = _ids(ppts, 1)

    # Prefer module evidence ids when present
    def mod_ids(name: str, fallback: list[str]) -> list[str]:
        payload = (modules.get(name) or {}).get("payload") or {}
        ids = [str(x) for x in (payload.get("evidence_ids") or []) if x]
        return ids[:4] or fallback

    supporting = [
        {
            "claim": f"Primary case disclosures for {ticker} establish the factual event/business window.",
            "evidence_ids": e_event or e_fin,
            "citations": [_cite(e, corpus) for e in (e_event or e_fin)],
        },
        {
            "claim": "Management commentary provides operational framing that can be tested against financials.",
            "evidence_ids": e_call or e_ppt,
            "citations": [_cite(e, corpus) for e in (e_call or e_ppt)],
        },
    ]
    contradicting = [
        {
            "claim": "Financial disclosures may incompletely quantify the multi-period impact of the case event.",
            "evidence_ids": e_fin or e_event,
            "citations": [_cite(e, corpus) for e in (e_fin or e_event)],
        },
        {
            "claim": "Peer trajectories can diverge, challenging idiosyncratic vs sector interpretations.",
            "evidence_ids": e_peer or e_fin,
            "citations": [_cite(e, corpus) for e in (e_peer or e_fin)],
        },
    ]
    if not contradicting[0]["evidence_ids"]:
        contradicting = supporting  # should not happen with standard packs

    unknowns = [
        {
            "item": f"Duration and full magnitude of {ticker} case overhang beyond disclosed periods",
            "evidence_ids": e_event + e_ppt,
            "why_unknown": "Disclosures define the window but do not close all forward paths.",
        },
        {
            "item": "Relative share / franchise shift versus peers over subsequent periods",
            "evidence_ids": e_peer,
            "why_unknown": "Peer packs provide baseline, not settled relative outcomes.",
        },
        {
            "item": "Whether management execution matches stated remediation/strategy milestones",
            "evidence_ids": e_call + e_ppt,
            "why_unknown": "Calls state intent; delivery must be tracked in later evidence.",
        },
    ]

    counterfactuals = [
        {
            "condition": "If margins recover to pre-case trajectory",
            "implication": "Supports temporary/operational interpretation over structural impairment.",
            "linked_evidence_ids": e_fin,
            "linked_metrics": ["margin", "ebit"],
        },
        {
            "condition": "If deposits / demand / volumes accelerate versus peers",
            "implication": "Strengthens franchise resilience thesis.",
            "linked_evidence_ids": e_fin + e_peer,
            "linked_metrics": ["growth", "volumes"],
        },
        {
            "condition": "If leverage increases materially",
            "implication": "Raises balance-sheet risk weight in the institutional view.",
            "linked_evidence_ids": e_fin,
            "linked_metrics": ["leverage", "debt"],
        },
        {
            "condition": "If regulation or demand weakens further",
            "implication": "Would increase structural-risk weight and monitoring intensity.",
            "linked_evidence_ids": e_event + e_call,
            "linked_metrics": ["regulation", "demand"],
        },
    ]

    monitoring = {
        "days_30": [
            {
                "item": "New exchange/IR disclosures related to the case event",
                "metric": "disclosure_flow",
                "evidence_ids": e_event,
                "events": ["announcement", "clarification"],
            }
        ],
        "next_quarter": [
            {
                "item": "Next quarterly results vs case-window baselines",
                "metric": "quarterly_metrics",
                "evidence_ids": e_fin,
                "events": ["results"],
            },
            {
                "item": "Management milestone updates on calls/presentations",
                "metric": "execution_milestones",
                "evidence_ids": e_call + e_ppt,
                "events": ["earnings_call"],
            },
        ],
        "six_month": [
            {
                "item": "Relative performance vs named peers",
                "metric": "peer_relative",
                "evidence_ids": e_peer,
                "events": ["peer_results"],
            }
        ],
        "twelve_month": [
            {
                "item": "Whether case overhang persists in disclosures and financials",
                "metric": "overhang_persistence",
                "evidence_ids": e_event + e_fin,
                "events": ["annual_report", "results"],
            }
        ],
    }

    confs = [
        _conf_num((modules.get(m) or {}).get("payload") or {})
        for m in ("FIRE-01", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06", "CIO-01")
    ]
    conf_mean = round(sum(confs) / max(1, len(confs)), 3)

    timeline = []
    for d in sorted(corpus.get("documents") or [], key=lambda x: str(x.get("date") or "")):
        timeline.append(
            {
                "date": d.get("date"),
                "evidence_id": d.get("evidence_id"),
                "type": d.get("evidence_type"),
                "summary": (d.get("text") or "")[:200],
                "source": d.get("source"),
            }
        )

    sections = {
        "executive_summary": {
            "paragraphs": [
                _para(
                    f"{title} ({ticker}, {sector}). Window {window}. "
                    "Institutional view must weigh disclosed facts, management framing, peer context, "
                    "and unknowns — without collapsing to BUY/SELL.",
                    (e_event or e_fin) + e_call[:1],
                    corpus,
                    kind="interpretation",
                )
            ]
        },
        "historical_timeline": {"events": timeline},
        "what_happened": {
            "paragraphs": [
                _para(
                    (events[0].get("text") if events else f"Case disclosures for {ticker} in {window}."),
                    e_event or e_fin,
                    corpus,
                    kind="fact",
                )
            ]
        },
        "business_context": {
            "paragraphs": [
                _para(
                    (calls[0].get("text") if calls else f"Management context for {ticker}."),
                    mod_ids("FIRE-03", e_call or e_ppt),
                    corpus,
                    kind="interpretation",
                )
            ]
        },
        "financial_analysis": {
            "paragraphs": [
                _para(
                    (fins[0].get("text") if fins else f"Financial disclosures for {ticker}."),
                    mod_ids("FIRE-01", e_fin),
                    corpus,
                    kind="fact",
                )
            ],
            "module": "FIRE-01/FIRE-02",
        },
        "business_quality": {
            "paragraphs": [
                _para(
                    f"Business-quality assessment for {ticker} uses disclosed franchise/mix/margin evidence "
                    "and remains provisional where multi-period impact is incomplete.",
                    mod_ids("FIRE-06", e_fin + e_call),
                    corpus,
                    kind="interpretation",
                )
            ],
            "module": "FIRE-06",
        },
        "management_assessment": {
            "paragraphs": [
                _para(
                    "Management diagnosis must be compared with financial evidence; alignment is treated as "
                    "partial unless disclosures quantify delivery.",
                    mod_ids("FIRE-03", e_call) + mod_ids("FIRE-04", e_fin) + mod_ids("FIRE-05", e_call + e_ppt),
                    corpus,
                    kind="interpretation",
                )
            ],
            "module": "FIRE-03/04/05",
        },
        "evidence_supporting": {"items": supporting},
        "evidence_contradicting": {"items": contradicting},
        "alternative_interpretations": {
            "paragraphs": [
                _para(
                    "Temporary/operational path: execution delivers and metrics normalise versus peers.",
                    e_call + e_fin,
                    corpus,
                    kind="interpretation",
                ),
                _para(
                    "Structural path: franchise or regulatory overhang persists beyond the case window.",
                    e_event + e_peer,
                    corpus,
                    kind="interpretation",
                ),
            ]
        },
        "peer_comparison": {
            "paragraphs": [
                _para(
                    f"Peers {', '.join(peers) if peers else 'n/a'} provide relative context; "
                    "idiosyncratic vs sector framing depends on subsequent relative metrics.",
                    mod_ids("CIO-01", e_peer or e_fin),
                    corpus,
                    kind="interpretation",
                )
            ],
            "peers": peers,
            "module": "CIO-01",
        },
        "historical_context": {
            "paragraphs": [
                _para(
                    f"Historical window {window}; price/context evidence anchors market reaction where available.",
                    e_px or e_event or e_fin,
                    corpus,
                    kind="fact",
                )
            ]
        },
        "risk_assessment": {
            "paragraphs": [
                _para(
                    "Key risks: incomplete quantification, execution slippage, peer share shift, and regulatory/demand shocks.",
                    e_event + e_fin + e_peer,
                    corpus,
                    kind="interpretation",
                )
            ]
        },
        "outstanding_unknowns": {"items": unknowns},
        "monitoring_framework": monitoring,
        "confidence_discussion": {
            "confidence": conf_mean,
            "drivers_increasing_confidence": [
                {
                    "driver": "Primary case disclosures present in the raw corpus",
                    "evidence_ids": e_event or e_fin,
                },
                {
                    "driver": "Peer context available for relative framing",
                    "evidence_ids": e_peer or e_fin,
                },
            ],
            "drivers_reducing_confidence": [
                {
                    "driver": "Multi-period impact incompletely quantified",
                    "evidence_ids": e_fin or e_event,
                },
                {
                    "driver": "Forward path depends on unobserved subsequent disclosures",
                    "evidence_ids": e_ppt or e_call or e_event,
                },
            ],
            "missing_evidence": [u["item"] for u in unknowns],
            "reason_confidence_cannot_be_higher": (
                "Contradictory or incomplete quantification remains, peer relative outcomes are unsettled, "
                "and several monitoring items depend on future disclosures."
            ),
            "citations": [_cite(e, corpus) for e in (e_event or e_fin)[:2]],
        },
        "counterfactual_analysis": {
            "question": "What evidence would change this view?",
            "items": counterfactuals,
        },
        "evidence_appendix": {
            "evidence_ids": list(graph.get("evidence_ids") or []),
            "coverage_by_type": graph.get("coverage_by_type") or {},
            "documents": [
                {
                    "evidence_id": d.get("evidence_id"),
                    "source": d.get("source"),
                    "date": d.get("date"),
                    "type": d.get("evidence_type"),
                    "confidence_contribution": d.get("confidence_contribution"),
                }
                for d in (corpus.get("documents") or [])
            ],
        },
    }

    matrix = []
    for role, items in (("supporting", supporting), ("contradicting", contradicting)):
        for item in items:
            for eid in item.get("evidence_ids") or []:
                matrix.append({"role": role, "claim": item.get("claim"), **_cite(eid, corpus)})

    return {
        "schema": "ibs01.institutional_report.v1",
        "case_id": corpus.get("case_id"),
        "ticker": ticker,
        "sector": sector,
        "title": title,
        "time_window": window,
        "sections": sections,
        "section_keys": list(REPORT_SECTIONS),
        "evidence_matrix": matrix,
        "buy_sell": None,
        "collapsed_to_buy_sell": False,
        "fixture_answers_used": False,
        "raw_evidence_only": True,
        "modules_used": sorted([k for k, v in modules.items() if not k.startswith("_") and v.get("ok")]),
        "historical_cutoff": corpus.get("historical_cutoff"),
    }
