"""Framework Execution Policy — soft-wire only (not a top-level engine).

Knowledge compilation (Academy Books) is not enough. Ask AGI must *execute*
applicable frameworks (or report insufficient evidence) before narrative.

Architecture v1.0.1 LOCKED — helper under institutional_reasoning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

MODULE = "framework_execution_policy"
VERSION = "v1.0.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED soft-wire"


@dataclass(frozen=True)
class ExecutableFramework:
    """Executable policy object — not a descriptive book summary."""

    framework_id: str
    name: str
    author: str
    question_types: tuple[str, ...]
    requires: tuple[str, ...]
    produces: tuple[str, ...]
    good_for: tuple[str, ...] = ()
    bad_for: tuple[str, ...] = ()
    packs: tuple[str, ...] = ()  # which runtime packs satisfy this framework
    base_score: int = 50
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Catalog — valuation-first; expand later without new engines
# ---------------------------------------------------------------------------

FRAMEWORK_CATALOG: tuple[ExecutableFramework, ...] = (
    ExecutableFramework(
        framework_id="rel_val_damodaran",
        name="Damodaran Relative Valuation",
        author="Damodaran",
        question_types=("Valuation", "Comparison", "Sector", "Company Analysis"),
        requires=("forward_pe", "peer_pe_or_index_pe", "growth_or_roe"),
        produces=("premium_discount", "peer_relative_fair_band", "confidence"),
        good_for=("equity_index", "large_cap_IT", "peer_set_available"),
        bad_for=("pre_profit_saas_without_peers", "one_off_earnings"),
        packs=("valuation", "company_analysis", "finance_retrieval", "peer"),
        base_score=98,
        notes="Primary for 'is it expensive vs peers/history' questions.",
    ),
    ExecutableFramework(
        framework_id="hist_multiples",
        name="Historical Multiples Percentile",
        author="Institutional",
        question_types=("Valuation", "Comparison", "Sector", "Company Analysis"),
        requires=("current_pe_or_ev_ebitda", "history_5y_or_10y", "percentile"),
        produces=("historical_percentile", "vs_cycle_context", "confidence"),
        good_for=("listed_index", "stable_reporting_history"),
        bad_for=("regime_break", "accounting_change"),
        packs=("valuation", "company_analysis", "finance_retrieval"),
        base_score=96,
        notes="Answers 'expensive versus history' with evidence, not adjectives.",
    ),
    ExecutableFramework(
        framework_id="margin_of_safety",
        name="Graham Margin of Safety",
        author="Graham",
        question_types=("Valuation", "Company Analysis", "Risk Analysis"),
        requires=("intrinsic_or_asset_anchor", "price_or_multiple", "downside_case"),
        produces=("mos_pct", "speculative_vs_investment", "confidence"),
        good_for=("asset_backed", "earnings_power_stable"),
        bad_for=("pure_optionality_growth", "negative_equity_without_EPV"),
        packs=("valuation", "company_analysis"),
        base_score=88,
        notes="Rejects narrative 'fair' without a downside buffer statement.",
    ),
    ExecutableFramework(
        framework_id="dcf_damodaran",
        name="Damodaran DCF / Expected Return",
        author="Damodaran",
        question_types=("Valuation", "Company Analysis"),
        requires=("fcf_or_earnings_path", "wacc_or_cost_of_equity", "terminal_assumption"),
        produces=("intrinsic_value", "expected_cagr", "sensitivity_drivers", "confidence"),
        good_for=("stable_fcf", "forecastable_franchise"),
        bad_for=("banks", "insurance", "early_biotech", "pre_profit_saas", "commodity_peak"),
        packs=("valuation", "company_analysis"),
        base_score=84,
        notes="Must refuse when applicability fails — not force a fake DCF.",
    ),
    ExecutableFramework(
        framework_id="capital_cycle",
        name="Capital Cycle / Supply Response",
        author="Institutional",
        question_types=("Valuation", "Sector", "Macro", "Company Analysis"),
        requires=("capex_or_supply_signal", "returns_cycle", "pricing_power_hint"),
        produces=("cycle_stage", "mean_reversion_risk", "confidence"),
        good_for=("cyclicals", "capacity_industries", "IT_hiring_wage_cycle"),
        bad_for=("pure_asset_plays"),
        packs=("company_analysis", "sector_intelligence", "live_evidence"),
        base_score=72,
    ),
    ExecutableFramework(
        framework_id="expected_return",
        name="Expected Return Bridge",
        author="Institutional",
        question_types=("Valuation", "Portfolio", "Company Analysis"),
        requires=("starting_yield_or_pe", "growth", "multiple_exit_assumption"),
        produces=("expected_return_band", "bear_base_bull", "confidence"),
        good_for=("listed_equity"),
        bad_for=(),
        packs=("valuation", "company_analysis", "decision_engine"),
        base_score=90,
    ),
)


_VALUATION_HINTS = (
    "valuat",
    "expensive",
    "cheap",
    "p/e",
    "pe ",
    " pe",
    "ev/ebitda",
    "fair value",
    "intrinsic",
    "premium",
    "discount",
    "percentile",
    "multiple",
)


def _norm_question_type(
    *,
    query: str,
    ontology: dict[str, Any] | None = None,
    irsp_type: str | None = None,
) -> str:
    if irsp_type:
        return str(irsp_type)
    ont = ontology or {}
    primary = str(
        ont.get("primary")
        or ont.get("intent_family")
        or (ont.get("research_ontology") or {}).get("primary")
        or ""
    ).lower()
    if "valuat" in primary:
        return "Valuation"
    if "macro" in primary:
        return "Macro"
    if "peer" in primary or "compar" in primary:
        return "Comparison"
    if "sector" in primary:
        return "Sector"
    if "portfolio" in primary:
        return "Portfolio"
    q = (query or "").lower()
    if any(h in q for h in _VALUATION_HINTS):
        return "Valuation"
    try:
        from institutional_reasoning.planner import classify_question_type

        return classify_question_type(query)
    except Exception:
        return "Company Analysis"


def score_framework(fw: ExecutableFramework, *, question_type: str, query: str) -> int:
    score = int(fw.base_score)
    if question_type not in fw.question_types:
        return max(0, score - 40)
    q = (query or "").lower()
    if "history" in q or "historical" in q or "versus history" in q:
        if fw.framework_id == "hist_multiples":
            score += 5
        if fw.framework_id == "dcf_damodaran":
            score -= 8
    if "peer" in q or "vs" in q or "versus" in q or "nifty" in q:
        if fw.framework_id == "rel_val_damodaran":
            score += 4
    if "dcf" in q or "intrinsic" in q:
        if fw.framework_id == "dcf_damodaran":
            score += 6
    if any(b.replace("_", " ") in q for b in fw.bad_for if b in {"banks", "insurance"}):
        if fw.framework_id == "dcf_damodaran":
            score -= 30
    return max(0, min(100, score))


def select_frameworks(
    query: str,
    *,
    ontology: dict[str, Any] | None = None,
    irsp_type: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    qtype = _norm_question_type(query=query, ontology=ontology, irsp_type=irsp_type)
    ranked: list[dict[str, Any]] = []
    for fw in FRAMEWORK_CATALOG:
        if qtype not in fw.question_types and qtype != "Valuation":
            # Still allow valuation catalog when type is valuation-adjacent via hints
            if not (qtype in {"Company Analysis", "Comparison", "Sector"} and "Valuation" in fw.question_types):
                if qtype not in fw.question_types:
                    continue
        sc = score_framework(fw, question_type=qtype, query=query)
        if sc < 40:
            continue
        ranked.append(
            {
                **fw.to_dict(),
                "score": sc,
                "status": "required",
            }
        )
    ranked.sort(key=lambda x: int(x.get("score") or 0), reverse=True)
    selected = ranked[: max(1, limit)]
    # Always require at least relative + historical for pure valuation questions
    if qtype == "Valuation":
        ids = {s["framework_id"] for s in selected}
        for must in ("rel_val_damodaran", "hist_multiples", "margin_of_safety"):
            if must not in ids:
                fw = next(f for f in FRAMEWORK_CATALOG if f.framework_id == must)
                selected.append({**fw.to_dict(), "score": fw.base_score, "status": "required"})
                ids.add(must)
        selected.sort(key=lambda x: int(x.get("score") or 0), reverse=True)
        selected = selected[:6]

    return {
        "ok": True,
        "module": MODULE,
        "version": VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "query": str(query or "")[:500],
        "question_type": qtype,
        "required_frameworks": selected,
        "required_packs": sorted(
            {p for s in selected for p in (s.get("packs") or [])}
        ),
        "policy": (
            "Each required framework must execute or report insufficient evidence "
            "before narrative generation."
        ),
    }


def _has_any(blob: Any, keys: tuple[str, ...]) -> bool:
    if not isinstance(blob, dict):
        return False
    flat = " ".join(str(k).lower() for k in _walk_keys(blob))
    text = str(blob).lower()
    numeric_requires = {
        "forward_pe",
        "current_pe_or_ev_ebitda",
        "peer_pe_or_index_pe",
        "percentile",
        "mos_pct",
        "intrinsic_or_asset_anchor",
        "intrinsic_value",
        "fcf_or_earnings_path",
        "wacc_or_cost_of_equity",
        "history_5y_or_10y",
        "growth_or_roe",
        "downside_case",
        "terminal_assumption",
        "starting_yield_or_pe",
        "multiple_exit_assumption",
        "capex_or_supply_signal",
        "returns_cycle",
        "pricing_power_hint",
        "growth",
        "price_or_multiple",
    }
    for key in keys:
        # Compound requirements (a_or_b) are resolved via numeric/alias signals.
        if key in numeric_requires and _has_numeric_signal(blob, key):
            return True
        token = key.replace("_", " ")
        if key in flat or token in text or key.replace("_", "") in flat:
            if key in numeric_requires:
                continue
            return True
    return False


def _walk_keys(obj: Any, *, depth: int = 0) -> list[str]:
    if depth > 4 or not isinstance(obj, dict):
        return []
    out: list[str] = []
    for k, v in obj.items():
        out.append(str(k))
        if isinstance(v, dict):
            out.extend(_walk_keys(v, depth=depth + 1))
    return out


def _has_numeric_signal(blob: dict[str, Any], require_key: str) -> bool:
    """Heuristic: look for numbers near related field names."""
    aliases = {
        "forward_pe": ("forward_pe", "fwd_pe", "pe_fwd", "pe_forward", "trailing_pe", "pe"),
        "current_pe_or_ev_ebitda": ("pe", "ev_ebitda", "evebitda", "multiple", "trailing_pe"),
        "peer_pe_or_index_pe": ("peer_pe", "index_pe", "sector_pe", "nifty_pe", "median_pe"),
        "percentile": ("percentile", "pctile", "hist_percentile", "rank"),
        "mos_pct": ("margin_of_safety", "mos", "upside", "downside"),
        "intrinsic_or_asset_anchor": ("intrinsic", "fair_value", "epv", "nav", "asset_value"),
        "intrinsic_value": ("intrinsic", "dcf_value", "fair_value"),
        "fcf_or_earnings_path": ("fcf", "fcff", "fcfe", "earnings", "eps"),
        "wacc_or_cost_of_equity": ("wacc", "cost_of_equity", "discount_rate", "ke"),
        "history_5y_or_10y": ("5y", "10y", "history", "historical", "avg_pe", "hist_percentile"),
        "growth_or_roe": ("growth", "roe", "roic", "cagr"),
        "growth": ("growth", "cagr", "roe"),
        "downside_case": ("bear", "downside", "stress", "bear_case"),
        "terminal_assumption": ("terminal", "exit_multiple", "perpetuity", "terminal_growth"),
        "starting_yield_or_pe": ("earnings_yield", "pe", "dividend_yield", "forward_pe", "trailing_pe"),
        "multiple_exit_assumption": ("exit", "terminal", "normalize", "exit_multiple"),
        "price_or_multiple": ("price", "pe", "multiple", "forward_pe", "trailing_pe"),
        "capex_or_supply_signal": ("capex", "supply", "capacity", "hiring"),
        "returns_cycle": ("roic", "roe", "cycle"),
        "pricing_power_hint": ("pricing", "margin", "power"),
    }
    wanted = aliases.get(require_key, (require_key,))
    stack: list[Any] = [blob]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = str(k).lower()
                if any(a in kl for a in wanted):
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        # Zero is commonly a missing-provider placeholder, not a
                        # usable valuation input (for example NIFTYIT 52w range).
                        if v != 0:
                            return True
                    if isinstance(v, str):
                        compact = v.replace(",", "")
                        if any(ch.isdigit() for ch in compact) and compact not in {
                            "0",
                            "0.0",
                            "0.00",
                            "0%",
                            "0.0%",
                            "0.00%",
                        }:
                            return True
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur[:20])
    return False


def _expected_symbols(query: str) -> set[str]:
    """Canonical entities for known index questions; never use another entity's model."""
    q = (query or "").lower()
    expected: set[str] = set()
    if "nifty it" in q or "niftyit" in q:
        expected.add("NIFTYIT")
    if "nifty bank" in q or "bank nifty" in q or "niftybank" in q:
        expected.add("NIFTYBANK")
    if "nifty 50" in q or "nifty50" in q:
        expected.add("NIFTY50")
    return expected


