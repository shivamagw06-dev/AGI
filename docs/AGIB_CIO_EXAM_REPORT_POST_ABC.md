# AGIB CIO Regression Exam Report — Post Track A + B + C

**Examiner role:** Independent Chief Investment Officer (certification board)  
**Candidate:** AGIB Ask Pipeline with Tracks A (Intent Resolution), B (Answer Assembly), C (Framework Selection)  
**Date:** 2026-07-28  
**Questions:** Exact same 25 prompts as baseline CIO exam  
**Execution path:** Question → Intent Resolution → IERE → Answer Assembly → Framework Selection → Existing Reasoning → UiService narrative  
**Track D:** Not included  
**Method constraint:** No code changes to improve AGIB; measurement only. Scoring methodology aligned with baseline 0–10 institutional scale.

---

## Verdict

### Overall score: **4.3 / 10** (baseline **3.7 / 10**) — Δ **+0.7**

### Certification: **PARTIALLY READY**

**Not PRODUCTION READY. Not INSTITUTIONAL GRADE.**

Tracks A–C materially fixed the *control plane* (routing, assembly plan, framework choice). They did **not** yet fix the *answer plane* (CIO-grade narrative that consumes those plans). A multi-billion-dollar investment firm would trust AGIB more for **pipeline correctness**, but still would not trust the **written answer** on conceptual / cross-domain questions.

### Score distribution (current)

| Verdict | Count |
|---------|------:|
| PARTIAL+ | 2 |
| PARTIAL | 6 |
| WEAK | 9 |
| FAIL | 8 |

### Improvement vs baseline

| | Count |
|--|------:|
| Improved | 21 |
| No Change | 3 |
| Regressed | 1 (Q11) |

### Version history (measured)

| Version | CIO Score | Primary Improvement |
|---------|----------:|---------------------|
| Baseline (pre A/B/C) | 3.7/10 | Retrieval + governance restraint |
| Track A+B+C (this exam) | **4.3/10** | Routing + assembly + framework selection |
| Track A+B+C+D | ? | Not run — narrative layer next |

---

## Executive finding (strict)

| Layer | Status |
|-------|--------|
| Track A Intent / Concept / Temporal | **Solved** on Ask path (~100% routing correctness on this set) |
| Track B Answer Assembly | **Built and executed** (100% of runs); **not consumed** by final narrative |
| Track C Framework Selection | **Accurate** on sector/concept samples (10/10 audited); **not consumed** by reasoning prose |
| Existing Reasoning + Ui narrative | **Still the bottleneck** — blocked summaries, template “business strength C”, wrong impulse templates |
| Historical answer integrity (Q24) | Routing **PASS**; delivered answer lookahead **FAIL** |

The +0.7 overall lift is real but modest. Most of the expected Track B (+2.0–2.5) and Track C impact is **trapped upstream** until Track D (and/or soft-binding of assembly/framework into narrative) lands.

---

## Final scorecard

### Overall

| | Baseline | A+B+C | Delta |
|--|---------:|------:|------:|
| Overall CIO score | 3.66 | 4.34 | **+0.68** |

### Category scores

| Category | Baseline | A+B+C | Delta |
|----------|---------:|------:|------:|
| Company | 5.40 | 6.10 | +0.70 |
| Industry | 2.90 | 4.20 | **+1.30** |
| Macro | 3.60 | 4.00 | +0.40 |
| Cross-Domain / Stress | 2.90 | 3.40 | +0.50 |
| Documents | 2.67 | 3.17 | +0.50 |
| Historical Replay | 4.00 | 4.50 | +0.50 |
| Institutional (Q25) | 5.50 | 6.00 | +0.50 |
| Corporate Events | n/a | n/a | — |
| Portfolio | n/a | n/a | — |
| Government (within Macro/Cross prompts) | weak use | framework OK / narrative thin | — |

Industry rose most because Track C finally selects cement/hospital/IT frameworks and Track A stops valuation misroutes — even when the written answer remains weak.

---

## KPI comparison (Delta analysis)

| KPI | Previous | Current | Delta | Notes |
|-----|---------:|--------:|------:|-------|
| Intent Routing | ~40% | **100%** | **+60pp** | No forbidden valuation qtype on explain/why set |
| Entity Resolution (Ask path) | ~60% | **100%** | **+40pp** | Concept mode; INFY hint ignored on Q21/Q23 Ask path |
| Historical Routing | ~0% | **100%** | **+100pp** | Q24 `as_of=2020-03-31` |
| Evidence Retrieval | Strong | Strong | ~0 | IERE still primary strength |
| Evidence Ranking | Pass | Pass | ~0 | Unchanged engine |
| Framework Selection (executed) | 0% | **100%** | **+100pp** | New Track C |
| Framework Accuracy (audited sample n=10) | n/a | **100%** | n/a | Banks/IT/Cement/Hospitals/SOTP/Macro/Policy |
| Framework Explanations | 0% | **100%** | **+100pp** | Explanation object always present |
| Evidence Utilisation (in narrative) | Low | Low | ~0 | Assembly plans unused by prose |
| Answer Assembly (executed) | 0% | **100%** | **+100pp** | Skeleton/gaps/citations always |
| Confidence Calibration (assembly) | n/a | Present | n/a | Deterministic bands |
| Replay Integrity (answer) | Fail | **Fail** | 0 | Q24 still shows current PE in Ui why |
| Citation Coverage (assembly map) | n/a | High (~1.0 structural) | n/a | Not visible in user prose |
| Generic / Blocked Summary Rate | ~64% | **~72%** | **-8pp worse** | Education path + empty narrative → block/template |
| Hallucination Rate | Moderate | Moderate | ~0 | Templates still invent “company” voice |
| Policy Compliance | Good | Good | ~0 | Still refuses unsupported valuation claims |
| Latency (avg ms) | 7834 | 7902 | +68 | Neutral |

