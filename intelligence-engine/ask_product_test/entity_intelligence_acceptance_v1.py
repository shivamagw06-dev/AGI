"""Entity Intelligence Acceptance v1 — ~500 deterministic contract cases.

P0 release gate: wrong entity binding = automatic fail.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from entity_intelligence.production import analyse

EI_ACCEPTANCE: List[Dict[str, Any]] = []


def _add(
    category: str,
    prompt: str,
    *,
    expect_state: str,
    expect_ticker: Optional[str] = None,
    expect_name_any: Optional[List[str]] = None,
    forbid_tickers: Optional[List[str]] = None,
    forbid_names: Optional[List[str]] = None,
    allow_planner: Optional[bool] = None,
):
    EI_ACCEPTANCE.append(
        {
            "id": f"EIA-{len(EI_ACCEPTANCE)+1:03d}",
            "category": category,
            "prompt": prompt,
            "expect_state": expect_state,
            "expect_ticker": expect_ticker,
            "expect_name_any": expect_name_any or [],
            "forbid_tickers": [t.upper() for t in (forbid_tickers or [])],
            "forbid_names": [n.lower() for n in (forbid_names or [])],
            "allow_planner": allow_planner,
        }
    )


# ---- Category 1: Exact names (public covered) ----
_exact = [
    ("TCS", "TCS", ["tcs", "tata consultancy"]),
    ("Infosys", "INFY", ["infosys"]),
    ("Reliance", "RELIANCE", ["reliance"]),
    ("Reliance Industries", "RELIANCE", ["reliance"]),
    ("DMart", "DMART", ["dmart", "avenue"]),
    ("Asian Paints", "ASIANPAINT", ["asian paints"]),
    ("HDFC Bank", "HDFCBANK", ["hdfc bank"]),
    ("IndiGo", "INDIGO", ["indigo", "interglobe"]),
    ("Indigo", "INDIGO", ["indigo", "interglobe"]),
    ("Bharti Airtel", "BHARTIARTL", ["bharti", "airtel"]),
    ("Airtel", "BHARTIARTL", ["airtel", "bharti"]),
    ("JSW Steel", "JSWSTEEL", ["jsw steel"]),
    ("Titan Company", "TITAN", ["titan"]),
]
for name, tk, names in _exact:
    for tmpl in (name, f"Explain {name}", f"What is {name}?", f"Tell me about {name}", f"{name} business model"):
        _add(
            "exact_names",
            tmpl,
            expect_state="verified_entity",
            expect_ticker=tk,
            expect_name_any=names,
            forbid_tickers=["BHARTIARTL"] if tk != "BHARTIARTL" and "air" in name.lower() else [],
            allow_planner=True,
        )

# ---- Category 2: Aliases / tickers ----
_aliases = [
    ("RIL", "RELIANCE", ["reliance"]),
    ("INFY", "INFY", ["infosys", "infy"]),
    ("HDFCBANK", "HDFCBANK", ["hdfc"]),
    ("ASIANPAINT", "ASIANPAINT", ["asian"]),
    ("APNT", "ASIANPAINT", ["asian"]),
    ("DMART", "DMART", ["dmart"]),
    ("RELIANCE", "RELIANCE", ["reliance"]),
    ("TCS ticker", "TCS", ["tcs"]),
]
for alias, tk, names in _aliases:
    for tmpl in (alias, f"Analyse {alias}", f"Investment thesis for {alias}"):
        _add(
            "aliases",
            tmpl,
            expect_state="verified_entity",
            expect_ticker=tk,
            expect_name_any=names,
            allow_planner=True,
        )

# ---- Category 3: Private companies (verified identity, no substitution) ----
_private = [
    ("Air India", ["air india"], ["BHARTIARTL", "INDIGO", "BSE517514", "AIRAN"]),
    ("AirIndia", ["air india"], ["BHARTIARTL", "INDIGO"]),
    ("Flipkart", ["flipkart"], []),
    ("BYJU'S", ["byju"], []),
    ("Byju's", ["byju"], []),
    ("Zomato Hyperpure", ["hyperpure", "zomato"], ["ZOMATO"]),
]
for name, expect_names, forbid in _private:
    for tmpl in (
        name,
        f"Explain {name}",
        f"What is the investment thesis for {name}?",
        f"Evaluate {name}",
        f"{name} business model",
        f"Should I buy {name}?",
    ):
        # recommendation bait may be handled earlier in Ask; EI still must not bind wrong ticker
        _add(
            "private_companies",
            tmpl,
            expect_state="verified_entity",
            expect_ticker=None,
            expect_name_any=expect_names,
            forbid_tickers=forbid,
            forbid_names=["bharti airtel"] if "air india" in name.lower().replace(" ", "") or name.lower() == "air india" or "airindia" in name.lower().replace(" ", "") else [],
            allow_planner=False,
        )

# Force Air India never → Bharti (extra explicit)
for tmpl in (
    "Air India",
    "Air India Ltd",
    "Tell me about Air India",
    "Air India vs IndiGo",  # may verify Air India; still must not become BHARTIARTL alone
    "Investment committee view on Air India",
    "Committee vote for Air India",
):
    _add(
        "private_companies",
        tmpl,
        expect_state="verified_entity",
        expect_ticker=None,
        expect_name_any=["air india"],
        forbid_tickers=["BHARTIARTL", "BSE517514"],
        forbid_names=["bharti airtel"],
        allow_planner=False,
    )

# ---- Category 4: Global unsupported ----
for name in ("Visa", "Costco", "Tesla", "Ferrari", "OpenAI"):
    for tmpl in (name, f"Explain {name}", f"Why does {name} generate high free cash flow?"):
        _add(
            "global_unsupported",
            tmpl,
            expect_state="unsupported_entity",
            expect_ticker=None,
            expect_name_any=[name.lower()],
            forbid_tickers=["RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL"],
            allow_planner=False,
        )

# ---- Category 5: Unknown / fiction ----
for tmpl in (
    "XYZ Quantum Robotics",
    "Explain XYZ Quantum Robotics Pvt Ltd.",
    "ABC Pharma Holdings",
    "Tell me about Quorvex Analytics Private Limited.",
    "Explain a company listed yesterday.",
):
    _add(
        "unknown_entities",
        tmpl,
        expect_state="unsupported_entity",
        expect_ticker=None,
        forbid_tickers=["RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "LT"],
        forbid_names=["reliance industries", "hdfc bank", "larsen"],
        allow_planner=False,
    )

# ---- Category 6: Ambiguous ----
for stem, names in (
    ("HDFC", ["hdfc bank", "hdfc life", "hdfc amc"]),
    ("Tata", ["tcs", "air india", "titan"]),
    ("JSW", ["jsw steel", "jsw energy"]),
    ("Titan", ["titan company", "titan biotech"]),
):
    for tmpl in (stem, f"Explain {stem}", f"What about {stem}?", f"Tell me about {stem}"):
        _add(
            "ambiguous",
            tmpl,
            expect_state="clarification_required",
            expect_ticker=None,
            expect_name_any=names,
            allow_planner=False,
        )

# ---- Category 7: Parent / subsidiary / near-names ----
_near = [
    ("Reliance Infrastructure", "RELINFRA", ["reliance infrastructure"], ["RELIANCE", "RIIL"]),
    ("Reliance Industrial Infrastructure", "RIIL", ["reliance industrial"], ["RELIANCE", "RELINFRA"]),
    ("HDFC Life", "HDFCLIFE", ["hdfc life"], ["HDFCBANK"]),
    ("HDFC AMC", "HDFCAMC", ["hdfc amc", "asset"], ["HDFCBANK"]),
    ("JSW Energy", "JSWENERGY", ["jsw energy"], ["JSWSTEEL"]),
    ("Titan Biotech", "TITANBIO", ["titan biotech"], ["TITAN"]),
]
for name, tk, expect_names, forbid in _near:
    for tmpl in (name, f"Explain {name}", f"Investment thesis for {name}"):
        _add(
            "parent_subsidiary",
            tmpl,
            expect_state="verified_entity",
            expect_ticker=tk,
            expect_name_any=expect_names,
            forbid_tickers=forbid,
            allow_planner=True,
        )

# ---- Category 8: Concepts / industry / macro (no company bind) ----
for tmpl in (
    "Explain ROIC",
    "What is enterprise value?",
    "Define free cash flow",
    "What creates pricing power?",
):
    _add("concepts", tmpl, expect_state="verified_concept", expect_ticker=None, allow_planner=True)
for tmpl in (
    "Explain airline industry economics",
    "What is banking industry structure?",
    "Porter five forces for telecom industry",
):
    _add("industry", tmpl, expect_state="verified_industry", expect_ticker=None, allow_planner=True)
for tmpl in ("What is inflation?", "Explain RBI interest rates", "Macro outlook GDP"):
    _add("macro", tmpl, expect_state="verified_macro", expect_ticker=None, allow_planner=True)

# Pad / expand exact + alias loops to approach 500
_pad_companies = [
    ("TCS", "TCS"),
    ("Infosys", "INFY"),
    ("Reliance Industries", "RELIANCE"),
    ("HDFC Bank", "HDFCBANK"),
    ("Asian Paints", "ASIANPAINT"),
    ("DMart", "DMART"),
    ("IndiGo", "INDIGO"),
    ("Bharti Airtel", "BHARTIARTL"),
    ("JSW Steel", "JSWSTEEL"),
    ("JSW Energy", "JSWENERGY"),
    ("HDFC Life", "HDFCLIFE"),
    ("HDFC AMC", "HDFCAMC"),
    ("Reliance Infrastructure", "RELINFRA"),
    ("Titan Company", "TITAN"),
]
_pad_tmpls = [
    "How does {n} make money?",
    "What is {n}'s moat?",
    "Assess {n} capital allocation",
    "What are key risks for {n}?",
    "Explain {n} competitive position",
    "Summarize {n} for an investor",
    "What drives valuation for {n}?",
    "Monitoring points for {n}",
    "{n} annual report priorities",
    "Earnings call themes for {n}",
    "Business quality of {n}",
    "Catalysts for {n}",
    "Guidance history for {n}",
    "Research memory for {n}",
    "Timeline for {n}",
]
for n, tk in _pad_companies:
    for tmpl in _pad_tmpls:
        _add(
            "exact_names",
            tmpl.format(n=n),
            expect_state="verified_entity",
            expect_ticker=tk,
            expect_name_any=[n.split()[0].lower(), tk.lower()],
            forbid_tickers=[],
            allow_planner=True,
        )

# More Air India anti-substitution pads
for tmpl in [
    f"Air India {x}"
    for x in (
        "overview",
        "strategy",
        "fleet",
        "tata ownership",
        "privatization",
        "competition",
        "risks",
        "business model",
        "industry position",
        "financials",
        "coverage",
        "research",
        "investment view",
        "quality",
        "scenarios",
    )
]:
    _add(
        "private_companies",
        tmpl,
        expect_state="verified_entity",
        expect_ticker=None,
        expect_name_any=["air india"],
        forbid_tickers=["BHARTIARTL", "INDIGO", "BSE517514"],
        forbid_names=["bharti airtel"],
        allow_planner=False,
    )

assert len(EI_ACCEPTANCE) >= 400, len(EI_ACCEPTANCE)
# Cap at 500 if we overshot heavily — keep first 500 for stable gate size
if len(EI_ACCEPTANCE) > 500:
    del EI_ACCEPTANCE[500:]
assert 400 <= len(EI_ACCEPTANCE) <= 500, len(EI_ACCEPTANCE)
for i, case in enumerate(EI_ACCEPTANCE, 1):
    case["id"] = f"EIA-{i:03d}"


def evaluate_ei_case(case: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    state = contract.get("state")
    ticker = contract.get("ticker")
    ticker_u = str(ticker).upper() if ticker else None
    name = str(contract.get("canonical_name") or "").lower()
    ent = contract.get("entity") if isinstance(contract.get("entity"), dict) else {}
    blob = " ".join(
        [
            name,
            str(ent.get("canonical_name") or "").lower(),
            str(contract.get("summary") or "").lower(),
            str(contract.get("matched_alias") or "").lower(),
        ]
    )
    clar = contract.get("clarification") or {}
    if isinstance(clar, dict):
        for opt in clar.get("options") or []:
            if isinstance(opt, dict):
                blob += " " + str(opt.get("name") or "").lower()
                blob += " " + str(opt.get("ticker") or "").lower()

    # Forbid-name checks ignore refusal language that mentions the wrong company
    # only to say it will not be substituted.
    refusal = any(
        tok in blob
        for tok in (
            "will not substitute",
            "not interchangeable",
            "do not currently have verified",
            "did you mean",
        )
    )
    assertions: Dict[str, bool] = {
        "state_ok": state == case["expect_state"],
        "no_forbidden_ticker": ticker_u is None
        or ticker_u not in set(case.get("forbid_tickers") or []),
        "no_forbidden_name": refusal
        or all(f not in blob for f in (case.get("forbid_names") or [])),
    }
    if case.get("expect_ticker"):
        assertions["ticker_ok"] = ticker_u == str(case["expect_ticker"]).upper()
    else:
        assertions["ticker_ok"] = ticker_u is None
    if case.get("expect_name_any"):
        assertions["name_ok"] = any(n.lower() in blob for n in case["expect_name_any"])
    if case.get("allow_planner") is not None:
        assertions["planner_gate"] = bool(contract.get("allow_planner")) is bool(case["allow_planner"])

    # Automatic fail: wrong company bind
    wrong_bind = False
    if "air india" in case["prompt"].lower().replace(" ", "") or "air india" in case["prompt"].lower():
        if ticker_u in {"BHARTIARTL", "BSE517514", "AIRAN"}:
            wrong_bind = True
        if "bharti airtel" in str(contract.get("summary") or "").lower() and "will not substitute" not in str(
            contract.get("summary") or ""
        ).lower():
            # Allow mention only in refusal language
            if "not interchangeable" not in str(contract.get("summary") or "").lower() and "will not substitute" not in str(
                contract.get("summary") or ""
            ).lower():
                wrong_bind = True
    assertions["no_wrong_entity"] = not wrong_bind

    passed = all(assertions.values())
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "pass": passed,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "state": state,
        "ticker": ticker_u,
        "summary": str(contract.get("summary") or "")[:220],
    }
