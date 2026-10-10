# AGIB CIO Regression Exam Report — Post Track A + B + C + D

**Examiner role:** Independent Chief Investment Officer (certification board)  
**Candidate:** AGIB Ask Pipeline with Tracks A–D (Intent → Assembly → Framework Selection → Institutional Communication)  
**Date:** 2026-07-28  
**Questions:** Exact same 25 prompts as baseline and post-A+B+C exams  
**Execution path:** Question → Intent Resolution → IERE → Answer Assembly → Framework Selection → Existing Reasoning → **ICE** → UiService  
**Method constraint:** No prompt changes. No scoring-methodology changes. No AGIB capability changes. Measurement only.

---

## Verdict

### Overall score: **6.26 / 10**

| Version | CIO Score | Δ vs prior |
|---------|----------:|----------:|
| Baseline | 3.66 | — |
| Track A+B+C | 4.34 | +0.68 |
| **Track A+B+C+D** | **6.26** | **+1.92** |

### Certification: **PARTIALLY READY** (materially stronger)

**Not PRODUCTION READY. Not INSTITUTIONAL GRADE.**

Track D did what the prior exam predicted: it made the final answer **consume** A/B/C objects. Generic/blocked summaries collapsed to **0%**. Framework visibility is **100%**. The remaining gap is **depth of institutional content** inside those correctly structured answers — ICE cannot invent checklists that reasoning never produced.

### Score distribution (current)

| Verdict | Count |
|---------|------:|
| PARTIAL+ | 4 |
| PARTIAL | 11 |
| WEAK | 10 |

### Improvement vs post-A+B+C

| | Count |
|--|------:|
| Improved | 25 |
| No Change | 0 |
| Regressed | 0 |

---

## Executive finding (strict)

| Layer | Post A+B+C | Post A+B+C+D |
|-------|------------|--------------|
| Intent / Concept / Temporal | Solved | Solved |
| Framework selection | Accurate, invisible | Accurate, **visible** |
| Answer assembly | Executed, unused | Executed, **bound into response** |
| Ui narrative | Generic / blocked (~72%) | **ICE source 100%; generic 0%** |
| Deep CIO checklists (10 reasons, section protocols, etc.) | Missing | Still missing |
| Q24 lookahead in Ui | FAIL (Current PE) | **PASS** (as_of bound; no Current PE) |

Track D delivered the largest single-step score lift in the programme (**+1.9** vs A+B+C; **+2.6** vs baseline).

---

## Final scorecard

### Overall

| | Baseline | A+B+C | A+B+C+D | Δ vs ABC | Δ vs baseline |
|--|---------:|------:|-------:|---------:|--------------:|
| Overall | 3.66 | 4.34 | 6.26 | **+1.92** | **+2.6** |

### Category scores

| Category | Baseline | A+B+C | A+B+C+D | Δ vs ABC |
|----------|---------:|------:|-------:|---------:|
| Company | 5.4 | 6.1 | 7.5 | +1.4 |
| Industry | 2.9 | 4.2 | 6.3 | +2.1 |
| Macro | 3.6 | 4.0 | 5.7 | +1.7 |
| Cross | 2.9 | 3.4 | 5.5 | +2.1 |
| Documents | 2.67 | 3.17 | 5.67 | +2.5 |
| Replay | 4.0 | 4.5 | 6.5 | +2.0 |
| Institutional | 5.5 | 6.0 | 8.0 | +2.0 |

---

## KPI comparison (Delta analysis)

| KPI | Baseline | A+B+C | A+B+C+D | Δ vs ABC |
|-----|---------:|------:|-------:|---------:|
| Intent Routing | 40.0 | 100.0 | **100.0** | 0.0 |
| Entity Resolution (Ask) | 60.0 | 100.0 | **100.0** | 0.0 |
| Historical Routing | 0.0 | 100.0 | **100.0** | 0.0 |
| Framework Visibility (Ui) | 0.0 | 0.0 | **100.0** | 100.0 |
| ICE Answer Source Rate | 0.0 | 0.0 | **100.0** | 100.0 |
| Answer Assembly Executed | 0.0 | 100.0 | **100.0** | 0.0 |
| Generic/Blocked Summary Rate | 64.0 | 72.0 | **0.0** | -72.0 |
| Avg Latency (ms) | 7834 | 7902 | **21796** | 13894 |