---

## Failure analysis (ranked by impact)

### 1. Narrative / Editorial (highest impact)
Final UiService summaries frequently ignore Track A/B/C outputs:
- “Valuation question blocked…” on education paths (Q5–Q7, Q10, Q18–Q19, Q25)
- “business strength rated C” templates (Q4, Q8, Q13, Q15, Q17, Q22–Q23)
- Wrong impulse templates (Q11 oil-shock text for a repo cut)

**Root cause:** Reasoning/editorial layer does not bind Framework Explanation Object or Answer Assembly skeleton into the user-visible answer. This is exactly Track D’s job (plus a soft bind).

### 2. Replay answer integrity
Q24 Ask routing is correct (`HistoricalReplay`, `as_of=2020-03-31`, IERE ranked=0). Delivered why-bullets still cite **Current PE 14.3**.  
**Root cause:** Ui/live packs not frozen to PIT objects.

### 3. Framework → narrative gap
Track C selects correctly (e.g. hospitals → Occupancy/ARPOB; Reliance → SOTP) but prose does not explain those frameworks.  
**Root cause:** Selection is metadata; reasoning frozen and unused.

### 4. Sector keyword collisions (Track C edge)
- Q8 “PSU Banks” → sector=banks only (misses FMCG/IT matrix)
- Q11 “Banks, NBFCs…” → bank valuation frameworks dominate Macro Transmission  

**Root cause:** Keyword sector detector lacks multi-sector / question-priority rules for macro-transmission prompts.

### 5. Residual UI entity pollution
Ask Pipeline clears INFY on Q23; Ui summary still starts with “Infosys…”.  
**Root cause:** Pollution outside Track A soft-wire.

### 6. Knowledge / synthesis depth (unchanged)
Still missing CIO checklists (10 reasons, moat decade evidence, GST limits, document section protocols). Not solvable by more intelligence packages — needs answer assembly consumption + narrative.

### 7. Q11 regression
Only clear regression: worse sector composition + wrong macro template vs baseline WEAK-but-macro-shaped answer.

---

## Recommendation answers

1. **Did Track A solve the routing problems?**  
   **Yes** on the Ask control path. Intent, concept mode, and historical `as_of` are fixed for this exam set.

2. **Did Track B materially improve institutional answer quality?**  
   **Only partially.** Assembly executes with skeleton, gaps, confidence, citations — but user-visible answers barely use it. Measured lift is structural, not communicative.

3. **Did Track C reduce wrong-framework errors?**  
   **Yes at selection time** (banks forbid EV/EBITDA; IT gets DCF/EV-EBITDA; conglomerates SOTP; hospitals healthcare ops). **No at answer time** — users still don’t see framework-correct explanations.

4. **Is Track D justified?**  
   **Yes — mandatory next.** Without narrative binding, A/B/C value is mostly invisible to a CIO reading the answer.

5. **Would Track D provide the largest remaining score improvement?**  
   **Yes.** The largest residual gap is communication of already-selected frameworks + assembled evidence. Expected remaining upside exceeds another intelligence domain.

6. **What remaining bottlenecks prevent institutional quality?**  
   - Narrative/editorial not consuming assembly + framework objects  
   - Historical answer lookahead  
   - Template / block messages on education paths  
   - Multi-sector macro composition edge cases  
   - Deep checklist synthesis (reasoning content), without redesigning KF  

---

## Pass / Fail decision

**PARTIALLY READY**

- Ready as an **institutional control-plane**: routes, plans, selects frameworks, retrieves evidence.  
- Not ready as an **institutional answer engine**: written outputs remain generic/blocked and sometimes lookahead-contaminated.  

Do **not** claim production readiness. Do **not** skip measurement before Track D. This report is the frozen baseline for Track D.

---

## Per-question grades (summary table)

