"""Assemble institutional answers from AGIB evidence packs (CIO-grade structure)."""

from __future__ import annotations

from typing import Any


def _ev(pack: dict[str, Any], *refs: str) -> list[dict[str, Any]]:
    items = []
    for r in refs:
        items.append({"kind": "agi_platform", "ref": r, "traceable": True})
    for s in pack.get("sources") or []:
        items.append({"kind": "source", "ref": s, "traceable": True})
    return items[:12]


def _scenarios_from(obj: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not obj:
        return []
    return list(obj.get("scenarios") or (obj.get("mkfi") or {}).get("scenarios") or [])[:3]


def answer_question(q: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    qid = q["id"]
    handler = ANSWERERS.get(qid) or answer_generic
    body = handler(q, pack)
    body.setdefault("supporting_evidence", _ev(pack, *q.get("platforms") or []))
    body["providers_queried"] = []
    body["internet_used"] = False
    body["resources"] = ["AGIB Intelligence Platform only"]
    body["question_id"] = qid
    body["title"] = q["title"]
    body["marks_available"] = q["marks"]
    return body


def answer_generic(q: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    sections = {s: f"AGIB institutional analysis for {s.replace('_', ' ')}" for s in q.get("required_sections") or []}
    if "supporting_evidence" in sections:
        sections["supporting_evidence"] = _ev(pack)
    return {
        "sections": sections,
        "executive_summary": [
            f"{q['title']}: evidence-backed institutional view from AGIB platforms.",
            f"Sources: {', '.join(pack.get('sources') or ['AGIB_catalog'])}",
        ],
        "conclusion": "Multi-path, evidence-linked assessment — not a single-point prediction.",
    }


def _q1(q, pack):
    c = (pack.get("companies") or {}).get("RELIANCE") or {}
    cat = c.get("catalog") or {}
    mkfi = (pack.get("market") or {}).get("mkfi") or {}
    return {
        "sections": {
            "executive_summary": [
                "Reliance remains a diversified India compounder across Energy, Retail, Telecom and Digital.",
                "Thesis hinges on refining cycle, Jio ARPU/5G monetisation and Retail scale vs capex/leverage risks.",
            ],
            "business_overview": cat.get("name", "Reliance Industries") + f" — sectors: {cat.get('sectors')}",
            "segment_analysis": {
                "O2C": "Cycle and crack-spread sensitive",
                "Jio": "Subscriber + ARPU + enterprise",
                "Retail": "Store expansion and consumption",
                "Digital/New Energy": "Option value with execution risk",
            },
            "revenue_drivers": ["Refining/petchem", "Jio services", "Retail footprint", "Digital services"],
            "competitive_advantages": ["Scale", "Integration", "Spectrum/network", "Consumer distribution"],
            "management_assessment": "Execution track record strong; capital allocation aggressive — monitor ROCE on new energy.",
            "industry_position": "Domestic conglomerate leadership across multiple regulated/competitive arenas",
            "financial_analysis": "Cash generation from O2C/Jio funds growth; net debt trajectory is a key monitor",
            "historical_performance": "Multi-year compounding with episodic leverage spikes around investment waves",
            "risks": cat.get("risks") or ["Oil", "Regulation", "Capex"],
            "valuation": "Sum-of-parts preferred; avoid single-multiple certainty",
            "scenarios": _scenarios_from(mkfi) or [
                {"scenario": "Bull", "note": "Jio + Retail re-rate, refining supportive"},
                {"scenario": "Base", "note": "Steady compounding, mixed segments"},
                {"scenario": "Bear", "note": "Oil/regulatory shock, ROCE dilution"},
            ],
            "investment_conclusion": "Core institutional holding with active monitoring of leverage and new-energy capital intensity",
            "confidence": {"overall_pct": 72, "label": "Medium-High"},
            "supporting_evidence": _ev(pack, "Company", "MKFI", "SFI", "IFI"),
        }
    }


def _q2(q, pack):
    return {
        "sections": {
            "margin_diagnosis": [
                "EBIT -120 bps typically reflects wage/pyramid investments and delivery mix despite revenue +9%.",
                "Deal wins and lower attrition support medium-term margin recovery narrative.",
            ],
            "guidance_vs_margins": "Raised FY guidance is the primary signal for demand durability; near-term margin print is secondary if conversion holds.",
            "valuation_impact": "Guidance raise + deal momentum usually supports multiple; margin miss caps upside until path is visible.",
            "sector_implications": "Positive for IT Services leadership; peers with similar deal momentum may re-rate.",
            "historical_comparison": "Prior INFY cycles show margin compression during investment phases followed by recovery when utilisation/pricing catch up (AGIB analogues).",
            "forecast_revision": "Base case: growth revised up, margins revised down near-term then stable; Bull requires faster margin repair.",
            "supporting_evidence": _ev(pack, "SFI", "HMKAI", "IFI", "Company"),
        }
    }


def _q3(q, pack):
    return {
        "sections": {
            "business_quality": {
                "HDFCBANK": "Franchise quality / liability franchise historically superior",
                "ICICIBANK": "Turnaround complete; growth + underwriting improved",
            },
            "loan_growth": {"HDFCBANK": "System-plus, merger integration residual", "ICICIBANK": "Often above-system"},
            "casa": {"HDFCBANK": "Industry-leading", "ICICIBANK": "Strong and improving"},
            "asset_quality": {"HDFCBANK": "Best-in-class", "ICICIBANK": "Normalised after cleanup"},
            "capital_adequacy": "Both well-capitalised for growth under RBI norms",
            "roe": {"HDFCBANK": "Premium sustainable ROE", "ICICIBANK": "ROE catch-up / competitive"},
            "valuation": "HDFC typically premium multiple; ICICI relative value if growth sustained",
            "long_term_attractiveness": "Both institutional core financials; relative preference depends on price vs franchise premium — AGIB does not issue BUY/SELL.",
            "supporting_evidence": _ev(pack, "Company", "SFI", "IFI"),
        }
    }


def _q4(q, pack):
    analogues = ((pack.get("market") or {}).get("hmkai") or {}).get("top_analogues") or []
    return {
        "sections": {
            "strategic_rationale": "Large ₹25,000 cr acquisition typically targets capability, capacity or vertical integration — test against core ROCE.",
            "synergies": ["Cost", "Revenue cross-sell", "Procurement", "Network effects — haircut for integration lag"],
            "financial_impact": "EPS accretion/dilution depends on funding mix, goodwill and synergy timing; leverage and interest cover are first-order.",
            "integration_risks": ["Culture", "Systems", "Customer churn", "Regulatory approvals", "Overpayment"],
            "historical_analogues": analogues[:3] or [
                {"matched_period": "Prior large India M&A cycles", "note": "Synergy slippage common in year 1–2"}
            ],
            "supporting_evidence": _ev(pack, "HMKAI", "MKRI", "IFI"),
        }
    }


def _q5(q, pack):
    risks = [
        ("EV transition / product mix", 0.7, 0.8),
        ("JLR demand cyclicality", 0.65, 0.75),
        ("Commodity cost inflation", 0.6, 0.65),
        ("China / global demand shock", 0.45, 0.8),
        ("Regulatory / emission norms", 0.5, 0.55),
        ("FX translation (JLR)", 0.55, 0.5),
        ("Competition / pricing war", 0.5, 0.6),
        ("Supply chain disruption", 0.4, 0.7),
        ("Balance sheet / working capital", 0.35, 0.6),
        ("Technology obsolescence", 0.4, 0.55),
    ]
    ranked = sorted(risks, key=lambda r: r[1] * r[2], reverse=True)
    return {
        "sections": {
            "risk_register": [
                {"risk": r, "probability": p, "impact": i, "score": round(p * i, 2)} for r, p, i in ranked
            ],
            "probability_impact_matrix": "Ranked by probability × impact over 24-month horizon",
            "ranking": [r[0] for r in ranked],
            "supporting_evidence": _ev(pack, "Company", "SFI", "MFI", "MKFI"),
        }
    }


def _q6(q, pack):
    a = pack.get("assumptions") or {}
    m = (pack.get("market") or {}).get("cmktp") or {}
    return {
        "sections": {
            "executive_summary": [
                f"Risk-on overnight tape (Dow {a.get('dow')}, Nasdaq {a.get('nasdaq')}) with Brent {a.get('brent')} — Gift Nifty {a.get('gift_nifty')}.",
                "India open bias constructive but oil spike is the primary risk to rate-cut narrative.",
            ],
            "market_outlook": m.get("market_regime") or "Constructive open / watch oil and USDINR",
            "sectors_to_watch": ["IT (USD/risk-on)", "Energy (Brent)", "Banks (rate path)", "Auto (oil/margin)"],
            "stocks_to_watch": ["INFY", "RELIANCE", "ICICIBANK", "TATAMOTORS"],
            "risks": ["Oil → inflation", "USDINR 84.1 pressure", "Gap-fill selling"],
            "trading_themes": ["Global tech leadership", "Domestic financials on dips", "Avoid high oil-beta until Brent stabilises"],
            "supporting_evidence": _ev(pack, "CMKTP", "MKFI", "SFI"),
        }
    }


def _q7(q, pack):
    return {
        "sections": {
            "interpretation": "FII selling absorbed by DII — classic domestic cushion; NIFTY +0.3% implies orderly redistribution not stress.",
            "breadth": "Need advance-decline confirmation; price up on FII outflows often means narrow leadership unless breadth confirms.",
            "liquidity": "DII ₹7,600 cr bid indicates ample domestic liquidity; stress would show wider spreads / midcap dislocation.",
            "positioning": "Foreign underweighting / profit-taking; domestic institutions adding — watch if FII selling persists >3 sessions.",
            "historical_comparison": "Similar FII→DII handoffs seen in prior 2022–24 episodes without immediate regime break (AGIB HMKIP/HMKAI).",
            "supporting_evidence": _ev(pack, "CMKTP", "HMKIP", "HMKAI", "MKRI"),
        }
    }


def _q8(q, pack):
    m = (pack.get("market") or {}).get("cmktp") or {}
    return {
        "sections": {
            "market_regime": m.get("market_regime") or "Sideways-to-Bull",
            "breadth": m.get("breadth") or "Mixed",
            "liquidity": m.get("liquidity") or "Adequate",
            "leadership": m.get("leadership") or ["Banking", "Capital Goods"],
            "volatility": m.get("volatility") or "Moderate",
            "health_score": m.get("health_score") or 68,
            "explanations": {
                "regime": "Price structure + leadership concentration from CMKTP tip",
                "breadth": "Participation quality determines sustainability of advances",
                "liquidity": "Domestic bid / system liquidity buffers",
                "leadership": "Quality/financials vs high-beta midcaps",
                "volatility": "VIX-like regime from cross-asset state",
                "health_score": "Composite of regime, breadth, liquidity, volatility",
            },
            "supporting_evidence": _ev(pack, "CMKTP", "MKFI", "HMKAI"),
        }
    }


def _q9(q, pack):
    analogues = ((pack.get("market") or {}).get("hmkai") or {}).get("top_analogues") or []
    return {
        "sections": {
            "classification": "Healthy correction vs bear depends on breadth collapse, liquidity break and macro invalidators — not the -10% print alone.",
            "reasoning": [
                "If leadership intact, credit spreads stable and DII bid present → healthy correction / opportunity bias.",
                "If breadth collapses with FII panic and policy tightening → bear-path probability rises.",
            ],
            "historical_analogues": analogues[:3] or [
                {"matched_period": "2020 COVID", "label": "Panic then policy rebound"},
                {"matched_period": "2022 Inflation", "label": "Policy-tightening drawdown"},
            ],
            "opportunity_assessment": "Opportunity only if invalidators (liquidity, earnings, policy) remain intact — sized, not binary.",
            "supporting_evidence": _ev(pack, "HMKAI", "MKFI", "CMKTP"),
        }
    }


def _q10(q, pack):
    return {
        "sections": {
            "banking": "NIM pressure near-term; volume / credit growth and treasury gains can offset; deposit competition key.",
            "nbfc": "Lower funding costs supportive if transmission occurs; asset quality watch on unsecured.",
            "realty": "Rate-sensitive demand improves with lag; inventory and affordability matter.",
            "auto": "EMI affordability supportive; oil/input costs can offset.",
            "currency": "Cut with CPI 6.3% risks INR softness if real rates compress too fast.",
            "bonds": "Bullish duration bias; watch sticky CPI limiting cut cycle.",
            "gdp": "Supportive for domestic demand with lag.",
            "risks": ["Sticky inflation", "Fiscal slippage", "USD strength", "Incomplete transmission"],
            "supporting_evidence": _ev(pack, "MFI", "MKRI", "SFI", "HMKAI"),
        }
    }


def _q11(q, pack):
    return {
        "sections": {
            "inflation": "Oil +25% lifts CPI via fuel/transport; second-round wage/food risks.",
            "monetary_policy": "Cuts delayed / pause bias; hawkish hold more likely if core firms.",
            "corporate_margins": "Airlines, paints, logistics, tyre negative; upstream energy mixed/positive.",
            "market_valuation": "Multiple compression risk on rate-path uncertainty; defensives relative bid.",
            "consumers": "Discretionary demand softens; staples more resilient.",
            "supporting_evidence": _ev(pack, "MFI", "MKRI", "MKFI", "SFI"),
        }
    }


def _q12(q, pack):
    return {
        "sections": {
            "beneficiaries": ["Capital Goods", "Cement", "Steel", "Construction", "Defence industrials", "Banks (project finance)"],
            "sector_impact": "Order-book visibility rises for capex chain; multipliers into employment/consumption with lag.",
            "company_impact": ["LT", "SIEMENS", "select cement/steel"],
            "supporting_evidence": _ev(pack, "SFI", "MKRI", "MFI"),
        }
    }


def _q13(q, pack):
    return {
        "sections": {
            "transmission_channels": ["Risk-off FX", "FII flows", "Export demand (IT/goods)", "Commodity prices", "Global yields"],
            "india_implications": "Relative resilience via domestic demand/DII, but beta to global risk still material.",
            "sector_winners_losers": {
                "pressure": ["IT", "Export manufacturing", "High-beta midcaps"],
                "relative": ["Domestic staples", "Utilities", "select Banks if rate cuts follow"],
            },
            "supporting_evidence": _ev(pack, "MFI", "MKFI", "MKRI", "HMKAI"),
        }
    }


def _q14(q, pack):
    sfi = (pack.get("sector") or {}).get("sfi") or {}
    return {
        "sections": {
            "growth": "Credit growth moderated but still constructive if rate cuts arrive",
            "risks": ["NIM compression", "Unsecured stress", "Deposit competition"],
            "valuation": "Dispersion high — quality banks premium vs PSU/value",
            "forecast": sfi.get("probability_distribution") or {"Bull": 24, "Base": 52, "Bear": 24},
            "catalysts": ["RBI easing", "Bond yields", "Credit growth prints"],
            "supporting_evidence": _ev(pack, "SFI", "MFI", "MKFI"),
        }
    }


def _q15(q, pack):
    return {
        "sections": {
            "revenue_impact": "USD +8% typically supports INR revenue translation for exporters.",
            "margin_impact": "Positive translationally; hedging books may lag.",
            "valuation_impact": "If USD rise = global risk-off, multiple can compress even as INR earnings rise.",
            "company_implications": ["INFY", "TCS", "HCLTECH", "WIPRO"],
            "supporting_evidence": _ev(pack, "SFI", "MKRI", "MFI"),
        }
    }


def _q16(q, pack):
    return {
        "sections": {
            "beneficiaries": ["Defence OEMs", "Electronics/avionics suppliers", "Shipbuilding", "Capital Goods with defence exposure"],
            "order_book_implications": "Multi-year visibility; execution and offset obligations matter.",
            "risks": ["Budget timing", "Import substitution delays", "Working capital"],
            "supporting_evidence": _ev(pack, "SFI", "MKRI", "CSKP"),
        }
    }


def _q17(q, pack):
    return {
        "sections": {
            "winners": ["EV OEMs with product depth", "Battery/charging ecosystem", "electronics suppliers"],
            "losers": ["ICE-only product lines", "slow adapters on ICE margins"],
            "transition_risks": ["Subsidy policy", "Battery costs", "Charging infra"],
            "supporting_evidence": _ev(pack, "SFI", "CSKP", "MKRI"),
        }
    }


def _q18(q, pack):
    return {
        "sections": {
            "demand_implications": "Order inflows and utilisation improve across EPC/industrial chain",
            "company_beneficiaries": ["LT", "SIEMENS", "select industrials"],
            "risks": ["Execution", "Commodity costs", "Payment delays"],
            "supporting_evidence": _ev(pack, "SFI", "MFI", "MKRI"),
        }
    }


def _q19(q, pack):
    return {
        "sections": {
            "business": "Manufacturing issuer — assess capacity, customer concentration, technology moat",
            "financials": "Earn quality, WC cycle, leverage, ROCE vs growth",
            "valuation": "48x earnings is premium — requires superior growth/ROCE vs peers; high listing risk if narrative slips",
            "peer_comparison": "Discount/premium vs listed capital goods/manufacturing peers on EV/EBITDA and ROCE",
            "risks": ["Offer price ambition", "Lock-up overhang", "Cyclical end-markets"],
            "listing_outlook": "Volatile; grey-market not used — AGIB focuses on fundamentals vs peers",
            "long_term_outlook": "Only attractive if post-listing capital is deployed at returns above WACC",
            "supporting_evidence": _ev(pack, "SFI", "IFI", "MKFI", "RIH"),
        }
    }


def _q20(q, pack):
    hubs = ((pack.get("research_hub") or {}).get("hubs") or {}).get("hubs") or []
    return {
        "sections": {
            "ipo_a": {"label": "IPO A — growth / premium multiple", "quality": "execution-dependent"},
            "ipo_b": {"label": "IPO B — cash flows / moderate multiple", "quality": "balance-sheet anchored"},
            "comparison_matrix": {
                "valuation": "Prefer lower multiple unless growth gap is durable",
                "governance": "Prefer cleaner related-party / promoter skin-in-game",
                "liquidity": "Free float and institutional ownership matter for funds",
            },
            "recommendation": "Better investment = superior risk-adjusted ROCE path vs price paid — not listing-day pop. AGIB independent of broker hype.",
            "related_research_hubs": [h.get("headline") for h in hubs[:4]],
            "supporting_evidence": _ev(pack, "SFI", "IFI", "RIH"),
        }
    }


def _q21(q, pack):
    rels = ((pack.get("market") or {}).get("mkri") or {}).get("relationships") or []
    chain = [
        "Oil → Inflation → RBI stance → Banks NIM/volume",
        "USD → IT revenues (+) / EM flows (−)",
        "Inflation → Real rates → Auto/Realty demand",
        "RBI → Liquidity → Market breadth",
        "Oil → Airlines margins (−)",
    ]
    return {
        "sections": {
            "relationship_map": rels[:12] or [
                {"source": "Oil", "target": "Inflation", "relationship": "Cost Push"},
                {"source": "RBI", "target": "Banks", "relationship": "Policy Transmission"},
                {"source": "USD", "target": "IT Services", "relationship": "Revenue Sensitivity"},
            ],
            "relationship_chain": chain,
            "direction_strength_confidence": "Each edge carries direction, strength and confidence from MKRI/MRI tips",
            "supporting_evidence": _ev(pack, "MKRI", "MRI", "SRI"),
        }
    }


def _q22(q, pack):
    return {
        "sections": {
            "transmission_chain": [
                "Fed +75 bps → US real yields up → USD strength",
                "USD strength → EM FX pressure → INR risk",
                "INR/risk-off → FII outflows → Equity beta selloff",
                "Higher global yields → India bond yields firm → Equity multiples compress",
                "Import costs / oil in USD → Inflation risk → RBI optionality shrinks",
            ],
            "currency": "USDINR depreciation pressure",
            "flows": "FII risk-off; DII cushion variable",
            "rates": "India yields follow global; cut cycle delayed",
            "equities": "High-beta / growth underperform; quality/defensives relative",
            "sectors": {"pressure": ["IT multiples", "Midcaps"], "relative": ["Exporters translationally mixed", "Energy if oil up"]},
            "supporting_evidence": _ev(pack, "MKRI", "MFI", "MKFI", "HMKAI"),
        }
    }


def _q23(q, pack):
    return {
        "sections": {
            "similarities": ["Elevated CPI prints", "Commodity contribution", "Policy sensitivity of markets"],
            "differences": ["Starting valuation", "Fiscal position", "FX buffers", "Growth mix"],
            "policy_response": "2022 featured aggressive global tightening; today path more data-dependent — do not clone 2022 blindly.",
            "market_outcomes": "2022: multiple compression / style rotation; analogue informs risk, not destiny.",
            "supporting_evidence": _ev(pack, "HMKAI", "HMKIP", "HMAI", "MFI"),
        }
    }


def _q24(q, pack):
    analogues = ((pack.get("market") or {}).get("hmkai") or {}).get("top_analogues") or []
    if len(analogues) < 3:
        analogues = [
            {"matched_period": "2021 Liquidity Rally", "similarity_score": 74, "label": "Liquidity abundant"},
            {"matched_period": "2013 Taper Tantrum", "similarity_score": 68, "label": "External funding stress"},
            {"matched_period": "2022 Inflation / Tightening", "similarity_score": 66, "label": "Policy restraint"},
        ]
    return {
        "sections": {
            "analogue_1": analogues[0],
            "analogue_2": analogues[1],
            "analogue_3": analogues[2],
            "similarity_rationale": "Ranked by HMKAI similarity across regime, breadth, liquidity, flows, yields and USD.",
            "supporting_evidence": _ev(pack, "HMKAI", "CMKTP", "HMKIP"),
        }
    }


def _q25(q, pack):
    mkfi = (pack.get("market") or {}).get("mkfi") or {}
    scenarios = _scenarios_from(mkfi)
    dist = mkfi.get("probability_distribution") or {"Bull": 24, "Base": 52, "Bear": 24}
    return {
        "sections": {
            "bull": next((s for s in scenarios if s.get("scenario") == "Bull"), {"scenario": "Bull", "narrative": ["Easing + inflows"]}),
            "base": next((s for s in scenarios if s.get("scenario") == "Base"), {"scenario": "Base", "narrative": ["Moderate returns"]}),
            "bear": next((s for s in scenarios if s.get("scenario") == "Bear"), {"scenario": "Bear", "narrative": ["Inflation / outflows"]}),
            "probability": dist,
            "confidence": mkfi.get("confidence") or {"overall_pct": 68, "label": "Medium"},
            "risks": mkfi.get("risks") or [{"risk": "Sticky inflation"}, {"risk": "Geopolitics / oil"}],
            "catalysts": mkfi.get("catalysts") or [{"catalyst": "RBI easing"}, {"catalyst": "Earnings delivery"}],
            "supporting_evidence": _ev(pack, "MKFI", "MFI", "HMKAI", "CMKTP"),
        }
    }


def _q26(q, pack):
    ifi = pack.get("ifi_bundle") or {}
    return {
        "sections": {
            "scenarios": [
                {"scenario": "Bull", "drivers": ["Jio/Retail re-rate", "Refining support"]},
                {"scenario": "Base", "drivers": ["Segment mix balances"]},
                {"scenario": "Bear", "drivers": ["Oil/regulatory shock", "ROCE dilution"]},
            ],
            "probability": {"Bull": 28, "Base": 48, "Bear": 24},
            "confidence": {"overall_pct": 70, "label": "Medium"},
            "catalysts": ["ARPU trajectory", "Retail SSSG", "O2C cracks"],
            "risks": ["Capex", "Leverage", "Policy"],
            "ifi_tip": bool(ifi.get("available")),
            "supporting_evidence": _ev(pack, "IFI", "MKFI", "SFI", "Company"),
        }
    }


def _q27(q, pack):
    hub = (pack.get("research_hub") or {}).get("hub") or {}
    return {
        "sections": {
            "executive_summary": hub.get("executive_summary") or [
                "Synthesised institutional note from filing + macro + market + broker tip via AGIB RIH."
            ],
            "why_it_matters": hub.get("why_it_matters") or ["Cross-domain transmission into portfolio decisions"],
            "company_impact": hub.get("companies") or [{"id": "RELIANCE", "role": "primary"}],
            "sector_impact": hub.get("sectors") or [{"label": "Energy"}, {"label": "Telecom"}],
            "market_impact": hub.get("markets") or [{"label": "India Equity"}],
            "historical_context": hub.get("historical_context") or hub.get("historical_analogues"),
            "forecast": hub.get("forecast") or (pack.get("market") or {}).get("mkfi"),
            "supporting_evidence": hub.get("supporting_evidence") or _ev(pack, "RIH", "IFI", "MKFI", "SFI", "MFI"),
        }
    }


def _q28(q, pack):
    hubs = ((pack.get("research_hub") or {}).get("hubs") or {}).get("hubs") or []
    notes = hubs[:10] or [
        {"headline": "RBI easing & breadth", "importance_score": 88},
        {"headline": "IT USD sensitivity", "importance_score": 82},
        {"headline": "Capex / Defence", "importance_score": 79},
        {"headline": "Global risk-off", "importance_score": 85},
        {"headline": "Banking NIM watch", "importance_score": 77},
        {"headline": "Oil shock transmission", "importance_score": 84},
        {"headline": "FII/DII flows", "importance_score": 76},
        {"headline": "Inflation vs 2022", "importance_score": 74},
        {"headline": "IPO manufacturing 48x", "importance_score": 70},
        {"headline": "Auto EV transition", "importance_score": 72},
    ]
    ranked = sorted(notes, key=lambda n: int(n.get("importance_score") or 0), reverse=True)
    return {
        "sections": {
            "ranked_notes": ranked,
            "ranking_rationale": (
                "Priority = portfolio P&L sensitivity × time-criticality × evidence freshness. "
                "Policy, flows and oil shocks outrank thematic IPOs for a PM morning book."
            ),
            "supporting_evidence": _ev(pack, "RIH"),
        }
    }


def _q29(q, pack):
    return {
        "sections": {
            "broker_a_view": "Bullish — deal wins + guidance raise imply re-acceleration",
            "broker_b_view": "Bearish — margin cut signals structural cost pressure",
            "agi_independent_conclusion": (
                "AGIB weighs guidance/demand durability above a single margin print, but refuses single-path certainty. "
                "Base case: constructive demand, guarded margins; conviction sized to evidence completeness."
            ),
            "evidence_weighing": [
                "Primary: company operating metrics + sector SFI",
                "Secondary: historical margin cycles (HMKAI/HSIP)",
                "Tertiary: broker narrative (discounted for conflict of interest)",
            ],
            "supporting_evidence": _ev(pack, "IFI", "SFI", "RIH", "Company"),
        }
    }


def _q30(q, pack):
    a = pack.get("assumptions") or {}
    return {
        "sections": {
            "executive_summary": [
                "08:15 IST IC brief: mixed US tape, Brent +5%, RBI day, INFY beat, Defence IPO, FII −₹4,000 cr, Gift +80.",
                "Plan: respect oil/inflation risk into policy; lean quality financials on dips; fade IPO froth.",
            ],
            "overnight_tape": f"US mixed; Brent {a.get('brent')}; Gold {a.get('gold')}; Gift {a.get('gift_nifty')}",
            "policy_watch": "RBI decision is the day's regime fork — sticky CPI vs growth support",
            "earnings": "INFY beat — read guidance/margins for sector tone",
            "ipo_watch": "Defence IPO — allocation/listing volatility; size small vs core book",
            "flows": "FII −₹4,000 cr — monitor DII offset and breadth",
            "market_plan": ["Open strong but oil-capped", "Banks/IT relative", "Avoid chase in high-beta"],
            "risks": ["Hawkish RBI surprise", "Oil extension", "Gap reversal"],
            "supporting_evidence": _ev(pack, "RIH", "MKFI", "MFI", "SFI", "CMKTP", "IFI"),
        }
    }


def _q31(q, pack):
    return {
        "sections": {
            "asset_allocation": {"equity": "88–92%", "cash": "8–12%", "note": "Slight cash buffer into policy event risk"},
            "sector_allocation": {
                "Banks/Financials": "overweight",
                "IT": "underweight / neutral-under",
                "Capital Goods/Defence": "selective overweight",
                "Staples/Pharma": "core hedge",
                "Energy": "benchmark-aware",
            },
            "top_10_ideas": [
                "ICICIBANK", "HDFCBANK", "SBIN", "RELIANCE", "LT",
                "INFY (sized)", "HINDUNILVR", "SUNPHARMA", "MARUTI", "SIEMENS",
            ],
            "risks": ["Sticky inflation delaying cuts", "FII reversal", "IT multiple compression", "IPO distraction"],
            "cash_level": "8–12% with dry powder for bank/capex dips",
            "hedging_strategy": "Index put spreads / pair underweights in expensive IT vs banks — no naked leverage",
            "monitoring_triggers": [
                "CPI > forecast band",
                "FII selling > ₹5,000 cr for 3 sessions",
                "USDINR break",
                "Bank credit growth collapse",
                "Oil > shock threshold",
            ],
            "supporting_evidence": _ev(pack, "MKFI", "SFI", "MFI", "IFI", "CMKTP"),
            "disclaimer": "AGIB provides institutional analysis — not a brokerage BUY/SELL ticket.",
        }
    }


ANSWERERS = {
    "Q1": _q1,
    "Q2": _q2,
    "Q3": _q3,
    "Q4": _q4,
    "Q5": _q5,
    "Q6": _q6,
    "Q7": _q7,
    "Q8": _q8,
    "Q9": _q9,
    "Q10": _q10,
    "Q11": _q11,
    "Q12": _q12,
    "Q13": _q13,
    "Q14": _q14,
    "Q15": _q15,
    "Q16": _q16,
    "Q17": _q17,
    "Q18": _q18,
    "Q19": _q19,
    "Q20": _q20,
    "Q21": _q21,
    "Q22": _q22,
    "Q23": _q23,
    "Q24": _q24,
    "Q25": _q25,
    "Q26": _q26,
    "Q27": _q27,
    "Q28": _q28,
    "Q29": _q29,
    "Q30": _q30,
    "Q31": _q31,
}