---

## Failure analysis (ranked by impact)

### 1. Thin institutional content under correct structure (highest remaining)
ICE correctly shows frameworks/evidence/risks/confidence, but many answers still lack CIO-depth checklists (Q17 ten reasons; Q22 named report sections; Q13 GST limits).  
**Root cause:** Communication renders existing objects; reasoning content remains thin. Not a Track D defect — a content-depth bottleneck.

### 2. Track C sector keyword collisions (unchanged)
Q8/Q11 still overweight bank frameworks when the word “Banks” appears in multi-sector / macro prompts.

### 3. Historical evidence emptiness (Q24)
Routing + communication PASS; IERE `ranked_count=0` for 2020-03-31 — substance limited by KF historical population.

### 4. Evidence pollution in concept packs
Some concept questions still bind INFY KF objects into evidence lists (communication discloses them; hygiene incomplete).

### 5. Latency
Avg latency rose (~22s) in this run (environment/Yahoo 404s). Not treated as a quality regression for certification scoring.

---

## Recommendation answers

1. **Did Track D bind InstitutionalAnswer into the final response?** **Yes** — 25/25 Ui answers sourced from ICE.  
2. **Did narrative quality improve materially?** **Yes** — generic/blocked rate 72% → **0%**; narrative Good/Institutional on examiner scale for all 25.  
3. **Did framework explanations become visible?** **Yes** — 100% framework visibility.  
4. **Is AGIB institutional-grade?** **No** — structure is institutional; content depth is not yet.  
5. **Largest remaining bottleneck?** Depth of analytical content / checklists inside the now-correct communication frame (plus Track C multi-sector composition edges and historical KF population).  
6. **New intelligence packages?** **Not recommended** as the next move — deepen content binding / checklist coverage inside the existing stack.

---

## Pass / Fail decision

**PARTIALLY READY**

AGIB is now a coherent institutional **control + communication** stack for Ask. A multi-billion-dollar firm would see the right frameworks and evidence ordering, but would still reject many answers for insufficient analytical depth.

---

## Per-question grades (summary)

| Q | Section | Baseline | A+B+C | A+B+C+D | Δ vs ABC | Verdict |
|---|---------|---------:|------:|-------:|---------:|---------|
| Q1 | Company | 5.5 | 7.0 | 8.0 | +1.0 | PARTIAL+ |
| Q2 | Company | 6.0 | 6.5 | 7.5 | +1.0 | PARTIAL+ |
| Q3 | Company | 6.5 | 6.5 | 7.0 | +0.5 | PARTIAL |
| Q4 | Company | 4.0 | 4.5 | 6.5 | +2.0 | PARTIAL |
| Q5 | Company | 5.0 | 6.0 | 8.5 | +2.5 | PARTIAL+ |
| Q6 | Industry | 2.0 | 4.0 | 6.5 | +2.5 | PARTIAL |
| Q7 | Industry | 2.0 | 3.5 | 6.0 | +2.5 | PARTIAL |
| Q8 | Industry | 3.0 | 3.5 | 5.0 | +1.5 | WEAK |
| Q9 | Industry | 5.5 | 6.0 | 7.0 | +1.0 | PARTIAL |
| Q10 | Industry | 2.0 | 4.0 | 7.0 | +3.0 | PARTIAL |
| Q11 | Macro | 4.5 | 4.0 | 5.0 | +1.0 | WEAK |
| Q12 | Macro | 3.5 | 4.5 | 6.5 | +2.0 | PARTIAL |
| Q13 | Macro | 2.5 | 3.0 | 5.0 | +2.0 | WEAK |
| Q14 | Macro | 5.0 | 5.5 | 6.5 | +1.0 | PARTIAL |
| Q15 | Macro | 2.5 | 3.0 | 5.5 | +2.5 | WEAK |
| Q16 | Cross | 5.0 | 5.5 | 7.0 | +1.5 | PARTIAL |
| Q17 | Cross | 2.0 | 2.5 | 4.5 | +2.0 | WEAK |
| Q18 | Cross | 2.0 | 3.0 | 5.5 | +2.5 | WEAK |
| Q19 | Cross | 2.5 | 3.0 | 5.5 | +2.5 | WEAK |
| Q20 | Cross | 3.0 | 3.0 | 5.0 | +2.0 | WEAK |
| Q21 | Documents | 3.5 | 4.5 | 6.5 | +2.0 | PARTIAL |
| Q22 | Documents | 2.0 | 2.5 | 5.0 | +2.5 | WEAK |
| Q23 | Documents | 2.5 | 2.5 | 5.5 | +3.0 | WEAK |
| Q24 | Replay | 4.0 | 4.5 | 6.5 | +2.0 | PARTIAL |
| Q25 | Institutional | 5.5 | 6.0 | 8.0 | +2.0 | PARTIAL+ |