| Q | Section | Before | After | Δ | Verdict | Improvement |
|---|---------|-------:|------:|--:|---------|-------------|
| Q1 | Company | 5.5 | 7.0 | +1.5 | PARTIAL+ | Improved |
| Q2 | Company | 6.0 | 6.5 | +0.5 | PARTIAL | Improved |
| Q3 | Company | 6.5 | 6.5 | 0.0 | PARTIAL+ | No Change |
| Q4 | Company | 4.0 | 4.5 | +0.5 | WEAK | Improved |
| Q5 | Company | 5.0 | 6.0 | +1.0 | PARTIAL | Improved |
| Q6 | Industry | 2.0 | 4.0 | +2.0 | WEAK | Improved |
| Q7 | Industry | 2.0 | 3.5 | +1.5 | WEAK | Improved |
| Q8 | Industry | 3.0 | 3.5 | +0.5 | WEAK | Improved |
| Q9 | Industry | 5.5 | 6.0 | +0.5 | PARTIAL | Improved |
| Q10 | Industry | 2.0 | 4.0 | +2.0 | WEAK | Improved |
| Q11 | Macro | 4.5 | 4.0 | -0.5 | WEAK | Regressed |
| Q12 | Macro | 3.5 | 4.5 | +1.0 | WEAK | Improved |
| Q13 | Macro | 2.5 | 3.0 | +0.5 | FAIL | Improved |
| Q14 | Macro | 5.0 | 5.5 | +0.5 | PARTIAL | Improved |
| Q15 | Macro | 2.5 | 3.0 | +0.5 | FAIL | Improved |
| Q16 | Cross | 5.0 | 5.5 | +0.5 | PARTIAL | Improved |
| Q17 | Cross | 2.0 | 2.5 | +0.5 | FAIL | Improved |
| Q18 | Cross | 2.0 | 3.0 | +1.0 | FAIL | Improved |
| Q19 | Cross | 2.5 | 3.0 | +0.5 | FAIL | Improved |
| Q20 | Cross | 3.0 | 3.0 | 0.0 | FAIL | No Change |
| Q21 | Documents | 3.5 | 4.5 | +1.0 | WEAK | Improved |
| Q22 | Documents | 2.0 | 2.5 | +0.5 | FAIL | Improved |
| Q23 | Documents | 2.5 | 2.5 | 0.0 | FAIL | No Change |
| Q24 | Replay | 4.0 | 4.5 | +0.5 | WEAK | Improved |
| Q25 | Institutional | 5.5 | 6.0 | +0.5 | PARTIAL | Improved |

---

## Per-question examiner sheets

### Q1 — PARTIAL+ (7.0/10) · Improved

**Question:** Why is HDFC Bank primarily valued using Price-to-Book and Residual Income, while Infosys is commonly valued using EV/EBITDA and DCF? Explain the economic and accounting reasons, not just the formulas.