def _valuation_target_mismatch(
    query: str,
    valuation: dict[str, Any] | None,
    company_analysis: dict[str, Any] | None,
) -> str | None:
    """Fail closed when the valuation model belongs to a different security."""
    expected = _expected_symbols(query)
    if not expected:
        return None
    symbols: set[str] = set()
    val = valuation or {}
    company = val.get("company") if isinstance(val.get("company"), dict) else {}
    for candidate in (
        company.get("company_symbol"),
        company.get("symbol"),
        val.get("ticker"),
    ):
        if candidate:
            symbols.add(str(candidate).upper().replace("^", ""))
    if not symbols:
        return f"target entity unresolved; expected {', '.join(sorted(expected))}"
    if not (expected & symbols):
        return (
            f"valuation model targets {', '.join(sorted(symbols))}, not "
            f"{', '.join(sorted(expected))}"
        )
    return None


def _pack_map(
    *,
    valuation: dict[str, Any] | None,
    company_analysis: dict[str, Any] | None,
    finance_retrieval: dict[str, Any] | None,
    sector_intelligence: dict[str, Any] | None,
    live_evidence: dict[str, Any] | None,
    decision_engine: dict[str, Any] | None,
    peer: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "valuation": valuation if isinstance(valuation, dict) else {},
        "company_analysis": company_analysis if isinstance(company_analysis, dict) else {},
        "finance_retrieval": finance_retrieval if isinstance(finance_retrieval, dict) else {},
        "sector_intelligence": sector_intelligence if isinstance(sector_intelligence, dict) else {},
        "live_evidence": live_evidence if isinstance(live_evidence, dict) else {},
        "decision_engine": decision_engine if isinstance(decision_engine, dict) else {},
        "peer": peer if isinstance(peer, dict) else {},
    }