---

## Per-question examiner sheets

### Q1 — PARTIAL+ (8.0/10) · vs A+B+C: Improved

**Question:** Why is HDFC Bank primarily valued using Price-to-Book and Residual Income, while Infosys is commonly valued using EV/EBITDA and DCF? Explain the economic and accounting reasons, not just the formulas.

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_PB, FW_RESIDUAL_INCOME, FW_ROE Sector context: banks (source=company:HDFCBANK). Intent: Explain. The entity/context is a regulated bank with book value as the principal anchor of value. EV/EBITDA is explicitly excluded by the fram… Evidence items bound: 6. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `['HDFCBANK', 'INFY']`; concept=`False`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_HDFCBANK` · FINANCIAL_METRICS · HDFCBANK expectations
  - `ici_HDFCBANK` · FINANCIAL_METRICS · HDFCBANK company intelligence
  - `hist_HDFCBANK` · HISTORICAL_VALUATION · HDFCBANK historical object
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - `ro_HDFCBANK` · TIMELINES · HDFCBANK research office
  - IERE ranked_count=`6`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 75/100

**Overall Question Score:** 80/100 (exam scale 8.0/10)

**Improvement:** ICE renders P/B+Residual Income and bank book-value reason with EV/EBITDA excluded. Still thin on Infosys DCF/EV-EBITDA economic contrast in analysis body.

### Q2 — PARTIAL+ (7.5/10) · vs A+B+C: Improved

**Question:** Compare Infosys, TCS, and Wipro. If all three trade at similar P/E multiples, which additional evidence would you retrieve before concluding whether one is undervalued?

**Final Answer (Ui executive summary):**  
Intent: Analyse · Template: Company Analysis Frameworks applied: FW_DCF, FW_EV_EBITDA, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: it_services (source=company:INFY). Intent: Analyse. IT services are cash-generative operating businesses — DCF and EV/EBITDA apply. Evidence items bound: 8. Conclusions follow evidence and frameworks only.

**ICE:** template=`company_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Analyse` / qtype=`business_quality` / path=`research`

**Entity Resolution:** Correct — `['INFY', 'TCS', 'WIPRO']`; concept=`False`; pollution_blocked=`False`

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
  - IERE ranked_count=`8`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 75/100

**Overall Question Score:** 75/100 (exam scale 7.5/10)

**Improvement:** Company-analysis template + DCF/EV-EBITDA/peer frameworks visible. Evidence checklist still incomplete vs full institutional ask.

### Q3 — PARTIAL (7.0/10) · vs A+B+C: Improved

**Question:** If Titan reports 25% revenue growth but operating cash flow falls sharply, what evidence would you investigate before determining whether growth quality has deteriorated?

**Final Answer (Ui executive summary):**  
Intent: Analyse · Template: Company Analysis Frameworks applied: FW_DCF, FW_BUSINESS_QUALITY, FW_ECONOMIC_MOAT, FW_ROIC Sector context: consumer_staples (source=company:TITAN). Intent: Analyse. Evidence items bound: 5. Conclusions follow evidence and frameworks only.

**ICE:** template=`company_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Analyse` / qtype=`business_quality` / path=`research`

**Entity Resolution:** Correct — `['TITAN']`; concept=`False`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_TITAN` · FINANCIAL_METRICS · TITAN expectations
  - `ici_TITAN` · FINANCIAL_METRICS · TITAN company intelligence
  - `hist_TITAN` · FINANCIAL_METRICS · TITAN historical object
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ro_TITAN` · TIMELINES · TITAN research office
  - IERE ranked_count=`5`

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

**Overall Question Score:** 70/100 (exam scale 7.0/10)

**Improvement:** No longer template/gate noise; frameworks communicated. Titan jewellery operating checklist still missing.

### Q4 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** How would you assess whether Asian Paints has maintained its competitive moat over the last decade? Which evidence domains should AGIB retrieve?

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_DCF, FW_FRAMEWORK_EXPLANATION, FW_ECONOMIC_MOAT, FW_ROIC Sector context: consumer_staples (source=company:ASIANPAINT). Intent: Explain. Evidence items bound: 4. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `['ASIANPAINT']`; concept=`False`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT expectations
  - `ici_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT company intelligence
  - `hist_ASIANPAINT` · FINANCIAL_METRICS · ASIANPAINT historical object
  - `ro_ASIANPAINT` · TIMELINES · ASIANPAINT research office
  - IERE ranked_count=`4`

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

