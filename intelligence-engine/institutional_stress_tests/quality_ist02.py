"""IST-02 quality detectors — failure codes from assembled report."""

from __future__ import annotations

import re
from typing import Any, Mapping

from institutional_stress_tests.schema_ist02 import IST02_REPORT_SECTIONS


def run_quality_checks(
    report: Mapping[str, Any],
    corpus: Mapping[str, Any],
    *,
    fixture_answers_used: bool = False,
) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    sections = report.get("sections") or {}
    corpus_ids = {d.get("evidence_id") for d in (corpus.get("documents") or [])}

    if not (corpus.get("documents") or []):
        failures.append({"code": "RAW_CORPUS_EMPTY", "detail": "No raw evidence documents loaded."})

    if fixture_answers_used or report.get("fixture_answers_used") is True:
        failures.append(
            {"code": "FIXTURE_ANSWER_USED", "detail": "IST-02 forbids fixture institutional answer packs."}
        )

    # Structure
    missing_sections = [k for k in IST02_REPORT_SECTIONS if k not in sections]
    # Provenance / unsupported
    orphan_n = 0
    cited_ids: set[str] = set()
    for key, sec in sections.items():
        if not isinstance(sec, Mapping):
            continue
        for p in sec.get("paragraphs") or []:
            if not isinstance(p, Mapping):
                continue
            eids = list(p.get("evidence_ids") or [])
            cited_ids.update(eids)
            if p.get("orphan") or not eids:
                orphan_n += 1
                if p.get("kind") == "interpretation" or key in {
                    "executive_summary",
                    "business_quality",
                    "management_assessment",
                }:
                    failures.append(
                        {
                            "code": "UNSUPPORTED_CONCLUSION",
                            "detail": f"Paragraph in {key} lacks evidence citations.",
                        }
                    )
            for eid in eids:
                if eid not in corpus_ids:
                    failures.append(
                        {
                            "code": "HALLUCINATED_FACT",
                            "detail": f"Citation {eid} not present in raw corpus.",
                        }
                    )
        for item in sec.get("items") or []:
            if isinstance(item, Mapping):
                for eid in item.get("evidence_ids") or []:
                    cited_ids.add(eid)
                    if eid not in corpus_ids:
                        failures.append(
                            {
                                "code": "HALLUCINATED_FACT",
                                "detail": f"Item citation {eid} not in raw corpus.",
                            }
                        )

    if orphan_n > 0:
        failures.append(
            {
                "code": "PROVENANCE_MISSING",
                "detail": f"{orphan_n} paragraph(s) without evidence linkage.",
            }
        )

    # Counter evidence
    contra = sections.get("evidence_contradicting") or {}
    if not (contra.get("items") or []):
        failures.append({"code": "NO_COUNTER_EVIDENCE", "detail": "No contradictory evidence section items."})

    # Unknowns
    unk = sections.get("outstanding_unknowns") or {}
    if not (unk.get("items") or []):
        failures.append({"code": "NO_UNKNOWNS", "detail": "Outstanding unknowns missing."})

    # Monitoring
    mon = sections.get("monitoring_framework") or {}
    if not (mon.get("next_quarter") and mon.get("six_month") and mon.get("twelve_month")):
        failures.append(
            {
                "code": "NO_MONITORING_FRAMEWORK",
                "detail": "Monitoring framework must include next_quarter, six_month, twelve_month.",
            }
        )
    else:
        for horizon in ("next_quarter", "six_month", "twelve_month"):
            for item in mon.get(horizon) or []:
                if not item.get("evidence_ids") and not item.get("metric"):
                    failures.append(
                        {
                            "code": "NO_MONITORING_FRAMEWORK",
                            "detail": f"Monitoring item in {horizon} lacks evidence/metric link.",
                        }
                    )

    # Confidence justification
    conf = sections.get("confidence_discussion") or {}
    if not isinstance(conf, Mapping) or conf.get("confidence") is None:
        failures.append({"code": "CONFIDENCE_UNJUSTIFIED", "detail": "Confidence value missing."})
    else:
        if not conf.get("drivers_increasing_confidence") or not conf.get("drivers_reducing_confidence"):
            failures.append(
                {
                    "code": "CONFIDENCE_UNJUSTIFIED",
                    "detail": "Confidence must list increasing and reducing drivers.",
                }
            )
        if not conf.get("reason_confidence_cannot_be_higher"):
            failures.append(
                {
                    "code": "CONFIDENCE_UNJUSTIFIED",
                    "detail": "Missing reason confidence cannot be higher.",
                }
            )
        if not conf.get("missing_evidence"):
            failures.append(
                {
                    "code": "CONFIDENCE_UNJUSTIFIED",
                    "detail": "Confidence block must list missing evidence.",
                }
            )

    # Peer comparison
    peer = sections.get("peer_comparison") or {}
    peer_paras = peer.get("paragraphs") or []
    if not peer_paras and not peer.get("peers"):
        failures.append({"code": "PEER_ANALYSIS_MISSING", "detail": "Peer comparison section empty."})

    # Counterfactual
    cf = sections.get("counterfactual_analysis") or {}
    if not (cf.get("items") or []):
        failures.append(
            {
                "code": "EVIDENCE_CHAIN_BROKEN",
                "detail": "Counterfactual analysis ('what would change this conclusion?') missing.",
            }
        )

    # Opinion-as-fact heuristic
    blob = str(report)
    if re.search(r"\bas\s+a\s+fact,?\s+(i|we)\s+(believe|feel|think)\b", blob, re.I):
        failures.append(
            {
                "code": "UNSUPPORTED_CONCLUSION",
                "detail": "Opinion language presented as fact.",
            }
        )

    # BUY/SELL collapse
    if report.get("collapsed_to_buy_sell") or report.get("buy_sell") in {"BUY", "SELL", "buy", "sell"}:
        failures.append(
            {
                "code": "UNSUPPORTED_CONCLUSION",
                "detail": "Report collapsed to BUY/SELL rather than institutional research view.",
            }
        )

    # Evidence chain: cited subset of corpus
    if cited_ids and corpus_ids and len(cited_ids & corpus_ids) == 0:
        failures.append(
            {
                "code": "EVIDENCE_CHAIN_BROKEN",
                "detail": "No citations intersect the raw corpus evidence ids.",
            }
        )

    # Dedupe
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for f in failures:
        key = f["code"] + "|" + f["detail"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)

    codes = sorted({f["code"] for f in unique})
    return {
        "ok": len(codes) == 0,
        "failures": unique,
        "failure_codes": codes,
        "missing_sections": missing_sections,
        "cited_evidence_ids": sorted(cited_ids),
        "corpus_evidence_ids": sorted(x for x in corpus_ids if x),
        "citation_coverage": round(len(cited_ids & corpus_ids) / max(1, len(corpus_ids)), 4),
    }