def evaluate_frameworks(
    selection: dict[str, Any],
    *,
    valuation: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    finance_retrieval: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    decision_engine: dict[str, Any] | None = None,
    peer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packs = _pack_map(
        valuation=valuation,
        company_analysis=company_analysis,
        finance_retrieval=finance_retrieval,
        sector_intelligence=sector_intelligence,
        live_evidence=live_evidence,
        decision_engine=decision_engine,
        peer=peer,
    )
    # Merge CA valuation slice into valuation blob for requirement checks
    ca_val = {}
    if isinstance(company_analysis, dict):
        ca_val = company_analysis.get("valuation_intelligence") or company_analysis.get("valuation") or {}
    merged_val = {**(valuation or {}), **(ca_val if isinstance(ca_val, dict) else {})}
    packs["valuation"] = merged_val
    target_mismatch = _valuation_target_mismatch(
        str(selection.get("query") or ""),
        valuation,
        company_analysis,
    )

    results: list[dict[str, Any]] = []
    missing_all: list[str] = []
    executed = 0
    insufficient = 0
    rejected = 0

    for fw in selection.get("required_frameworks") or []:
        fw_id = str(fw.get("framework_id") or "")
        requires = tuple(fw.get("requires") or ())
        bad_for = tuple(fw.get("bad_for") or ())
        pack_names = tuple(fw.get("packs") or ())
        evidence_blob: dict[str, Any] = {}
        for pn in pack_names:
            evidence_blob.update(packs.get(pn) or {})

        if target_mismatch and fw_id in {
            "rel_val_damodaran",
            "hist_multiples",
            "margin_of_safety",
            "dcf_damodaran",
            "expected_return",
        }:
            insufficient += 1
            missing_all.append("target_matched_valuation_evidence")
            results.append(
                {
                    "framework_id": fw_id,
                    "name": fw.get("name"),
                    "author": fw.get("author"),
                    "score": fw.get("score"),
                    "status": "insufficient_evidence",
                    "missing": ["target_matched_valuation_evidence"],
                    "produces": fw.get("produces") or [],
                    "detail": f"Insufficient evidence: {target_mismatch}.",
                }
            )
            continue

        # Applicability reject (e.g. DCF on banks) when signals present
        applicability_fail = False
        blob_text = str(evidence_blob).lower() + " " + str(company_analysis or {}).lower()
        for bad in bad_for:
            token = bad.replace("_", " ")
            if token in blob_text and fw_id == "dcf_damodaran":
                # Only reject when sector hint clearly matches
                if bad in {"banks", "insurance"} and any(
                    t in blob_text for t in ("bank", "insurance", "nbfc", "life insurance")
                ):
                    applicability_fail = True
                    break

        if applicability_fail:
            rejected += 1
            results.append(
                {
                    "framework_id": fw_id,
                    "name": fw.get("name"),
                    "author": fw.get("author"),
                    "score": fw.get("score"),
                    "status": "rejected_not_applicable",
                    "missing": [],
                    "produces": fw.get("produces") or [],
                    "detail": f"Framework rejected: not applicable ({', '.join(bad_for[:3])}).",
                }
            )
            continue

        missing = [r for r in requires if not _has_any(evidence_blob, (r,))]
        if missing:
            insufficient += 1
            missing_all.extend(missing)
            results.append(
                {
                    "framework_id": fw_id,
                    "name": fw.get("name"),
                    "author": fw.get("author"),
                    "score": fw.get("score"),
                    "status": "insufficient_evidence",
                    "missing": missing,
                    "produces": fw.get("produces") or [],
                    "detail": "Insufficient evidence: " + ", ".join(missing),
                }
            )
        else:
            executed += 1
            results.append(
                {
                    "framework_id": fw_id,
                    "name": fw.get("name"),
                    "author": fw.get("author"),
                    "score": fw.get("score"),
                    "status": "executed",
                    "missing": [],
                    "produces": fw.get("produces") or [],
                    "detail": "Framework requirements present in evidence packs.",
                }
            )

    required_n = len(selection.get("required_frameworks") or [])
    # Sufficiency: at least one top framework executed OR explicit insufficient report
    top = results[:2]
    top_ok = any(r.get("status") == "executed" for r in top) if top else False
    narrative_allowed = True
    gate_reason = None
    qtype = selection.get("question_type")
    if qtype == "Valuation" and not top_ok:
        narrative_allowed = False
        gate_reason = (
            "Valuation question blocked from unsupported narrative: "
            "required frameworks lack evidence (historical/relative multiples)."
        )

    unique_missing = list(dict.fromkeys(missing_all))
    return {
        "ok": True,
        "module": MODULE,
        "version": VERSION,
        "question_type": qtype,
        "required_frameworks": selection.get("required_frameworks") or [],
        "results": results,
        "executed": executed,
        "insufficient": insufficient,
        "rejected_not_applicable": rejected,
        "required_count": required_n,
        "missing_evidence": unique_missing[:20],
        "narrative_allowed": narrative_allowed,
        "gate_reason": gate_reason,
        "sufficient": top_ok,
        "summary": _summary_line(results, narrative_allowed),
    }


def _summary_line(results: list[dict[str, Any]], narrative_allowed: bool) -> str:
    parts = []
    for r in results[:4]:
        st = r.get("status")
        name = r.get("name") or r.get("framework_id")
        if st == "executed":
            parts.append(f"{name}: executed")
        elif st == "insufficient_evidence":
            miss = ", ".join((r.get("missing") or [])[:3])
            parts.append(f"{name}: insufficient ({miss})")
        elif st == "rejected_not_applicable":
            parts.append(f"{name}: not applicable")
    suffix = "narrative allowed" if narrative_allowed else "narrative withheld pending evidence"
    return (" · ".join(parts) + f" — {suffix}") if parts else suffix


def ask_agi_hints(report: dict[str, Any], *, limit: int = 6) -> list[str]:
    hints: list[str] = []
    qtype = report.get("question_type")
    if qtype:
        hints.append(f"Execution policy: question typed as {qtype}; frameworks must run or report gaps.")
    for r in report.get("results") or []:
        st = r.get("status")
        name = r.get("name") or r.get("framework_id")
        author = r.get("author") or ""
        label = f"{name}" + (f" ({author})" if author else "")
        if st == "executed":
            hints.append(f"Framework executed: {label}.")
        elif st == "insufficient_evidence":
            miss = ", ".join((r.get("missing") or [])[:4])
            hints.append(f"Framework insufficient: {label} — missing {miss}.")
        elif st == "rejected_not_applicable":
            hints.append(f"Framework rejected as not applicable: {label}.")
        if len(hints) >= limit:
            break
    if report.get("gate_reason"):
        hints.insert(0, str(report["gate_reason"])[:420])
    if report.get("missing_evidence"):
        hints.append(
            "Missing valuation evidence: " + ", ".join(report["missing_evidence"][:6]) + "."
        )
    # de-dupe
    out: list[str] = []
    for h in hints:
        t = str(h).strip()
        if t and t not in out:
            out.append(t[:420])
        if len(out) >= limit:
            break
    return out


def soft_slice_for_ask_agi(
    query: str,
    *,
    ontology: dict[str, Any] | None = None,
    irsp_type: str | None = None,
) -> dict[str, Any]:
    """Select required frameworks for the question (planner stage)."""
    return select_frameworks(query, ontology=ontology, irsp_type=irsp_type)


def finalize_for_ask_agi(
    selection: dict[str, Any],
    **packs: Any,
) -> dict[str, Any]:
    """Evaluate packs against required frameworks (post VE/FRE/CA)."""
    report = evaluate_frameworks(selection, **packs)
    report["ask_agi_hints"] = ask_agi_hints(report)
    report["selection"] = {
        "question_type": selection.get("question_type"),
        "required_frameworks": [
            {
                "framework_id": f.get("framework_id"),
                "name": f.get("name"),
                "author": f.get("author"),
                "score": f.get("score"),
            }
            for f in (selection.get("required_frameworks") or [])
        ],
    }
    return report


def enforce_valuation_narrative(
    *,
    executive: str | None,
    house_label: str | None,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Replace unsupported valuation adjectives when policy withholds narrative."""
    out = {
        "executive": executive,
        "house_label": house_label,
        "rewritten": False,
    }
    if report.get("narrative_allowed", True):
        return out
    missing = ", ".join((report.get("missing_evidence") or [])[:6]) or "key valuation inputs"
    msg = (
        f"Valuation coverage incomplete — required frameworks could not execute "
        f"(missing: {missing}). Refuse unsupported 'fair/expensive' language until "
        f"historical multiples, relative valuation, and margin-of-safety evidence are present."
    )
    out["executive"] = msg
    if house_label and str(house_label).lower() in {"buy", "sell", "hold", "fair", "expensive", "cheap"}:
        out["house_label"] = "Insufficient evidence"
    elif not house_label:
        out["house_label"] = "Insufficient evidence"
    out["rewritten"] = True
    return out