**Reasoning Review:** Partially Correct

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 50/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Economic Moat framework visible; decade evidence domains still not enumerated as a CIO checklist.

### Q5 — PARTIAL+ (8.5/10) · vs A+B+C: Improved

**Question:** Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_PB, FW_RESIDUAL_INCOME, FW_ROE Sector context: banks (source=keyword). Intent: Explain. The entity/context is a regulated bank with book value as the principal anchor of value. EV/EBITDA is explicitly excluded by the framework reg… Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Institutional

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 70/100

**Overall Question Score:** 85/100 (exam scale 8.5/10)

**Improvement:** Largest Track D win: blocked summary gone; P/B+RI+exclusion of EV/EBITDA explained. Accounting EBITDA-as-operating-cost nuance still under-developed.

### Q6 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** Why do cement companies often experience valuation expansion before earnings actually improve?

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_CEMENT_CAPACITY, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_REPLACEMENT_COST Sector context: cement (source=keyword). Intent: Explain. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 45/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Cement capacity + EV/EBITDA rendered. Utilisation→pricing→multiple-expansion chain still not synthesised in analysis.

### Q7 — PARTIAL (6.0/10) · vs A+B+C: Improved

**Question:** Why do software companies typically receive higher valuation multiples than steel producers?

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_DCF, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_PE Sector context: it_services (source=keyword). Intent: Explain. IT services are cash-generative operating businesses — DCF and EV/EBITDA apply. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Reasoning Review:** Partially Correct

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 40/100

**Overall Question Score:** 60/100 (exam scale 6.0/10)

**Improvement:** IT frameworks communicated; steel/commodity contrast remains incomplete (sector detector).

### Q8 — WEAK (5.0/10) · vs A+B+C: Improved

**Question:** Compare the business economics of FMCG, IT Services, and PSU Banks. Which KPIs matter most for each and why?

**Final Answer (Ui executive summary):**  
Intent: Industry · Template: Industry Analysis Frameworks applied: FW_INDUSTRY_STRUCTURE, FW_PB, FW_RESIDUAL_INCOME, FW_PORTERS_FIVE Sector context: banks (source=keyword). Intent: Industry. The entity/context is a regulated bank with book value as the principal anchor of value. EV/EBITDA is explicitly excluded by the framework re… Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`industry_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Industry` / qtype=`sector` / path=`clarification`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Inappropriate

**Evidence Completeness:** 35/100

**Overall Question Score:** 50/100 (exam scale 5.0/10)

**Improvement:** Industry template replaces C-grade template, but sector detector still overweights Banks vs FMCG/IT/PSU matrix.

### Q9 — PARTIAL (7.0/10) · vs A+B+C: Improved