**Final Answer (Ui executive summary):**  
Yes — book value can rise while price-to-book falls when the share price does not keep pace with book equity. Price-to-book is price divided by book value. If book equity grows faster than the share price — or the price falls — the multiple compresses even though book value is higher. Other possible explanations include: (1) Investors marked down return expectations on equity; (2) Market-wide de-rating of financials or the sector; (3) Book value rose through capital raising rather than earned returns. Additional evidence needed: Share-price move vs book-value bridge; ROE trend and capital actions. Both can be true; separate balance-sheet growth from the market's pricing of that equity.

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`['HDFCBANK', 'INFY']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_HDFCBANK` · FINANCIAL_METRICS · HDFCBANK expectations
  - `ici_HDFCBANK` · FINANCIAL_METRICS · HDFCBANK company intelligence
  - `hist_HDFCBANK` · HISTORICAL_VALUATION · HDFCBANK historical object
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - `ro_HDFCBANK` · TIMELINES · HDFCBANK research office
  - packs: `['company', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`6`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION, FW_PB, FW_RESIDUAL_INCOME
- **Secondary:** FW_ROE
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_DDM, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** FW_EV_EBITDA, FW_EV_SALES, FW_ROIC
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 5, 'Historical': 3, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** High (0.8869)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 70/100

**Overall Question Score:** 70/100 (exam scale 7.0/10)

**Improvement vs previous CIO exam:** Improved — Track A routes Explain/education; Track C selects P/B+Residual Income and rejects EV/EBITDA; assembly skeleton present. Final prose still drifts into P/B mechanics and does not cleanly contrast Infosys DCF/EV-EBITDA economics.

### Q2 — PARTIAL (6.5/10) · Improved

**Question:** Compare Infosys, TCS, and Wipro. If all three trade at similar P/E multiples, which additional evidence would you retrieve before concluding whether one is undervalued?

**Final Answer (Ui executive summary):**  
A valuation multiple can move differently from earnings because price and the earnings base are separate inputs. Multiples compress or expand when investors change growth assumptions, risk appetite or the peer set — even if the company earns more. Other possible explanations include: (1) Price lagged earnings; (2) Market-wide de-rating; (3) Earnings composition changed. Additional evidence needed: Price path vs earnings path; Trailing vs forward base. Separate the accounting change from the market's pricing of that change.

**Intent Classification:** Correct — Ask=`Analyse` / qtype=`business_quality` / gov_path=`research`

**Entity Resolution:** Correct — entities=`['INFY', 'TCS', 'WIPRO']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_INFY` · FINANCIAL_METRICS · INFY expectations
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `ici_TCS` · FINANCIAL_METRICS · TCS company intelligence
  - `ici_WIPRO` · FINANCIAL_METRICS · WIPRO company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - `hist_TCS` · HISTORICAL_VALUATION · TCS historical object
  - `hist_WIPRO` · HISTORICAL_VALUATION · WIPRO historical object
  - `ro_INFY` · TIMELINES · INFY research office
  - packs: `['company', 'industry', 'expectation', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`8`

**Framework Selected:**
- **Primary:** FW_DCF, FW_EV_EBITDA
- **Secondary:** FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PE
- **Supporting:** FW_CASH_FLOW_QUALITY, FW_ROIC
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 10, 'Historical': 4, 'Industry': 3, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** High (0.8515)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 75/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement vs previous CIO exam:** Improved — Entities INFY/TCS/WIPRO bound; frameworks DCF+EV/EBITDA+peer. Delivered answer still generic PE-multiple scaffolding; does not list the full institutional evidence checklist asked.

### Q3 — PARTIAL+ (6.5/10) · No Change

**Question:** If Titan reports 25% revenue growth but operating cash flow falls sharply, what evidence would you investigate before determining whether growth quality has deteriorated?

**Final Answer (Ui executive summary):**  
Higher revenue does not guarantee stronger cash generation. Cash can fall when working capital rises, capital expenditure increases, or accruals run ahead of collections. Sales are recognised on an accrual basis. Free cash flow subtracts cash stuck in inventory and receivables and cash spent on investing. Those bridges can turn a revenue increase into weaker cash. Other possible explanations include: (1) inventory build; (2) slower customer payments; (3) higher capex; (4) one-off cash outflows. Additional evidence needed: operating cash-flow and working-capital bridges, plus capex detail. Identify the cash bridge before judging whether the revenue growth is high quality.

**Intent Classification:** Correct — Ask=`Analyse` / qtype=`business_quality` / gov_path=`research`

**Entity Resolution:** Correct — entities=`['TITAN']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_TITAN` · FINANCIAL_METRICS · TITAN expectations
  - `ici_TITAN` · FINANCIAL_METRICS · TITAN company intelligence
  - `hist_TITAN` · FINANCIAL_METRICS · TITAN historical object
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ro_TITAN` · TIMELINES · TITAN research office
  - packs: `['company', 'industry', 'expectation', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`5`

**Framework Selected:**
- **Primary:** FW_DCF
- **Secondary:** FW_BUSINESS_QUALITY, FW_ECONOMIC_MOAT, FW_ROIC
- **Supporting:** FW_CASH_FLOW_QUALITY, FW_EV_EBITDA, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 5, 'Historical': 1, 'Macro': 1, 'Industry': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.8148)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 65/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement vs previous CIO exam:** No Change — Cash vs accrual reasoning remains the relative strength. Framework composition includes DCF/moat more than cash-flow quality primacy. Titan-specific jewellery operating checklist still missing.

### Q4 — WEAK (4.5/10) · Improved

**Question:** How would you assess whether Asian Paints has maintained its competitive moat over the last decade? Which evidence domains should AGIB retrieve?

**Final Answer (Ui executive summary):**  
Asian Paints continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`['ASIANPAINT']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT expectations
  - `ici_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT company intelligence
  - `hist_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT historical object
  - `ro_ASIANPAINT` · TIMELINES · ASIANPAINT research office
  - packs: `['company', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`4`

**Framework Selected:**
- **Primary:** FW_DCF, FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_ECONOMIC_MOAT, FW_ROIC
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_EV_EBITDA, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 4, 'Historical': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.8037)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 45/100

**Overall Question Score:** 45/100 (exam scale 4.5/10)

**Improvement vs previous CIO exam:** Improved — Education path + Economic Moat framework selected (Track C). Final answer still 'business strength rated C' template; decade moat evidence domains not enumerated.

### Q5 — PARTIAL (6.0/10) · Improved

**Question:** Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION, FW_PB, FW_RESIDUAL_INCOME
- **Secondary:** FW_ROE
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_DDM, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** FW_EV_EBITDA, FW_EV_SALES, FW_ROIC
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 55/100

**Overall Question Score:** 60/100 (exam scale 6.0/10)

**Improvement vs previous CIO exam:** Improved — Major Track A/C win: concept mode, education path, banks frameworks, EV/EBITDA forbidden with explanation object. Executive summary still shows valuation-block message — narrative layer ignores the correct path.

### Q6 — WEAK (4.0/10) · Improved

**Question:** Why do cement companies often experience valuation expansion before earnings actually improve?

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_CEMENT_CAPACITY, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_REPLACEMENT_COST
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_INDUSTRY_STRUCTURE
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 40/100

**Overall Question Score:** 40/100 (exam scale 4.0/10)

**Improvement vs previous CIO exam:** Improved — Cement capacity + EV/EBITDA selected; why-bullets mention regional cement economics. Summary still valuation-blocked; no utilisation→pricing→multiple-expansion chain synthesised.

### Q7 — WEAK (3.5/10) · Improved

**Question:** Why do software companies typically receive higher valuation multiples than steel producers?

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_DCF, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_PE
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_HISTORICAL_VALUATION, FW_ROIC
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 35/100

**Overall Question Score:** 35/100 (exam scale 3.5/10)

**Improvement vs previous CIO exam:** Improved — Routed away from valuation block path; IT frameworks selected but steel/commodity contrast incomplete (sector keyword collapsed to it_services). Answer still blocked/generic.

### Q8 — WEAK (3.5/10) · Improved

**Question:** Compare the business economics of FMCG, IT Services, and PSU Banks. Which KPIs matter most for each and why?

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Industry` / qtype=`sector` / gov_path=`clarification`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_INDUSTRY_STRUCTURE, FW_PB, FW_RESIDUAL_INCOME
- **Secondary:** FW_PORTERS_FIVE, FW_ROE
- **Supporting:** FW_DDM, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** FW_EV_EBITDA, FW_EV_SALES, FW_ROIC
- **Framework confidence:** High (90%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=['Industry']; coverage=0.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Insufficient (0.2424)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Inappropriate

**Evidence Completeness:** 30/100

**Overall Question Score:** 35/100 (exam scale 3.5/10)

**Improvement vs previous CIO exam:** Improved — Intent Industry correct, but sector detector over-weights 'Banks' → bank P/B frameworks dominate instead of FMCG/IT/PSU matrix. Template answer unchanged in substance.

### Q9 — PARTIAL (6.0/10) · Improved

**Question:** If crude oil prices fall by 25%, which Indian industries benefit first, and which benefit only after a lag?

**Final Answer (Ui executive summary):**  
The same macro move rarely affects every sector or market price the same way. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Additional evidence needed: Company- or sector-specific transmission map; Timing and magnitude of pass-through. Map the causal chain before applying one macro story everywhere.

**Intent Classification:** Correct — Ask=`Macro` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'alternative_data', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_MACRO_TRANSMISSION
- **Secondary:** FW_SCENARIO
- **Supporting:** FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Low (60%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=['Macro']; coverage=0.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Insufficient (0.2124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 60/100

**Overall Question Score:** 60/100 (exam scale 6.0/10)

**Improvement vs previous CIO exam:** Improved — Macro Transmission primary. Answer still transmission-generic; first vs lag beneficiaries not sharply institutionalised.

### Q10 — WEAK (4.0/10) · Improved

**Question:** Explain why hospitals often require a different valuation framework than pharmaceutical manufacturers.

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_HEALTHCARE_OPS
- **Secondary:** —
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_HISTORICAL_VALUATION, FW_INDUSTRY_STRUCTURE
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 40/100

**Overall Question Score:** 40/100 (exam scale 4.0/10)

**Improvement vs previous CIO exam:** Improved — Hospitals sector + Healthcare Ops + EV/EBITDA correctly selected (Track C). Narrative blocked; why-bullets still lean pharma FDA language rather than occupancy/ARPOB.

### Q11 — WEAK (4.0/10) · Regressed

**Question:** The RBI unexpectedly cuts the repo rate by 75 basis points. Trace the complete transmission mechanism through Banks, NBFCs, Real Estate, Auto, IT, and FMCG. Explain first-order and second-order effects.

**Final Answer (Ui executive summary):**  
Second-order macro chain (example oil shock): Oil ↑ → energy/logistics inflation ↑ → sticky inflation → policy rates stay higher for longer → discount rates / refinance coupons ↑ → valuation multiples ↓ AND industrial demand slows with a lag → orders delay → receivables/inventory stretch → working capital absorbs cash → credit metrics (coverage, leverage, runway) weaken → refinance probability falls. First-order ‘margins fall’ is necessary but insufficient; IC memos need the cascade into rates, demand, WC and credit. Second-order reasoning links macro to credit and valuation through time. Other possible explanations / points include: (1) Fiscal offsets or hedges truncate the chain. Additiona

**Intent Classification:** Correct — Ask=`Government` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'decision', 'iere']`; IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_PB, FW_POLICY, FW_RESIDUAL_INCOME
- **Secondary:** FW_MACRO_TRANSMISSION, FW_ROE
- **Supporting:** FW_DDM, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** FW_EV_EBITDA, FW_EV_SALES, FW_ROIC
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Macro': 1, 'Government': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7455)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Inappropriate

**Evidence Completeness:** 45/100

**Overall Question Score:** 40/100 (exam scale 4.0/10)

**Improvement vs previous CIO exam:** Regressed — REGRESSION risk: question mentions Banks → sector=banks so P/B/RI dominate over pure Macro Transmission. Delivered summary is an oil-shock template, not a 75bp repo cut chain.

### Q12 — WEAK (4.5/10) · Improved

**Question:** The Government doubles import duties on steel. Which sectors are likely to benefit, and which are likely to suffer? Explain the economic transmission.

**Final Answer (Ui executive summary):**  
Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk or funding terms worsened even as volume rose; (3) One-off items lifted the stronger-looking metric. Additional evidence needed: Bridge between the two metrics; Whether the quality deterioration is temporary or structural. Assess both together and wait for the linking evidence be

**Intent Classification:** Correct — Ask=`Government` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'decision', 'iere']`; IERE ranked_count=`5`

**Framework Selected:**
- **Primary:** FW_COMMODITY_CYCLE, FW_EV_EBITDA, FW_POLICY
- **Secondary:** FW_MACRO_TRANSMISSION
- **Supporting:** FW_INDUSTRY_STRUCTURE, FW_ROCE
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Government': 2, 'Industry': 2, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** High (0.8727)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 55/100

**Overall Question Score:** 45/100 (exam scale 4.5/10)

**Improvement vs previous CIO exam:** Improved — Government→Policy + steel Commodity Cycle frameworks correct. Final prose still generic quality language, not duty-transmission winners/losers.

### Q13 — FAIL (3.0/10) · Improved

**Question:** GST collections hit a record high for six consecutive months. What conclusions can—and cannot—be drawn from this?

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Government` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `alt_dash` · ALTERNATIVE_DATA · Alternative data coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'decision', 'iere']`; IERE ranked_count=`4`

**Framework Selected:**
- **Primary:** FW_POLICY
- **Secondary:** FW_MACRO_TRANSMISSION
- **Supporting:** FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Government': 2, 'AlternativeData': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.793)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 35/100

**Overall Question Score:** 30/100 (exam scale 3.0/10)

**Improvement vs previous CIO exam:** Improved — Policy framework selected. Answer still business-strength C template; no GST interpretation limits.

### Q14 — PARTIAL (5.5/10) · Improved

**Question:** How would a weakening Indian Rupee affect Infosys, Indigo, Maruti, and Oil Marketing Companies? Explain the mechanisms.

**Final Answer (Ui executive summary):**  
The same macro move rarely affects every sector or market price the same way. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Additional evidence needed: Company- or sector-specific transmission map; Timing and magnitude of pass-through. Map the causal chain before applying one macro story everywhere.

**Intent Classification:** Correct — Ask=`Macro` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`['INFY', 'INDIGO', 'MARUTI']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_INFY` · FINANCIAL_METRICS · INFY expectations
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - `ro_INFY` · TIMELINES · INFY research office
  - packs: `['company', 'government', 'relationship', 'alternative_data', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`4`

**Framework Selected:**
- **Primary:** FW_DCF, FW_EV_EBITDA, FW_MACRO_TRANSMISSION
- **Secondary:** FW_PE, FW_SCENARIO
- **Supporting:** FW_HISTORICAL_VALUATION, FW_ROIC
- **Forbidden rejected:** —
- **Framework confidence:** High (85%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 6, 'Historical': 1, 'Government': 1, 'AlternativeData': 3, 'Ownership': 1, 'Relationships': 3, 'Other': 1}
- **Gap detection:** missing=['Macro']; coverage=0.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Insufficient (0.3883)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 60/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement vs previous CIO exam:** Improved — Macro path + multi-entity bind. Framework stack includes macro transmission with IT primary overweight from INFY hint. Mechanisms for Indigo/Maruti/OMC thin.

### Q15 — FAIL (3.0/10) · Improved

**Question:** Inflation rises while GDP growth slows. Which sectors historically outperform in such an environment?

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. Framework insufficient: Capital Cycle / Supply Response (Institutional) — missing capex_or_supply_signal, returns_cycle, pricing_power_hint. The main point to watch is execution. Another supporting point is Execution policy: question typed as Macro; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Macro` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'relationship', 'alternative_data', 'decision', 'iere']`; IERE ranked_count=`5`

**Framework Selected:**
- **Primary:** FW_MACRO_TRANSMISSION
- **Secondary:** FW_SCENARIO
- **Supporting:** FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Macro': 1, 'Government': 1, 'Industry': 2, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.8255)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 30/100

**Overall Question Score:** 30/100 (exam scale 3.0/10)

**Improvement vs previous CIO exam:** Improved — Macro Transmission selected. Narrative remains template; no stagflation sector evidence.

### Q16 — PARTIAL (5.5/10) · Improved

**Question:** Suppose all of the following occur simultaneously: RBI cuts rates; Crude oil falls 20%; UPI transactions reach record highs; GST collections rise; The Government announces a new PLI scheme. Identify the Indian sectors most likely to benefit over the next 12–24 months, and explain your reasoning using evidence from macro, government, alternative data, industry, and company intelligence.

**Final Answer (Ui executive summary):**  
The impact differs across industries and market prices. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Additional evidence needed: Company- or sector-specific transmission map; Timing and magnitude of pass-through. Map the causal chain before applying one macro story everywhere.

**Intent Classification:** Correct — Ask=`CrossDomain` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `alt_dash` · ALTERNATIVE_DATA · Alternative data coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'expectation', 'decision', 'iere']`; IERE ranked_count=`7`

**Framework Selected:**
- **Primary:** FW_MACRO_TRANSMISSION
- **Secondary:** FW_SCENARIO
- **Supporting:** FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_INDUSTRY_STRUCTURE, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Macro': 1, 'Government': 2, 'Industry': 2, 'AlternativeData': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** High (0.9039)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 70/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement vs previous CIO exam:** Improved — CrossDomain + Macro Transmission + Scenario. Retrieval breadth remains a relative strength; narrative still not a CIO multi-impulse sector map.

### Q17 — FAIL (2.5/10) · Improved

**Question:** A company reports excellent quarterly earnings, but its stock falls 8% the next day. List at least ten institutional reasons why this can happen.

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. business strength and customer base delivery exceeds the base path and returns expand while the entry multiple stays reasonable. The main point to watch is execution. Another supporting point is Sector demand and operating leverage reinforce compounding.

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** —
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Macro': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7554)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 25/100

**Overall Question Score:** 25/100 (exam scale 2.5/10)

**Improvement vs previous CIO exam:** Improved — No longer forced to valuation; still fails to list ≥10 institutional reasons. Template C.

### Q18 — FAIL (3.0/10) · Improved

**Question:** Two companies have identical revenue growth and EPS growth, but one trades at twice the valuation multiple. Explain all plausible institutional reasons.

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** —
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7124)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 30/100

**Overall Question Score:** 30/100 (exam scale 3.0/10)

**Improvement vs previous CIO exam:** Improved — Education routing correct; executive summary still valuation-block text. Multiple-dispersion institutional catalogue absent.

### Q19 — FAIL (3.0/10) · Improved

**Question:** How should AGIB determine whether a company deserves a premium valuation rather than simply identifying that it has one?

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`Explain` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - packs: `['company', 'industry', 'government', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_HISTORICAL_VALUATION
- **Supporting:** FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Historical': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.7132)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 30/100

**Overall Question Score:** 30/100 (exam scale 3.0/10)

**Improvement vs previous CIO exam:** Improved — Framework Explanation + Historical Valuation selected. Answer does not operationalise premium-deserve tests.

### Q20 — FAIL (3.0/10) · No Change

**Question:** What evidence should AGIB gather before recommending that an analyst initiate research coverage on a newly listed Indian company?

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Analyse` / qtype=`business_quality` / gov_path=`clarification`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'expectation', 'decision', 'iere']`; IERE ranked_count=`2`

**Framework Selected:**
- **Primary:** —
- **Secondary:** FW_BUSINESS_QUALITY
- **Supporting:** FW_CASH_FLOW_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (70%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.6524)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 25/100

**Overall Question Score:** 30/100 (exam scale 3.0/10)

**Improvement vs previous CIO exam:** No Change — Clarification path; thin primary frameworks; coverage-initiation evidence checklist not produced.

### Q21 — WEAK (4.5/10) · Improved

**Question:** Using only institutional documents, explain how you would evaluate whether management's capital allocation policy has improved over the last five years.

**Final Answer (Ui executive summary):**  
Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk or funding terms worsened even as volume rose; (3) One-off items lifted the stronger-looking metric. Additional evidence needed: Bridge between the two metrics; Whether the quality deterioration is temporary or structural. Assess both together and wait for the linking evidence be

**Intent Classification:** Correct — Ask=`Documents` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`True`; ignored_hint=`INFY`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'expectation', 'decision', 'iere']`; IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_CAPITAL_ALLOCATION, FW_FRAMEWORK_EXPLANATION, FW_ROIC
- **Secondary:** FW_EV_EBITDA, FW_RISK
- **Supporting:** FW_CORPORATE_GOVERNANCE, FW_ROCE
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Government': 2, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.655)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Generic

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 40/100

**Overall Question Score:** 45/100 (exam scale 4.5/10)

**Improvement vs previous CIO exam:** Improved — Documents intent + Capital Allocation framework; ticker_hint INFY ignored (pollution blocked). Final answer still generic quality prose, not a 5-year document method.

### Q22 — FAIL (2.5/10) · Improved

**Question:** Which sections of an annual report are most useful for identifying emerging risks before they appear in the financial statements?

**Final Answer (Ui executive summary):**  
the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Documents` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'expectation', 'decision', 'iere']`; IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_RISK
- **Supporting:** FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION, FW_CORPORATE_GOVERNANCE, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Macro': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.6647)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too High

**Evidence Completeness:** 25/100

**Overall Question Score:** 25/100 (exam scale 2.5/10)

**Improvement vs previous CIO exam:** Improved — Documents + Risk framework selected. Answer does not name MDA/risk-factor/contingency sections.

### Q23 — FAIL (2.5/10) · No Change

**Question:** How would you detect inconsistencies between an investor presentation and the audited annual report?

**Final Answer (Ui executive summary):**  
Infosys continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Intent Classification:** Correct — Ask=`Documents` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`[]`; concept_mode=`True`; pollution_blocked=`True`; ignored_hint=`INFY`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - packs: `['company', 'industry', 'government', 'expectation', 'decision', 'iere']`; IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_RISK
- **Supporting:** FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION, FW_CORPORATE_GOVERNANCE, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Macro': 1, 'Government': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.6555)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Inappropriate

**Evidence Completeness:** 30/100

**Overall Question Score:** 25/100 (exam scale 2.5/10)

**Improvement vs previous CIO exam:** No Change — Ask Pipeline concept mode clears INFY, but UiService narrative still opens with Infosys — residual pollution outside Track A. No cross-document protocol.

### Q24 — WEAK (4.5/10) · Improved

**Question:** Replay Infosys as of 31 March 2020. Describe only the evidence that would have been available on that date. Explain how AGIB prevents future information leakage.

**Final Answer (Ui executive summary):**  
Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk or funding terms worsened even as volume rose; (3) One-off items lifted the stronger-looking metric. Additional evidence needed: Bridge between the two metrics; Whether the quality deterioration is temporary or structural. Assess both together and wait for the linking evidence be

**Intent Classification:** Correct — Ask=`HistoricalReplay` / qtype=`education` / gov_path=`education`

**Entity Resolution:** Correct — entities=`['INFY']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** Correct — as_of=`2020-03-31`

