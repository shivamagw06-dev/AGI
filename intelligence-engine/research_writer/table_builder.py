"""Automatic institutional summary tables when supporting structure exists."""

from __future__ import annotations

from typing import Any

from research_writer.language_quality import is_placeholder, scrub_leaks


def _rows_from_sections(sections: dict[str, Any], keys: list[tuple[str, str]]) -> list[dict[str, str]]:
    rows = []
    for label, key in keys:
        val = sections.get(key)
        if isinstance(val, dict):
            # flatten first meaningful
            for sk, sv in val.items():
                if not is_placeholder(sv):
                    rows.append({"metric": scrub_leaks(f"{label} · {sk}", limit=60), "value": scrub_leaks(sv, limit=80)})
                    break
        elif not is_placeholder(val):
            rows.append({"metric": label, "value": scrub_leaks(val, limit=120)})
    return rows


def build_tables(
    *,
    opinions: dict[str, dict[str, Any]],
    cio: dict[str, Any],
    committee: dict[str, Any],
) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    fin = (opinions or {}).get("financial") or {}
    fin_sec = fin.get("sections") if isinstance(fin.get("sections"), dict) else {}
    fin_rows = _rows_from_sections(
        fin_sec,
        [
            ("Revenue", "revenue"),
            ("Margins", "margins"),
            ("ROE", "roe"),
            ("ROIC", "roic"),
            ("Cash flow", "cash_flow"),
            ("Debt", "debt"),
        ],
    )
    if fin_rows:
        tables.append({"id": "financial_summary", "title": "Financial Summary", "rows": fin_rows[:8]})

    val = (opinions or {}).get("valuation") or {}
    val_sec = val.get("sections") if isinstance(val.get("sections"), dict) else {}
    multiples = val_sec.get("current_multiples") if isinstance(val_sec.get("current_multiples"), dict) else {}
    val_rows = []
    for k, label in (("pe", "P/E"), ("forward_pe", "Forward P/E"), ("pb", "P/B"), ("peg", "PEG")):
        if multiples.get(k) not in (None, "", "n/a"):
            val_rows.append({"metric": label, "value": scrub_leaks(multiples.get(k), limit=40)})
    if val_sec.get("margin_of_safety") and not is_placeholder(val_sec.get("margin_of_safety")):
        val_rows.append({"metric": "Margin of safety", "value": scrub_leaks(val_sec.get("margin_of_safety"), limit=100)})
    if val_rows:
        tables.append({"id": "valuation_summary", "title": "Valuation Summary", "rows": val_rows[:8]})

    risk = (opinions or {}).get("risk") or {}
    risk_sec = risk.get("sections") if isinstance(risk.get("sections"), dict) else {}
    risk_items = list(risk_sec.get("business_risks") or risk.get("weaknesses") or cio.get("key_risks") or [])
    if risk_items:
        rows = []
        for i, r in enumerate(risk_items[:6]):
            rows.append(
                {
                    "metric": scrub_leaks(r, limit=100),
                    "probability": "High" if i == 0 else "Medium" if i < 3 else "Low",
                    "impact": "High" if i < 2 else "Medium",
                    "monitoring": scrub_leaks(
                        (list(risk_sec.get("monitoring") or [])[:1] or ["Next earnings / guidance"])[0],
                        limit=80,
                    ),
                }
            )
        tables.append({"id": "risk_summary", "title": "Risk Summary", "rows": rows})

    catalysts = list(cio.get("key_catalysts") or [])
    if catalysts:
        tables.append(
            {
                "id": "catalyst_timeline",
                "title": "Catalyst Timeline",
                "rows": [{"metric": f"T+{i+1}", "value": scrub_leaks(c, limit=140)} for i, c in enumerate(catalysts[:6])],
            }
        )

    # Peer comparison only when valuation sections carry peer language
    peer = val_sec.get("peer_comparison")
    if peer and not is_placeholder(peer):
        tables.append(
            {
                "id": "peer_comparison",
                "title": "Peer Comparison",
                "rows": [{"metric": "Peer context", "value": scrub_leaks(peer, limit=180)}],
            }
        )

    decision = committee.get("decision") if isinstance(committee.get("decision"), dict) else {}
    if decision:
        tables.append(
            {
                "id": "committee_scorecard",
                "title": "Committee Scorecard",
                "rows": [
                    {"metric": k.replace("_", " ").title(), "value": scrub_leaks(v, limit=80)}
                    for k, v in decision.items()
                    if k
                    in {
                        "business_quality",
                        "financials",
                        "valuation",
                        "risk",
                        "committee_position",
                        "recommendation_readiness",
                    }
                    and not is_placeholder(v)
                ],
            }
        )
    return tables