**Question:** If crude oil prices fall by 25%, which Indian industries benefit first, and which benefit only after a lag?

**Final Answer (Ui executive summary):**  
Intent: Macro · Template: Macro Analysis Frameworks applied: FW_MACRO_TRANSMISSION, FW_SCENARIO, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: Macro. Macro / cross-domain questions use transmission and scenario frameworks. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`macro_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Macro` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`2`

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

**Overall Question Score:** 70/100 (exam scale 7.0/10)

**Improvement:** Macro Transmission primary and visible; first-vs-lag beneficiaries still not sharply listed.

### Q10 — PARTIAL (7.0/10) · vs A+B+C: Improved

**Question:** Explain why hospitals often require a different valuation framework than pharmaceutical manufacturers.

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_HEALTHCARE_OPS, FW_ACCOUNTING_QUALITY Sector context: hospitals (source=keyword). Intent: Explain. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 55/100

**Overall Question Score:** 70/100 (exam scale 7.0/10)

**Improvement:** Healthcare Ops + EV/EBITDA visible — major vs blocked baseline. Occupancy/ARPOB economics not fully explained.

### Q11 — WEAK (5.0/10) · vs A+B+C: Improved

**Question:** The RBI unexpectedly cuts the repo rate by 75 basis points. Trace the complete transmission mechanism through Banks, NBFCs, Real Estate, Auto, IT, and FMCG. Explain first-order and second-order effects.

**Final Answer (Ui executive summary):**  
Intent: Government · Template: Government / Policy Analysis Frameworks applied: FW_PB, FW_POLICY, FW_RESIDUAL_INCOME, FW_MACRO_TRANSMISSION Sector context: banks (source=keyword). Intent: Government. The entity/context is a regulated bank with book value as the principal anchor of value. EV/EBITDA is explicitly excluded by the framework… Evidence items bound: 3. Conclusions follow evidence and frameworks only.

**ICE:** template=`government_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Government` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`3`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Inappropriate

**Evidence Completeness:** 50/100

**Overall Question Score:** 50/100 (exam scale 5.0/10)

**Improvement:** Oil-shock template removed (Track D). Bank-framework overweight from keyword 'Banks' remains a Track C composition flaw; rate-cut chain still incomplete.

### Q12 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** The Government doubles import duties on steel. Which sectors are likely to benefit, and which are likely to suffer? Explain the economic transmission.

**Final Answer (Ui executive summary):**  
Intent: Government · Template: Government / Policy Analysis Frameworks applied: FW_COMMODITY_CYCLE, FW_EV_EBITDA, FW_POLICY, FW_MACRO_TRANSMISSION Sector context: steel (source=keyword). Intent: Government. Government questions use the policy framework. Evidence items bound: 5. Conclusions follow evidence and frameworks only.

**ICE:** template=`government_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Government` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`5`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 55/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Policy + commodity cycle frameworks communicated; winner/loser transmission still thin.

### Q13 — WEAK (5.0/10) · vs A+B+C: Improved

**Question:** GST collections hit a record high for six consecutive months. What conclusions can—and cannot—be drawn from this?

**Final Answer (Ui executive summary):**  
Intent: Government · Template: Government / Policy Analysis Frameworks applied: FW_POLICY, FW_MACRO_TRANSMISSION, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: Government. Government questions use the policy framework. Evidence items bound: 4. Conclusions follow evidence and frameworks only.

**ICE:** template=`government_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Government` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `alt_dash` · ALTERNATIVE_DATA · Alternative data coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`4`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 40/100

**Overall Question Score:** 50/100 (exam scale 5.0/10)

**Improvement:** Policy framework visible; GST can/cannot conclusions still not institutionalised.

### Q14 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** How would a weakening Indian Rupee affect Infosys, Indigo, Maruti, and Oil Marketing Companies? Explain the mechanisms.

**Final Answer (Ui executive summary):**  
Intent: Macro · Template: Macro Analysis Frameworks applied: FW_DCF, FW_EV_EBITDA, FW_MACRO_TRANSMISSION, FW_PE Sector context: it_services (source=company:INFY). Intent: Macro. IT services are cash-generative operating businesses — DCF and EV/EBITDA apply. Evidence items bound: 4. Conclusions follow evidence and frameworks only.

