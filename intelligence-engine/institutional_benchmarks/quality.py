"""IBS quality detectors — extends IST-02 rules with suite-specific codes."""

from __future__ import annotations

import re
from typing import Any, Mapping

from institutional_benchmarks.schema import REPORT_SECTIONS


def run_quality_checks(
    report: Mapping[str, Any],
    corpus: Mapping[str, Any],
    *,
    fixture_answers_used: bool = False,
) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    sections = report.get("sections") or {}
    corpus_ids = {d.get("evidence_id") for d in (corpus.get("documents") or []) if d.get("evidence_id")}

    if not (corpus.get("documents") or []):
        failures.append({"code": "RAW_CORPUS_EMPTY", "detail": "No raw evidence documents."})

    if fixture_answers_used or report.get("fixture_answers_used") is True:
        failures.append({"code": "FIXTURE_ANSWER_USED", "detail": "Fixture answer pack forbidden in IBS."})

    if report.get("raw_evidence_only") is False:
        failures.append({"code": "RAW_EVIDENCE_NOT_USED", "detail": "Report not marked raw-evidence-only."})

    cited: set[str] = set()
    orphan_n = 0
    for key, sec in sections.items():
        if not isinstance(sec, Mapping):
            continue
        for p in sec.get("paragraphs") or []:
            if not isinstance(p, Mapping):
                continue
            eids = list(p.get("evidence_ids") or [])
            cited.update(eids)
            if not eids or p.get("orphan"):
                orphan_n += 1
                failures.append(
                    {"code": "UNSUPPORTED_CONCLUSION", "detail": f"Uncited paragraph in {key}."}
                )
            for eid in eids:
                if eid not in corpus_ids:
                    failures.append(
                        {"code": "HALLUCINATED_FACT", "detail": f"Citation {eid} not in raw corpus."}
                    )
        for item in sec.get("items") or []:
            if isinstance(item, Mapping):
                for eid in item.get("evidence_ids") or []:
                    cited.add(eid)
                    if eid not in corpus_ids:
                        failures.append(
                            {"code": "HALLUCINATED_FACT", "detail": f"Item citation {eid} missing."}
                        )

    if orphan_n:
        failures.append({"code": "PROVENANCE_MISSING", "detail": f"{orphan_n} uncited paragraph(s)."})

    if not (sections.get("evidence_contradicting") or {}).get("items"):
        failures.append({"code": "NO_COUNTER_EVIDENCE", "detail": "Counter evidence missing."})

    if not (sections.get("outstanding_unknowns") or {}).get("items"):
        failures.append({"code": "NO_UNKNOWNS", "detail": "Unknowns missing."})

    mon = sections.get("monitoring_framework") or {}
    # Accept days_30 or next_quarter + six + twelve
    has_nq = bool(mon.get("next_quarter"))
    has_6 = bool(mon.get("six_month"))
    has_12 = bool(mon.get("twelve_month"))
    has_30 = bool(mon.get("days_30") or mon.get("next_30_days"))
    if not (has_nq and has_6 and has_12):
        failures.append(
            {
                "code": "NO_MONITORING_FRAMEWORK",
                "detail": "Monitoring must include next_quarter, six_month, twelve_month.",
            }
        )
    elif not has_30 and not has_nq:
        failures.append({"code": "NO_MONITORING_FRAMEWORK", "detail": "Near-term monitoring missing."})

    peer = sections.get("peer_comparison") or {}
    if not (peer.get("paragraphs") or peer.get("peers")):
        failures.append({"code": "NO_PEER_ANALYSIS", "detail": "Peer comparison missing."})

    tl = sections.get("historical_timeline") or {}
    if not (tl.get("events") or []):
        failures.append({"code": "NO_TIMELINE", "detail": "Historical timeline missing."})

    conf = sections.get("confidence_discussion") or {}
    if conf.get("confidence") is None:
        failures.append({"code": "CONFIDENCE_UNJUSTIFIED", "detail": "Confidence missing."})
    else:
        if not conf.get("drivers_increasing_confidence") or not conf.get("drivers_reducing_confidence"):
            failures.append({"code": "CONFIDENCE_UNJUSTIFIED", "detail": "Confidence drivers incomplete."})
        if not conf.get("reason_confidence_cannot_be_higher"):
            failures.append({"code": "CONFIDENCE_UNJUSTIFIED", "detail": "Missing why confidence capped."})
        if not conf.get("missing_evidence"):
            failures.append({"code": "CONFIDENCE_UNJUSTIFIED", "detail": "Missing evidence list absent."})

    if not (sections.get("counterfactual_analysis") or {}).get("items"):
        failures.append({"code": "EVIDENCE_CHAIN_BROKEN", "detail": "Counterfactuals missing."})

    if cited and corpus_ids and len(cited & corpus_ids) == 0:
        failures.append({"code": "EVIDENCE_CHAIN_BROKEN", "detail": "No citation intersects corpus."})
        failures.append({"code": "RAW_EVIDENCE_NOT_USED", "detail": "Report citations unused corpus ids."})

    if report.get("collapsed_to_buy_sell") or report.get("buy_sell") in {"BUY", "SELL", "buy", "sell"}:
        failures.append({"code": "UNSUPPORTED_CONCLUSION", "detail": "Collapsed to BUY/SELL."})

    if re.search(r"\bas\s+a\s+fact,?\s+(i|we)\s+(believe|feel|think)\b", str(report), re.I):
        failures.append({"code": "UNSUPPORTED_CONCLUSION", "detail": "Opinion presented as fact."})

    missing_sections = [k for k in REPORT_SECTIONS if k not in sections]

    # dedupe
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
        "cited_evidence_ids": sorted(cited),
        "corpus_evidence_ids": sorted(corpus_ids),
        "citation_coverage": round(len(cited & corpus_ids) / max(1, len(corpus_ids)), 4),
        "hallucination_count": sum(1 for f in unique if f["code"] == "HALLUCINATED_FACT"),
        "broken_provenance_count": sum(1 for f in unique if f["code"] == "PROVENANCE_MISSING"),
        "unsupported_count": sum(1 for f in unique if f["code"] == "UNSUPPORTED_CONCLUSION"),
    }