**Evidence Retrieved:**
  - (none / empty ranked list)
  - packs: `['company', 'portfolio', 'decision']`; IERE ranked_count=`0`

**Framework Selected:**
- **Primary:** FW_DCF, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_HISTORICAL_VALUATION
- **Secondary:** FW_PE
- **Supporting:** FW_ROIC
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Low (0.5712)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Generic

**Replay Review:** FAIL

**Confidence Review:** Too High

**Evidence Completeness:** 20/100

**Overall Question Score:** 45/100 (exam scale 4.5/10)

**Improvement vs previous CIO exam:** Improved — Track A sets as_of=2020-03-31; Historical Valuation primary. IERE ranked_count=0. Ui why still cites Current PE 14.3 — lookahead FAIL in delivered answer. Routing fixed; answer integrity not.

### Q25 — PARTIAL (6.0/10) · Improved

**Question:** Imagine you are presenting Reliance Industries to an Investment Committee. Construct the institutional evidence package you would prepare before anyone begins valuation. Do not value the company. List every evidence domain, document, macro factor, industry consideration, government policy, alternative dataset, historical context, and risk assessment that should be assembled first.

**Final Answer (Ui executive summary):**  
Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Intent Classification:** Correct — Ask=`CrossDomain` / qtype=`macro` / gov_path=`research`