**ICE:** template=`macro_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Macro` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `['INFY', 'INDIGO', 'MARUTI']`; concept=`False`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `exp_INFY` · FINANCIAL_METRICS · INFY expectations
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - `ro_INFY` · TIMELINES · INFY research office
  - IERE ranked_count=`4`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 60/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Macro template + multi-entity bind; Indigo/Maruti/OMC mechanisms still thin vs INFY overweight.

### Q15 — WEAK (5.5/10) · vs A+B+C: Improved

**Question:** Inflation rises while GDP growth slows. Which sectors historically outperform in such an environment?

**Final Answer (Ui executive summary):**  
Intent: Macro · Template: Macro Analysis Frameworks applied: FW_MACRO_TRANSMISSION, FW_SCENARIO, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: Macro. Macro / cross-domain questions use transmission and scenario frameworks. Evidence items bound: 5. Conclusions follow evidence and frameworks only.

**ICE:** template=`macro_analysis`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Macro` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`5`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 35/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement:** Macro Transmission communicated; stagflation outperformers list still absent.

### Q16 — PARTIAL (7.0/10) · vs A+B+C: Improved

**Question:** Suppose all of the following occur simultaneously: RBI cuts rates; Crude oil falls 20%; UPI transactions reach record highs; GST collections rise; The Government announces a new PLI scheme. Identify the Indian sectors most likely to benefit over the next 12–24 months, and explain your reasoning using evidence from macro, government, alternative data, industry, and company intelligence.

**Final Answer (Ui executive summary):**  
Intent: CrossDomain · Template: Investment Committee Brief Frameworks applied: FW_MACRO_TRANSMISSION, FW_SCENARIO, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: CrossDomain. Macro / cross-domain questions use transmission and scenario frameworks. Evidence items bound: 7. Conclusions follow evidence and frameworks only.

**ICE:** template=`investment_committee_brief`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `CrossDomain` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `rel_INFY` · RELATIONSHIP_GRAPH · INFY relationships
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ind_INFY` · RELATIONSHIP_GRAPH · Industry intelligence
  - `alt_dash` · ALTERNATIVE_DATA · Alternative data coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`7`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 70/100

**Overall Question Score:** 70/100 (exam scale 7.0/10)

**Improvement:** IC brief + Macro Transmission/Scenario visible with strong retrieval; sector map still not fully written.

### Q17 — WEAK (4.5/10) · vs A+B+C: Improved

**Question:** A company reports excellent quarterly earnings, but its stock falls 8% the next day. List at least ten institutional reasons why this can happen.

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: Explain. Evidence items bound: 3. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`3`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 30/100

**Overall Question Score:** 45/100 (exam scale 4.5/10)

**Improvement:** Generic C-template gone; still fails ≥10 institutional reasons — ICE cannot invent missing reasoning content.

### Q18 — WEAK (5.5/10) · vs A+B+C: Improved

**Question:** Two companies have identical revenue growth and EPS growth, but one trades at twice the valuation multiple. Explain all plausible institutional reasons.

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY, FW_HISTORICAL_VALUATION Sector context: generic (source=default). Intent: Explain. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 35/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement:** Education path communicated with frameworks; multiple-dispersion catalogue still incomplete.

### Q19 — WEAK (5.5/10) · vs A+B+C: Improved

**Question:** How should AGIB determine whether a company deserves a premium valuation rather than simply identifying that it has one?

