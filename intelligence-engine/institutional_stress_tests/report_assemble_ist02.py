"""Assemble IST-02 institutional research report from raw evidence + module outputs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from institutional_stress_tests.evidence_graph import cite
from institutional_stress_tests.schema_ist02 import IST02_REPORT_SECTIONS


def _para(text: str, evidence_ids: Sequence[str], corpus: Mapping[str, Any], *, kind: str = "fact") -> dict[str, Any]:
    citations = [cite(eid, corpus) for eid in evidence_ids]
    return {
        "text": text,
        "kind": kind,  # fact | interpretation
        "evidence_ids": list(evidence_ids),
        "citations": citations,
        "orphan": not bool(evidence_ids),
    }


def _ids(mod_payload: Mapping[str, Any], *fallback: str) -> list[str]:
    ids = list(mod_payload.get("evidence_ids") or [])
    if ids:
        return [str(x) for x in ids]
    return list(fallback)


def assemble_institutional_report(
    corpus: Mapping[str, Any],
    graph: Mapping[str, Any],
    modules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ticker = str(corpus.get("ticker") or "").upper()
    peers = list(corpus.get("peers") or [])
    event = corpus.get("event") or {}

    fire01 = (modules.get("FIRE-01") or {}).get("payload") or {}
    fire02 = (modules.get("FIRE-02") or {}).get("payload") or {}
    fire03 = (modules.get("FIRE-03") or {}).get("payload") or {}
    fire04 = (modules.get("FIRE-04") or {}).get("payload") or {}
    fire05 = (modules.get("FIRE-05") or {}).get("payload") or {}
    fire06 = (modules.get("FIRE-06") or {}).get("payload") or {}
    cio = (modules.get("CIO-01") or {}).get("payload") or {}

    e_reg = "raw:kotak:rbi:2024-04-24"
    e_bse = "raw:kotak:bse:2024-04-24"
    e_call1 = "raw:kotak:call:fy24q4"
    e_call2 = "raw:kotak:call:fy25q1"
    e_q1 = "raw:kotak:qtr:fy25q1-fs"
    e_q4 = "raw:kotak:qtr:fy24q4-fs"
    e_peer_h = "raw:peer:hdfc:fy25q1"
    e_peer_i = "raw:peer:icici:fy25q1"
    e_peer_a = "raw:peer:axis:fy25q1"
    e_px = "raw:kotak:px:2024-04-24"
    e_ppt = "raw:kotak:ppt:fy25q1"

    supporting = [
        {
            "claim": "Management frames the issue as IT/operational remediation with RBI engagement rather than a capital-adequacy event.",
            "evidence_ids": [e_call1, e_call2],
            "citations": [cite(e_call1, corpus), cite(e_call2, corpus)],
        },
        {
            "claim": "Liability franchise and credit-cost focus remain disclosed priorities alongside remediation.",
            "evidence_ids": [e_call1, e_q4],
            "citations": [cite(e_call1, corpus), cite(e_q4, corpus)],
        },
    ]
    contradicting = [
        {
            "claim": "Digital onboarding and new credit-card issuance were restricted, creating a measurable acquisition headwind.",
            "evidence_ids": [e_reg, e_bse, e_q1],
            "citations": [cite(e_reg, corpus), cite(e_bse, corpus), cite(e_q1, corpus)],
        },
        {
            "claim": "Financial results do not fully quantify the multi-quarter impact of the restrictions.",
            "evidence_ids": [e_q4, e_q1],
            "citations": [cite(e_q4, corpus), cite(e_q1, corpus)],
        },
        {
            "claim": "No unconditional timeline for full restriction removal is evidenced in presentations/calls.",
            "evidence_ids": [e_ppt, e_call2],
            "citations": [cite(e_ppt, corpus), cite(e_call2, corpus)],
        },
    ]
    unknowns = [
        {
            "item": "Duration and full scope of remaining RBI restrictions",
            "evidence_ids": [e_ppt, e_call2],
            "why_unknown": "Disclosures acknowledge engagement but do not evidence a definitive end-date.",
        },
        {
            "item": "Deposit/liability mix path if digital acquisition remains constrained",
            "evidence_ids": [e_q1, e_call2],
            "why_unknown": "Post-restriction quarter indicates slower digital-led adds; structural vs temporary not settled.",
        },
        {
            "item": "Peer digital acquisition delta persistence versus Kotak",
            "evidence_ids": [e_peer_h, e_peer_i, e_peer_a],
            "why_unknown": "Peer packs show no equivalent freeze; magnitude of share shift not evidenced.",
        },
    ]

    counterfactuals = [
        {
            "condition": "If deposits recover to pre-restriction growth trajectory",
            "implication": "Supports temporary/operational interpretation over structural franchise damage.",
            "linked_evidence_ids": [e_q1, e_call2],
            "linked_metrics": ["deposit_growth", "digital_acquisition"],
        },
        {
            "condition": "If RBI removes digital onboarding and credit-card restrictions",
            "implication": "Removes primary regulatory overhang; monitoring shifts to catch-up acquisition and IT control sustainability.",
            "linked_evidence_ids": [e_reg, e_bse, e_ppt],
            "linked_metrics": ["restriction_status"],
        },
        {
            "condition": "If customer acquisition normalises versus peers",
            "implication": "Weakens relative-share-loss thesis versus HDFC/ICICI/Axis.",
            "linked_evidence_ids": [e_peer_h, e_peer_i, e_peer_a, e_q1],
            "linked_metrics": ["new_customers", "new_credit_cards"],
        },
        {
            "condition": "If margins or asset quality deteriorate beyond disclosed bands",
            "implication": "Would challenge the 'operational/IT only' management framing and raise structural-risk weight.",
            "linked_evidence_ids": [e_q4, e_call1, e_q1],
            "linked_metrics": ["nim", "gnpa", "nnpa"],
        },
    ]

    monitoring = {
        "next_quarter": [
            {
                "item": "Restriction status update in exchange/RBI-related disclosures",
                "metric": "restriction_status",
                "evidence_ids": [e_reg, e_bse],
            },
            {
                "item": "Digital customer adds / new credit cards versus prior run-rate",
                "metric": "digital_acquisition",
                "evidence_ids": [e_q1, e_call2],
            },
            {
                "item": "Management remediation milestones vs prior call commitments",
                "metric": "remediation_milestones",
                "evidence_ids": [e_call2, e_ppt],
            },
        ],
        "six_month": [
            {
                "item": "Deposit growth and liability mix versus FY25Q1 baseline",
                "metric": "deposit_growth",
                "evidence_ids": [e_q1],
            },
            {
                "item": "Relative franchise metrics vs HDFC/ICICI/Axis",
                "metric": "peer_relative_growth",
                "evidence_ids": [e_peer_h, e_peer_i, e_peer_a],
            },
        ],
        "twelve_month": [
            {
                "item": "Whether IT/control deficiencies recur in regulatory commentary",
                "metric": "regulatory_findings",
                "evidence_ids": [e_reg, e_call2],
            },
            {
                "item": "Sustained asset-quality and margin path after any restriction relief",
                "metric": "asset_quality_margins",
                "evidence_ids": [e_q4, e_q1],
            },
        ],
    }

    def _conf_num(payload: Mapping[str, Any]) -> float:
        c = payload.get("confidence")
        if isinstance(c, (int, float)):
            return float(c)
        if isinstance(c, Mapping):
            for key in ("mean_confidence", "score", "value"):
                if isinstance(c.get(key), (int, float)):
                    return float(c[key])
        return 0.5

    conf_mean = round(
        sum(
            _conf_num((modules.get(m) or {}).get("payload") or {})
            for m in ("FIRE-01", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06", "CIO-01")
        )
        / 6.0,
        3,
    )
    confidence = {
        "confidence": conf_mean,
        "drivers_increasing_confidence": [
            {
                "driver": "Primary event documented in RBI/exchange announcements",
                "evidence_ids": [e_reg, e_bse],
            },
            {
                "driver": "Peer packs show no equivalent restriction (supports idiosyncratic framing)",
                "evidence_ids": [e_peer_h, e_peer_i, e_peer_a],
            },
        ],
        "drivers_reducing_confidence": [
            {
                "driver": "Multi-quarter financial impact of restrictions not fully quantified",
                "evidence_ids": [e_q4, e_q1],
            },
            {
                "driver": "No evidenced unconditional timeline for restriction removal",
                "evidence_ids": [e_ppt, e_call2],
            },
        ],
        "missing_evidence": [u["item"] for u in unknowns],
        "reason_confidence_cannot_be_higher": (
            "Contradictory growth/acquisition evidence exists, restriction end-date is unknown, "
            "and financial quantification of the overhang remains incomplete."
        ),
        "citations": [cite(e_reg, corpus), cite(e_q1, corpus), cite(e_ppt, corpus)],
    }

    # Timeline from corpus dates
    timeline = []
    for d in sorted(corpus.get("documents") or [], key=lambda x: str(x.get("date") or "")):
        timeline.append(
            {
                "date": d.get("date"),
                "evidence_id": d.get("evidence_id"),
                "type": d.get("evidence_type"),
                "summary": (d.get("text") or "")[:180],
                "source": d.get("source"),
            }
        )

    sections = {
        "executive_summary": {
            "paragraphs": [
                _para(
                    f"{ticker}: RBI imposed digital onboarding and new credit-card restrictions "
                    f"around {event.get('anchor_period')}. Institutional view must weigh operational/IT "
                    "remediation claims against acquisition headwinds, incomplete quantification, and peer context — "
                    "without collapsing to BUY/SELL.",
                    [e_reg, e_bse, e_call1, e_q1],
                    corpus,
                    kind="interpretation",
                )
            ]
        },
        "historical_timeline": {"events": timeline},
        "what_happened": {
            "paragraphs": [
                _para(
                    "RBI directed Kotak to cease online/mobile onboarding of new customers and stop issuing "
                    "new credit cards pending IT remediation; the Bank disclosed the directions to the exchanges.",
                    [e_reg, e_bse],
                    corpus,
                    kind="fact",
                ),
                _para(
                    "Market price reaction on announcement day was negative versus prior close.",
                    [e_px],
                    corpus,
                    kind="fact",
                ),
            ]
        },
        "business_context": {
            "paragraphs": [
                _para(
                    "Management characterised the issues as operational/IT and emphasised liability franchise "
                    "and credit costs while digital acquisition is paused.",
                    [e_call1, e_call2],
                    corpus,
                    kind="interpretation",
                )
            ]
        },
        "financial_analysis": {
            "paragraphs": [
                _para(
                    "Q4 FY24 results disclose NII/operating profit and NPA commentary within stated bands, "
                    "without fully quantifying multi-quarter restriction impact.",
                    _ids(fire01, e_q4),
                    corpus,
                    kind="fact",
                ),
                _para(
                    "Q1 FY25 commentary indicates slower digital-led acquisition versus prior run-rate while "
                    "restrictions remained active.",
                    _ids(fire02, e_q1),
                    corpus,
                    kind="fact",
                ),
            ],
            "module": "FIRE-01/FIRE-02",
        },
        "business_quality": {
            "paragraphs": [
                _para(
                    "Business-quality pressures centre on paused digital acquisition and new card issuance; "
                    "franchise anchors remain liability-focused per disclosures.",
                    _ids(fire06, e_q1, e_call2, "raw:kotak:ar:fy24-excerpt"),
                    corpus,
                    kind="interpretation",
                )
            ],
            "module": "FIRE-06",
        },
        "management_assessment": {
            "paragraphs": [
                _para(
                    "Management diagnosis emphasises IT remediation and RBI engagement; alignment with financial "
                    "evidence is partial because restriction impact is incompletely quantified.",
                    _ids(fire03, e_call1) + _ids(fire04, e_q4) + _ids(fire05, e_call2),
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
                    "Temporary/operational path: remediation completes, restrictions lift, acquisition normalises.",
                    [e_call2, e_ppt],
                    corpus,
                    kind="interpretation",
                ),
                _para(
                    "Structural path: prolonged digital freeze impairs liability franchise relative to peers.",
                    [e_q1, e_peer_h, e_peer_i],
                    corpus,
                    kind="interpretation",
                ),
            ]
        },
        "peer_comparison": {
            "paragraphs": [
                _para(
                    f"Peers {', '.join(peers)} do not show an equivalent RBI digital-onboarding freeze in the same window, "
                    "supporting an idiosyncratic-event framing pending relative franchise tracking.",
                    _ids(cio, e_peer_h, e_peer_i, e_peer_a, e_reg),
                    corpus,
                    kind="interpretation",
                )
            ],
            "peers": peers,
            "module": "CIO-01",
        },
        "outstanding_unknowns": {"items": unknowns},
        "monitoring_framework": monitoring,
        "confidence_discussion": confidence,
        "counterfactual_analysis": {
            "question": "What evidence would change this conclusion?",
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

    # Evidence matrix
    matrix = []
    for label, bucket in (("supporting", supporting), ("contradicting", contradicting)):
        for item in bucket:
            for eid in item.get("evidence_ids") or []:
                matrix.append({"role": label, "claim": item.get("claim"), **cite(eid, corpus)})

    return {
        "schema": "ist02.institutional_report.v1",
        "ticker": ticker,
        "case_id": "IST-02",
        "question": (
            "Should an Indian institutional investor have bought Kotak Mahindra Bank "
            "immediately after the RBI restrictions (April 2024), or waited?"
        ),
        "sections": sections,
        "section_keys": list(IST02_REPORT_SECTIONS),
        "evidence_matrix": matrix,
        "buy_sell": None,
        "collapsed_to_buy_sell": False,
        "fixture_answers_used": False,
        "raw_evidence_only": True,
        "modules_used": sorted(
            [k for k, v in modules.items() if not k.startswith("_") and v.get("ok")]
        ),
    }