**Entity Resolution:** Correct — entities=`['RELIANCE']`; concept_mode=`False`; pollution_blocked=`False`; ignored_hint=`None`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_RELIANCE` · FINANCIAL_METRICS · RELIANCE expectations
  - `rel_RELIANCE` · RELATIONSHIP_GRAPH · RELIANCE relationships
  - `ici_RELIANCE` · FINANCIAL_METRICS · RELIANCE company intelligence
  - `hist_RELIANCE` · HISTORICAL_VALUATION · RELIANCE historical object
  - `ind_RELIANCE` · RELATIONSHIP_GRAPH · Industry intelligence
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `alt_dash` · ALTERNATIVE_DATA · Alternative data coverage
  - `ro_RELIANCE` · TIMELINES · RELIANCE research office
  - packs: `['company', 'industry', 'government', 'alternative_data', 'expectation', 'portfolio', 'decision', 'iere']`; IERE ranked_count=`9`

**Framework Selected:**
- **Primary:** FW_MACRO_TRANSMISSION, FW_SOTP
- **Secondary:** FW_NAV, FW_SCENARIO
- **Supporting:** FW_CAPITAL_ALLOCATION, FW_HISTORICAL_VALUATION, FW_INDUSTRY_STRUCTURE
- **Forbidden rejected:** —
- **Framework confidence:** High (99%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 4, 'Historical': 2, 'Macro': 1, 'Government': 2, 'Industry': 3, 'AlternativeData': 2, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** High (0.9033)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Partially Correct

**Narrative Quality:** Weak

**Replay Review:** N/A

**Confidence Review:** Too Low

**Evidence Completeness:** 75/100

**Overall Question Score:** 60/100 (exam scale 6.0/10)

**Improvement vs previous CIO exam:** Improved — SOTP primary for conglomerates (Track C) with strong IERE packs. Executive summary valuation-blocked despite research path; why-bullets correctly warn against single-multiple on conglomerates.

---

## Bottom line

Tracks A, B, and C did their jobs as infrastructure. The CIO score moved from **3.7 → 4.3**, not to the 6–7 range, because the firm still reads **generic or blocked prose**.  

**Authorize Track D** (Institutional Narrative Generation) with an explicit requirement: every answer must render the Answer Assembly skeleton and Framework Explanation Object. Re-run this exact 25-question exam after Track D before any further expansion.