**Final Answer (Ui executive summary):**  
Intent: Explain · Template: Educational Explanation Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_HISTORICAL_VALUATION, FW_ACCOUNTING_QUALITY, FW_BUSINESS_QUALITY Sector context: generic (source=default). Intent: Explain. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`educational`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Explain` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · HISTORICAL_VALUATION · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 35/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement:** Framework Explanation + Historical Valuation visible; premium-deserve tests not operationalised.

### Q20 — WEAK (5.0/10) · vs A+B+C: Improved

**Question:** What evidence should AGIB gather before recommending that an analyst initiate research coverage on a newly listed Indian company?

**Final Answer (Ui executive summary):**  
Intent: Analyse · Template: Research Note Frameworks applied: FW_BUSINESS_QUALITY, FW_CASH_FLOW_QUALITY, FW_HISTORICAL_VALUATION, FW_PEER_COMPARISON Sector context: generic (source=default). Intent: Analyse. Evidence items bound: 2. Conclusions follow evidence and frameworks only.

**ICE:** template=`research_note`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Analyse` / qtype=`business_quality` / path=`clarification`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`2`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 30/100

**Overall Question Score:** 50/100 (exam scale 5.0/10)

**Improvement:** Research-note template replaces clarification noise; coverage-initiation checklist still thin.

### Q21 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** Using only institutional documents, explain how you would evaluate whether management's capital allocation policy has improved over the last five years.

**Final Answer (Ui executive summary):**  
Intent: Documents · Template: Research Note Frameworks applied: FW_CAPITAL_ALLOCATION, FW_FRAMEWORK_EXPLANATION, FW_ROIC, FW_EV_EBITDA Sector context: industrials (source=keyword). Intent: Documents. Evidence items bound: 3. Conclusions follow evidence and frameworks only.

**ICE:** template=`research_note`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Documents` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`True`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `gov_dash` · GOVERNMENT_POLICIES · Government intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`3`

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

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 45/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Capital Allocation framework communicated; 5-year document method still not detailed.

### Q22 — WEAK (5.0/10) · vs A+B+C: Improved

**Question:** Which sections of an annual report are most useful for identifying emerging risks before they appear in the financial statements?

**Final Answer (Ui executive summary):**  
Intent: Documents · Template: Research Note Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_RISK, FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION Sector context: generic (source=default). Intent: Documents. Evidence items bound: 3. Conclusions follow evidence and frameworks only.

**ICE:** template=`research_note`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Documents` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`False`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `ici_INFY` · FINANCIAL_METRICS · INFY company intelligence
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_RISK
- **Supporting:** FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION, FW_CORPORATE_GOVERNANCE, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 2, 'Macro': 1, 'Government': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.6647)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 30/100

**Overall Question Score:** 50/100 (exam scale 5.0/10)

**Improvement:** Risk framework visible; does not name MDA/risk-factor/contingency sections explicitly.

### Q23 — WEAK (5.5/10) · vs A+B+C: Improved

**Question:** How would you detect inconsistencies between an investor presentation and the audited annual report?

**Final Answer (Ui executive summary):**  
Intent: Documents · Template: Research Note Frameworks applied: FW_FRAMEWORK_EXPLANATION, FW_RISK, FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION Sector context: generic (source=default). Intent: Documents. Evidence items bound: 3. Conclusions follow evidence and frameworks only.

**ICE:** template=`research_note`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `Documents` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `[]`; concept=`True`; pollution_blocked=`True`

**Temporal Routing:** N/A — as_of=`None`

**Evidence Retrieved:**
  - `macro_cov` · MACRO_INDICATORS · Macro intelligence coverage
  - `ici_INFY` · OWNERSHIP · INFY company intelligence
  - `hist_INFY` · FINANCIAL_METRICS · INFY historical object
  - IERE ranked_count=`3`

**Framework Selected:**
- **Primary:** FW_FRAMEWORK_EXPLANATION
- **Secondary:** FW_RISK
- **Supporting:** FW_BUSINESS_QUALITY, FW_CAPITAL_ALLOCATION, FW_CORPORATE_GOVERNANCE, FW_HISTORICAL_VALUATION
- **Forbidden rejected:** —
- **Framework confidence:** Moderate (75%)

**Answer Assembly Review:**
- **Evidence ordering:** domains={'Financial': 1, 'Macro': 1, 'Government': 1, 'Ownership': 1, 'Other': 1}
- **Gap detection:** missing=[]; coverage=1.0
- **Skeleton completeness:** ['executive_summary', 'evidence', 'analysis', 'framework', 'risks', 'conclusion', 'confidence', 'sources']
- **Confidence calibration:** Moderate (0.6555)
- **Citation mapping:** coverage=1.0

**Reasoning Review:** Incorrect

**Narrative Quality:** Good

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 35/100

**Overall Question Score:** 55/100 (exam scale 5.5/10)

**Improvement:** Ui no longer opens with Infosys pollution; cross-document protocol still missing.

### Q24 — PARTIAL (6.5/10) · vs A+B+C: Improved

**Question:** Replay Infosys as of 31 March 2020. Describe only the evidence that would have been available on that date. Explain how AGIB prevents future information leakage.

**Final Answer (Ui executive summary):**  
Intent: HistoricalReplay · Template: Historical Replay Frameworks applied: FW_DCF, FW_EV_EBITDA, FW_FRAMEWORK_EXPLANATION, FW_HISTORICAL_VALUATION Sector context: it_services (source=company:INFY). Intent: HistoricalReplay. IT services are cash-generative operating businesses — DCF and EV/EBITDA apply. Historical replay as_of=2020-03-31 — current prices excluded.

**ICE:** template=`historical_replay`; framework_visible=`True`; validation=`False`; source=`institutional_communication`

**Intent Classification:** Correct — `HistoricalReplay` / qtype=`education` / path=`education`

**Entity Resolution:** Correct — `['INFY']`; concept=`False`; pollution_blocked=`False`

**Temporal Routing:** Correct — as_of=`2020-03-31`

**Evidence Retrieved:**
  - (none / empty ranked list)
  - IERE ranked_count=`0`

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

**Reasoning Review:** Partially Correct

**Narrative Quality:** Good

**Replay Review:** PASS

**Confidence Review:** Appropriate

**Evidence Completeness:** 25/100

**Overall Question Score:** 65/100 (exam scale 6.5/10)

**Improvement:** Historical-replay template states as_of=2020-03-31 and excludes current prices; no Current PE in Ui. IERE ranked_count=0 so substance thin. (ICE gate false-positive on 'current prices excluded' wording.)

### Q25 — PARTIAL+ (8.0/10) · vs A+B+C: Improved

**Question:** Imagine you are presenting Reliance Industries to an Investment Committee. Construct the institutional evidence package you would prepare before anyone begins valuation. Do not value the company. List every evidence domain, document, macro factor, industry consideration, government policy, alternative dataset, historical context, and risk assessment that should be assembled first.

**Final Answer (Ui executive summary):**  
Intent: CrossDomain · Template: Investment Committee Brief Frameworks applied: FW_MACRO_TRANSMISSION, FW_SOTP, FW_NAV, FW_SCENARIO Sector context: conglomerates (source=company:RELIANCE). Intent: CrossDomain. Multi-business groups require Sum-of-the-Parts, not a single multiple. Evidence items bound: 9. Conclusions follow evidence and frameworks only.

**ICE:** template=`investment_committee_brief`; framework_visible=`True`; validation=`True`; source=`institutional_communication`

**Intent Classification:** Correct — `CrossDomain` / qtype=`macro` / path=`research`

**Entity Resolution:** Correct — `['RELIANCE']`; concept=`False`; pollution_blocked=`False`

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
  - IERE ranked_count=`9`

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

**Narrative Quality:** Institutional

**Replay Review:** N/A

**Confidence Review:** Appropriate

**Evidence Completeness:** 80/100

**Overall Question Score:** 80/100 (exam scale 8.0/10)

**Improvement:** IC brief + SOTP primary with rich packs; blocked valuation summary gone. Full domain inventory still not exhaustively listed.

---

## Bottom line

| Version | CIO Score | Primary Improvement |
|---------|----------:|---------------------|
| Baseline | 3.7/10 | Retrieval + governance restraint |
| Track A+B+C | 4.3/10 | Routing + assembly + framework selection |
| **Track A+B+C+D** | **6.3/10** | **Communication binds InstitutionalAnswer** |

The programme hypothesis is confirmed: once A/B/C were correct, **Track D produced the largest score jump** by making the final response consume those objects. Remaining work is content depth inside the now-correct institutional frame — not another intelligence package.
