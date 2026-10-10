# AGIB CIO Examination Report

**Examiner:** Cursor Cloud Agent (Chief Knowledge Retrieval Architect / CIO exam board)
**Candidate:** AGIB Ask Pipeline + IERE + UiService.search
**Date:** 2026-07-28 12:50 UTC
**Questions:** 25 CIO-level institutional prompts
**Runtime:** all 25 executed without crash (avg latency ~7834 ms)

## Verdict

**Overall score: 3.7 / 10 — NOT YET INSTITUTIONAL PASS**

AGIB can *retrieve* multi-domain evidence and *refuse* unsupported valuation claims. It cannot yet *answer* CIO conceptual questions with precise, multi-layer institutional synthesis. The stack behaves like a guarded research operating system with thin conceptual reasoning — not yet like a senior analyst.

### Score distribution

- **FAIL:** 11
- **PARTIAL:** 7
- **PARTIAL+:** 1
- **PARTIAL-:** 1
- **WEAK:** 5

### What worked

1. **End-to-end Ask path is live** — every question completed; no process failures.
2. **IERE is real** — ranked Evidence Packs with citations across company/industry/macro/government/historical/cross-domain (best on Q16/Q25).
3. **Governance honesty** — valuation contracts block unsupported “cheap/expensive” narrative when required multiples are missing.
4. **Some institutional heuristics survive in Why-bullets** — bank P/B orthodoxy, IT utilisation/TCV, conglomerate segment valuation, cash≠revenue.
5. **Point-in-time replay gate** — IERE `as_of=2020-03-31` returned `future_leakage=false` (empty pack because KF lacks 2020-dated objects).

### What failed (examiner board)

1. **Question misrouting** — conceptual / education / process questions often typed as valuation → blocked or generic company template.
2. **Entity pollution** — non-entity questions attached Infosys or Adani documents.
3. **Editorial layer down** — Gemini API key invalid → template fallback produced low-quality prose and ignored the actual question.
4. **Live fundamentals fragile** — Yahoo `INFY.NS` / `RELIANCE.NS` 404s in this environment; answers leaned on soft KF scaffolds.
5. **Historical replay not wired into Ask** — IERE PIT filter OK, but Ask answer for Q24 used current 2026 market data (lookahead).
6. **Knowledge errors** — Titan classified as mining; generic “business strength rated C” reused across unrelated questions.
7. **Synthesis gap** — retrieval > reasoning. Packs assembled; CIO-grade explanation often absent.

## Per-question grades

| Q | Section | Score | Verdict | IERE packs | Latency |
|---|---------|------:|---------|------------|--------:|
| Q1 | Company | 5.5 | PARTIAL | 2 | 20690 |
| Q2 | Company | 6.0 | PARTIAL | 2 | 18420 |
| Q3 | Company | 6.5 | PARTIAL+ | 3 | 15826 |
| Q4 | Company | 4.0 | WEAK | 2 | 14686 |
| Q5 | Company | 5.0 | PARTIAL | 2 | 642 |
| Q6 | Industry | 2.0 | FAIL | 2 | 624 |
| Q7 | Industry | 2.0 | FAIL | 2 | 591 |
| Q8 | Industry | 3.0 | FAIL | 1 | 1975 |
| Q9 | Industry | 5.5 | PARTIAL | 1 | 36397 |
| Q10 | Industry | 2.0 | FAIL | 2 | 575 |
| Q11 | Macro | 4.5 | WEAK | 2 | 623 |
| Q12 | Macro | 3.5 | WEAK | 3 | 669 |
| Q13 | Macro | 2.5 | FAIL | 3 | 631 |
| Q14 | Macro | 5.0 | PARTIAL | 2 | 15313 |
| Q15 | Macro | 2.5 | FAIL | 3 | 641 |
| Q16 | Cross | 5.0 | PARTIAL | 5 | 750 |
| Q17 | Cross | 2.0 | FAIL | 2 | 693 |
| Q18 | Cross | 2.0 | FAIL | 2 | 625 |
| Q19 | Cross | 2.5 | FAIL | 2 | 643 |
| Q20 | Cross | 3.0 | WEAK | 1 | 734 |
| Q21 | Documents | 3.5 | WEAK | 3 | 14915 |
| Q22 | Documents | 2.0 | FAIL | 2 | 615 |
| Q23 | Documents | 2.5 | FAIL | 3 | 16356 |
| Q24 | Replay | 4.0 | PARTIAL- | 1 | 15594 |
| Q25 | Institutional | 5.5 | PARTIAL | 6 | 16642 |

## Detailed examiner notes

### Q1 — PARTIAL (5.5/10)

**Question:** Why is HDFC Bank primarily valued using Price-to-Book and Residual Income, while Infosys is commonly valued using EV/EBITDA and DCF? Explain the economic and accounting reasons, not just the formulas.

**Candidate summary:** Yes — book value can rise while price-to-book falls when the share price does not keep pace with book equity. Price-to-book is price divided by book value. If book equity grows faster than the share price — or the price falls — the multiple compresses even though book value is higher. Other possible explanations include: (1) Investors marked down return expectations on equity; (2) Market-wide de-rating of financials 

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Return on Equity: Net income divided by book equity; accounting return to shareholders. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Using manufacturing WACC/DCF as primary bank valuation
- Decision: Underwrite deposit franchise (CASA) before loan growth narratives
- Current PE 16.492487 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 11.747604 sits below trailing PE 16.492487, consistent with expected earnings improvement already partly in the price. PEG around 0.89 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. Dividend yield near 1.8%

**IERE:** ranked=6 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=6 gate_fails=[]

**Examiner:** Candidate partially understood bank valuation orthodoxy (Avoid manufacturing WACC/DCF; prefer P/B + ROE/COE; CASA underwriting) but never cleanly contrasted Infosys EV/EBITDA/DCF economics. Summary drifted into P/B mechanics. Residual Income named in frameworks elsewhere but not explained. IERE pulled HDFC+INFY packs — good retrieval, weak synthesis.

### Q2 — PARTIAL (6.0/10)

**Question:** Compare Infosys, TCS, and Wipro. If all three trade at similar P/E multiples, which additional evidence would you retrieve before concluding whether one is undervalued?

**Candidate summary:** A valuation multiple can move differently from earnings because price and the earnings base are separate inputs. Multiples compress or expand when investors change growth assumptions, risk appetite or the peer set — even if the company earns more. Other possible explanations include: (1) Price lagged earnings; (2) Market-wide de-rating; (3) Earnings composition changed. Additional evidence needed: Price path vs earni

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring attrition/utilisation
- Decision: Lead with large deal TCV/pipeline and utilisation before multiple expansion stories
- Current PE 14.309564 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 13.831805 sits below trailing PE 14.309564, consistent with expected earnings improvement already partly in the price. PEG around 1.91 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 974.6x a

**IERE:** ranked=8 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=8 gate_fails=[]

**Examiner:** Correct instinct: do not conclude undervaluation from similar P/E alone. Why-bullets mention FCF, attrition/utilisation, TCV/pipeline — the right IT evidence domains. Failed to explicitly retrieve/compare ROIC, FCF conversion, deal mix, client concentration, return of capital, and expectation gaps across INFY/TCS/WIPRO. IERE did retrieve all three company objects.

### Q3 — PARTIAL+ (6.5/10)

**Question:** If Titan reports 25% revenue growth but operating cash flow falls sharply, what evidence would you investigate before determining whether growth quality has deteriorated?

**Candidate summary:** Higher revenue does not guarantee stronger cash generation. Cash can fall when working capital rises, capital expenditure increases, or accruals run ahead of collections. Sales are recognised on an accrual basis. Free cash flow subtracts cash stuck in inventory and receivables and cash spent on investing. Those bridges can turn a revenue increase into weaker cash. Other possible explanations include: (1) inventory bu

**Key why-bullets:**
- Committee vote 7 / 9 → Neutral (Low conviction).
- ROIC: After-tax operating return on capital invested in operations (debt + equity capital, adjusted). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring royalty/policy shocks
- Decision: Prefer FCF yield through the cycle
- Current PE 84.54847 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 56.85315 sits below trailing PE 84.54847, consistent with expected earnings improvement already partly in the price. EV/EBITDA around 56.8x adds an enterprise-value lens beyond equity multiples. Dividend yield near 32.0% informs shareholder-return capacity along

**IERE:** ranked=5 packs=['COMPANY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=5 gate_fails=[]

**Examiner:** Strong on cash vs accrual distinction (WC, capex, accruals). Weak on Titan-specific evidence checklist (jewellery inventory days, gold hedging, lease liabilities, channel financing, store openings vs SSSG). Misclassified Titan as mining — serious knowledge error.

### Q4 — WEAK (4.0/10)

**Question:** How would you assess whether Asian Paints has maintained its competitive moat over the last decade? Which evidence domains should AGIB retrieve?

**Candidate summary:** Asian Paints continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 7 / 9 → Neutral (Low conviction).
- Working Capital: Capital tied in the operating cycle; analytically often non-cash net working capital (AR + Inventory - AP - deferred items, etc.). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Paying premium multiples for price-led growth without volume
- Decision: Separate volume vs price/mix before calling growth high-quality
- Current PE 60.817955 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 46.521988 sits below trailing PE 60.817955, consistent with expected earnings improvement already partly in the price. EV/EBITDA around 40.6x adds an enterprise-value lens beyond equity multiples. Dividend yield near 101.0% informs shareholder-return capacity a

**IERE:** ranked=4 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=4 gate_fails=[]

**Examiner:** Did not assemble decade moat evidence (dealer network density, pricing power vs Berger, rural mix, ROCE trend, advertising intensity, capacity). Defaulted to generic business-quality grade C and missing peer PE. Domains not enumerated as asked.

### Q5 — PARTIAL (5.0/10)

**Question:** Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Return on Equity: Net income divided by book equity; accounting return to shareholders. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Using manufacturing WACC/DCF as primary bank valuation
- Decision: Underwrite deposit franchise (CASA) before loan growth narratives
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available. For banks, prefer P/B + ROE/COE framing beside PE; PE alone misleads across credit cycles.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Why-bullets correctly say prefer P/B+ROE/COE and avoid manufacturing WACC/DCF; summary blocked as valuation without entity. Missed core accounting reason: interest expense is operating for banks; EBITDA meaningless; EV definition breaks with deposits-as-funding. Entity resolution polluted with Adani docs — fail for cleanliness.

### Q6 — FAIL (2.0/10)

**Question:** Why do cement companies often experience valuation expansion before earnings actually improve?

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- ROIC: After-tax operating return on capital invested in operations (debt + equity capital, adjusted). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: National average pricing for regional cement economics
- Decision: Lead with regional demand-supply and EBITDA/tonne before national narratives
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Blocked valuation narrative. No cement cycle economics (utilisation → pricing power → multiple expansion before EPS). Industry intelligence not synthesised.

### Q7 — FAIL (2.0/10)

**Question:** Why do software companies typically receive higher valuation multiples than steel producers?

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- ROIC: After-tax operating return on capital invested in operations (debt + equity capital, adjusted). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Peak-spread multiples
- Decision: Locate cycle position before extrapolating EBITDA
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Blocked. No discussion of capital intensity, ROIC durability, commodity vs IP economics, reinvestment, or cyclicality differentials.

### Q8 — FAIL (3.0/10)

**Question:** Compare the business economics of FMCG, IT Services, and PSU Banks. Which KPIs matter most for each and why?

**Candidate summary:** the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Return on Equity: Net income divided by book equity; accounting return to shareholders. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Using manufacturing WACC/DCF as primary bank valuation
- Decision: Underwrite deposit franchise (CASA) before loan growth narratives
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available. For banks, prefer P/B + ROE/COE framing beside PE; PE alone misleads across credit cycles.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Template fallback; no structured KPI matrix for FMCG/IT/PSU banks (GM/A&P/SSS; utilisation/attrition/TCV; NIM/GNPA/CASA/PCR).

### Q9 — PARTIAL (5.5/10)

**Question:** If crude oil prices fall by 25%, which Indian industries benefit first, and which benefit only after a lag?

**Candidate summary:** The same macro move rarely affects every sector or market price the same way. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Ad

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Working Capital: Capital tied in the operating cycle; analytically often non-cash net working capital (AR + Inventory - AP - deferred items, etc.). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Peak-cycle multiple on refining earnings
- Decision: Separate upstream/refining/marketing; use mid-cycle assumptions
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Acknowledged heterogeneous transmission by business model/funding/inputs — correct framing. Did not name first-order beneficiaries (OMCs/refiners margins, tyre, paints, airlines with lag on hedge books; petrochem feedstock) vs lagged (FMCG via inflation, autos via real incomes).

### Q10 — FAIL (2.0/10)

**Question:** Explain why hospitals often require a different valuation framework than pharmaceutical manufacturers.

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- ROIC: After-tax operating return on capital invested in operations (debt + equity capital, adjusted). Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Extrapolating one-off launch profits
- Decision: Haircut for FDA/compliance risk before multiple expansion
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Blocked. Missed hospital EV/EBITDA bed economics, occupancy, ARPOB vs pharma DCF/pipeline/patent cliffs.

### Q11 — WEAK (4.5/10)

**Question:** The RBI unexpectedly cuts the repo rate by 75 basis points. Trace the complete transmission mechanism through Banks, NBFCs, Real Estate, Auto, IT, and FMCG. Explain first-order and second-order effects.

**Candidate summary:** Second-order macro chain (example oil shock): Oil ↑ → energy/logistics inflation ↑ → sticky inflation → policy rates stay higher for longer → discount rates / refinance coupons ↑ → valuation multiples ↓ AND industrial demand slows with a lag → orders delay → receivables/inventory stretch → working capital absorbs cash → credit metrics (coverage, leverage, runway) weaken → refinance probability falls. First-order ‘mar

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Return on Equity: Net income divided by book equity; accounting return to shareholders. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Using manufacturing WACC/DCF as primary bank valuation
- Decision: Underwrite deposit franchise (CASA) before loan growth narratives
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available. For banks, prefer P/B + ROE/COE framing beside PE; PE alone misleads across credit cycles.

**IERE:** ranked=3 packs=['COMPANY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK'] citations=3 gate_fails=[]

**Examiner:** Offered a generic second-order oil-shock chain rather than a 75bp repo cut transmission through Banks→NBFCs→RE→Auto→IT→FMCG. Wrong macro impulse in the summary. IERE did retrieve MACRO pack.

### Q12 — WEAK (3.5/10)

**Question:** The Government doubles import duties on steel. Which sectors are likely to benefit, and which are likely to suffer? Explain the economic transmission.

**Candidate summary:** Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk 

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- WACC: The weighted average cost of capital — blended required return on the firm's debt and equity capital used as a discount/hurdle rate for operating cash flows. Investor lens: Business quality via capital allocation and ROIC vs WACC
- Avoid: Applying growth-tech multiples to regulated utilities
- Decision: Primary valuation is DCF/regulated equity — not software multiples
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=5 packs=['COMPANY_EVIDENCE_PACK', 'INDUSTRY_EVIDENCE_PACK', 'GOVERNMENT_EVIDENCE_PACK'] citations=5 gate_fails=[]

**Examiner:** Did not identify steel producers as beneficiaries and auto/capex/infra as cost sufferers. Government pack retrieved but not used in synthesis.

### Q13 — FAIL (2.5/10)

**Question:** GST collections hit a record high for six consecutive months. What conclusions can—and cannot—be drawn from this?

**Candidate summary:** the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Interpret Financial analysis specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Never retrieve five book paragraphs — retrieve this unified object
- Institutional ROIC knowledge: return on invested capital judged versus cost of capital, stability, cash support, and reinvestment runway — synthesized across valuation, accounting, and business-quality traditions.
- Apply the Implied ERP (Monthly from 9-08) framework: map evidence to inputs, then translate outputs into investment implications in AGI's own language.

**IERE:** ranked=4 packs=['COMPANY_EVIDENCE_PACK', 'GOVERNMENT_EVIDENCE_PACK', 'CROSS_DOMAIN_EVIDENCE_PACK'] citations=4 gate_fails=[]

**Examiner:** Failed can/cannot-draw distinction (formalisation vs inflation vs compliance vs base effects). Template noise.

### Q14 — PARTIAL (5.0/10)

**Question:** How would a weakening Indian Rupee affect Infosys, Indigo, Maruti, and Oil Marketing Companies? Explain the mechanisms.

**Candidate summary:** The same macro move rarely affects every sector or market price the same way. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Ad

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring attrition/utilisation
- Decision: Lead with large deal TCV/pipeline and utilisation before multiple expansion stories
- Current PE 14.309564 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 13.831805 sits below trailing PE 14.309564, consistent with expected earnings improvement already partly in the price. PEG around 1.91 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 974.6x a

**IERE:** ranked=4 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=4 gate_fails=[]

**Examiner:** Correct general transmission framing; INFY FX benefit hinted via IT model notes but Indigo/Maruti/OMC mechanisms not explicitly differentiated (fuel USD costs, CKD imports, under-recovery).

### Q15 — FAIL (2.5/10)

**Question:** Inflation rises while GDP growth slows. Which sectors historically outperform in such an environment?

**Candidate summary:** the company continues to show business strength rated C. Framework insufficient: Capital Cycle / Supply Response (Institutional) — missing capex_or_supply_signal, returns_cycle, pricing_power_hint. The main point to watch is execution. Another supporting point is Execution policy: question typed as Macro; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Interpret creative_destruction specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Creative Destruction: The process by which innovation displaces obsolete products, firms, and technologies, raising long-run living standards. Investor lens: Investors care because cash flows, discount rates, or risk premia change
- Inflation: A sustained increase in the general price level, reducing the purchasing power of money. Investor lens: Inflation ↑ → expected policy rates ↑ → discount rate ↑ → DCF values ↓ for long-duration assets
- GDP: The market value of all final goods and services produced within a country in a given period. Investor lens: GDP ↑ → revenue opportunity ↑ → earnings ↑ → equity risk appetite ↑

**IERE:** ranked=5 packs=['COMPANY_EVIDENCE_PACK', 'INDUSTRY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK'] citations=5 gate_fails=[]

**Examiner:** No stagflation sector map (staples, gold, OMCs selectively, quality compounders vs cyclicals).

### Q16 — PARTIAL (5.0/10)

**Question:** Suppose all of the following occur simultaneously: RBI cuts rates; Crude oil falls 20%; UPI transactions reach record highs; GST collections rise; The Government announces a new PLI scheme. Identify the Indian sectors most likely to benefit over the next 12–24 months, and explain your reasoning using evidence from macro, government, alternative data, industry, and company intelligence.

**Candidate summary:** The impact differs across industries and market prices. Transmission depends on business models, funding structures, input costs and what investors are discounting beyond the headline variable. Possible reasons include: (1) Direct demand or cost channel for some industries; (2) Indirect margin or funding-cost channel for others; (3) Second-order effects through inflation, rates or confidence. Additional evidence need

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Peak-cycle multiple on refining earnings
- Decision: Separate upstream/refining/marketing; use mid-cycle assumptions
- Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.

**IERE:** ranked=7 packs=['COMPANY_EVIDENCE_PACK', 'INDUSTRY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK', 'GOVERNMENT_EVIDENCE_PACK', 'CROSS_DOMAIN_EVIDENCE_PACK'] citations=7 gate_fails=[]

**Examiner:** Best IERE multi-domain retrieval of the exam (company/industry/macro/gov/cross). Synthesis stayed generic — did not name winners (rate-sensitive RE/auto/NBFCs, consumption via UPI/GST, PLI beneficiaries, oil-cost beneficiaries) with layered evidence.

### Q17 — FAIL (2.0/10)

**Question:** A company reports excellent quarterly earnings, but its stock falls 8% the next day. List at least ten institutional reasons why this can happen.

**Candidate summary:** the company continues to show business strength rated C. business strength and customer base delivery exceeds the base path and returns expand while the entry multiple stays reasonable. The main point to watch is execution. Another supporting point is Sector demand and operating leverage reinforce compounding.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Firm Value Maximisation: The corporate finance objective of maximising the value of the business (firm) for its owners, subject to governance and stakeholder constraints in practice. Investor lens: Business quality via capital allocation and ROIC vs WACC
- Earnings Quality: The degree to which reported earnings are persistent, cash-backed, and free from aggressive estimates or distortions. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Market context matters because it frames entry timing and risk — it does not replace business or valuation analysis.

**IERE:** ranked=3 packs=['COMPANY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK'] citations=3 gate_fails=[]

**Examiner:** Asked for ≥10 institutional reasons; produced none of: guide-down, quality miss, peak margins, multiple compression, positioning, index flows, peer miss, FX, one-offs, buy-rumour/sell-news, expectation gap. Entity pollution (Adani).

### Q18 — FAIL (2.0/10)

**Question:** Two companies have identical revenue growth and EPS growth, but one trades at twice the valuation multiple. Explain all plausible institutional reasons.

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Interpret bkc_uation_8328ebe2bd specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Revenue Recognition: Rules determining when a sale is recorded as revenue — typically when the good/service is delivered and collectability is reasonably assured. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Economic Growth: The sustained increase in an economy's real output and productive capacity over time. Investor lens: Investors care because cash flows, discount rates, or risk premia change
- Discount Rate: The rate used to convert future cash flows into present value, combining time value and risk compensation. Investor lens: Investors care because cash flows, discount rates, or risk premia change

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Blocked. Missed ROIC, FCF, capital intensity, cyclicality, governance, accounting quality, scarcity, index inclusion, liquidity, optionality.

### Q19 — FAIL (2.5/10)

**Question:** How should AGIB determine whether a company deserves a premium valuation rather than simply identifying that it has one?

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Interpret bkc_and_that_the_market_price_793421e92d specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Dividend Principle: Return cash to owners when the firm lacks enough investments earning above the hurdle rate; choose dividends vs buybacks based on shareholder preferences and valuation. Investor lens: Business quality via capital allocation and ROIC vs WACC
- Restatements: Corrections that revise previously issued financial statements due to error or misapplication of GAAP/IFRS. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Capitalised Expenses: Costs recorded as assets and expensed over time rather than immediately through the income statement (e.g., certain software, R&D adjustments in valuation). Investor lens: Business quality: reliability of the scorecard and capital efficie

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** Blocked. Did not articulate deserved-premium tests (ROIC>WACC persistence, reinvestment runway, moat evidence, earnings quality).

### Q20 — WEAK (3.0/10)

**Question:** What evidence should AGIB gather before recommending that an analyst initiate research coverage on a newly listed Indian company?

**Candidate summary:** the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 7 / 9 → Neutral (Low conviction).
- Interpret bkc_we_told_him_that_what_he_should_care_abo_1549d824f3 specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Operating Cash Flow: Cash generated by core operations after working-capital changes, before investing and financing cash flows. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Interest Coverage: Operating earnings relative to interest expense — a solvency/risk ratio from the statements. Investor lens: Business quality: reliability of the scorecard and capital efficiency

**IERE:** ranked=2 packs=['COMPANY_EVIDENCE_PACK'] citations=2 gate_fails=[]

**Examiner:** No IPO/coverage initiation checklist (DRHP, promoter, related party, peer set, accounting policies, float, lock-in, use of proceeds).

### Q21 — WEAK (3.5/10)

**Question:** Using only institutional documents, explain how you would evaluate whether management's capital allocation policy has improved over the last five years.

**Candidate summary:** Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk 

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring attrition/utilisation
- Decision: Lead with large deal TCV/pipeline and utilisation before multiple expansion stories
- Current PE 14.309564 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 13.831805 sits below trailing PE 14.309564, consistent with expected earnings improvement already partly in the price. PEG around 1.91 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 974.6x a

**IERE:** ranked=5 packs=['COMPANY_EVIDENCE_PACK', 'GOVERNMENT_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=5 gate_fails=[]

**Examiner:** Mentioned capital allocation concept and company documents, but did not walk 5-year document method (buybacks vs dividends vs M&A vs ROCE vs cash conversion from annual notes/CFO commentary). No IDI chunk citations.

### Q22 — FAIL (2.0/10)

**Question:** Which sections of an annual report are most useful for identifying emerging risks before they appear in the financial statements?

**Candidate summary:** the company continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe, growth_or_roe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Interpret Financial analysis specifically for this company using sector economics, financial history and live evidence — not as an isolated concept.
- Institutional ROIC knowledge: return on invested capital judged versus cost of capital, stability, cash support, and reinvestment runway — synthesized across valuation, accounting, and business-quality traditions.
- Apply the Implied ERP- Annual since 1960 framework: map evidence to inputs, then translate outputs into investment implications in AGI's own language.
- A high PE alone does not indicate overvaluation. Evaluate the multiple alongside expected growth, reinvestment needs, return on capital, competitive position and cash generation.

**IERE:** ranked=3 packs=['COMPANY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK'] citations=3 gate_fails=[]

**Examiner:** Did not name MD&A, Risk Factors, Notes (contingencies/leases/related party), Auditor emphasis, Related Party, Contingent liabilities.

### Q23 — FAIL (2.5/10)

**Question:** How would you detect inconsistencies between an investor presentation and the audited annual report?

**Candidate summary:** Infosys continues to show business strength rated C. Framework insufficient: Damodaran Relative Valuation (Damodaran) — missing peer_pe_or_index_pe. The main point to watch is execution. Another supporting point is Execution policy: question typed as Company Analysis; frameworks must run or report gaps.

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Free Cash Flow: Cash available after funding operations and necessary reinvestment; FCFF is before debt payments, FCFE is after. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring attrition/utilisation
- Decision: Lead with large deal TCV/pipeline and utilisation before multiple expansion stories
- Current PE 14.309564 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 13.831805 sits below trailing PE 14.309564, consistent with expected earnings improvement already partly in the price. PEG around 1.91 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 974.6x a

**IERE:** ranked=5 packs=['COMPANY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK'] citations=5 gate_fails=[]

**Examiner:** Did not describe cross-check protocol (KPI definitions, adjusted EBITDA bridges, segment splits, guidance vs audited notes). Misrouted to company analysis on INFY.

### Q24 — PARTIAL- (4.0/10)

**Question:** Replay Infosys as of 31 March 2020. Describe only the evidence that would have been available on that date. Explain how AGIB prevents future information leakage.

**Candidate summary:** Both signals can be real; the more important one is usually the measure of quality, sustainability or risk — not the measure of scale alone. Headline growth or size can improve while a quality ratio, margin, mix or risk indicator weakens. That tension means the business may be getting larger without getting healthier. Other possible explanations include: (1) Mix shifted toward lower-quality activity; (2) Costs, risk 

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Operating Cash Flow: Cash generated by core operations after working-capital changes, before investing and financing cash flows. Investor lens: Business quality: reliability of the scorecard and capital efficiency
- Avoid: Ignoring attrition/utilisation
- Decision: Lead with large deal TCV/pipeline and utilisation before multiple expansion stories
- Current PE 14.309564 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 13.831805 sits below trailing PE 14.309564, consistent with expected earnings improvement already partly in the price. PEG around 1.91 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 974.6x a

**Replay:** as_of=2020-03-31 ok=True leakage=False ranked=0

**Examiner:** Replay API correctly reported future_leakage=False and ranked_count=0 for as_of 2020-03-31 — PIT gate works. But Ask answer used CURRENT Infosys price/PE (2026) — severe lookahead contamination in the user-facing answer path. Candidate fails the spirit of historical replay even though IERE replay filter holds.

### Q25 — PARTIAL (5.5/10)

**Question:** Imagine you are presenting Reliance Industries to an Investment Committee. Construct the institutional evidence package you would prepare before anyone begins valuation. Do not value the company. List every evidence domain, document, macro factor, industry consideration, government policy, alternative dataset, historical context, and risk assessment that should be assembled first.

**Candidate summary:** Valuation question blocked from unsupported narrative: required frameworks lack evidence (historical/relative multiples).

**Key why-bullets:**
- Committee vote 8 / 9 → Neutral (Low conviction).
- Capital Allocation: Management's choices on deploying and returning capital across organic reinvestment, acquisitions, buybacks, dividends, debt repayment, and capital raising. Investor lens: Business quality via capital allocation and ROIC vs WACC
- Avoid: Single-multiple on blended conglomerate earnings
- Decision: Value segments with their own sector frameworks then apply holding discount
- Current PE 22.978067 is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns. Forward PE 17.725508 sits below trailing PE 22.978067, consistent with expected earnings improvement already partly in the price. PEG around 0.82 helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict. EV/EBITDA around 11.4x ad

**IERE:** ranked=9 packs=['COMPANY_EVIDENCE_PACK', 'INDUSTRY_EVIDENCE_PACK', 'MACRO_EVIDENCE_PACK', 'GOVERNMENT_EVIDENCE_PACK', 'HISTORICAL_EVIDENCE_PACK', 'CROSS_DOMAIN_EVIDENCE_PACK'] citations=9 gate_fails=[]

**Examiner:** IERE assembled the broadest pack set (company/industry/macro/gov/historical/cross) and why-bullets correctly warn against single-multiple on conglomerates and urge segment frameworks + holding discount. Summary blocked. Did not enumerate full IC evidence package (segments O2C/Retail/Jio/New Energy, govt energy policy, crude, circle data, related party, promoter pledge, historical capital cycle).

## Capability scorecard (exam objective)

| Capability | Result | Evidence |
|------------|--------|----------|
| Company Intelligence | Partial | Q1–Q3 heuristics present; Q4 moat weak; Titan sector wrong |
| Industry Intelligence | Fail | Q6–Q10 mostly blocked/template |
| Government Intelligence | Partial retrieval / weak use | Packs on Q12/Q13/Q16; synthesis thin |
| Macro Intelligence | Partial | Transmission framing OK; wrong impulse on Q11 |
| Corporate Events | Not demonstrated | No event-chain answers surfaced |
| Historical Replay | Gate pass / Answer fail | IERE PIT OK; Ask used current prices on Q24 |
| Institutional Documents | Weak | Documents named; no section/page capital-allocation method |
| Evidence Retrieval (IERE) | Pass (infra) | Deterministic packs+citations across domains |
| Knowledge Factory | Partial | Soft objects present; depth/freshness uneven |
| Reasoning | Fail for CIO conceptual | Misroute + blocked + template fallback |
| Cross-domain synthesis | Partial | Q16 retrieval excellent; narrative generic |

## Remediation priority (examiner recommendations)

1. **Intent routing for conceptual/process questions** — do not force valuation contracts on “explain why / list evidence / how would you assess” prompts.
2. **Wire IERE Evidence Packs into the narrative assembly** — Why-bullets should cite ranked pack items, not only committee PE scaffolding.
3. **Ask-path historical replay** — when `as_of` present, freeze market/fundamentals to PIT objects (Q24 critical fail otherwise).
4. **Fix editorial provider credentials** — Gemini key invalid collapsed many answers to template fallback.
5. **Entity hygiene** — never attach Adani/INFY docs to entity-less conceptual questions.
6. **Sector knowledge corrections** — Titan ≠ mining; build industry KPI matrices for FMCG/IT/Banks/Cement/Hospitals.
7. **Populate historical KF objects with real `available_from`** — replay returned empty for 2020-03-31.

## Bottom line

AGIB is a promising **institutional evidence operating system**. On this CIO exam it proves retrieval, governance restraint, and multi-domain pack assembly. It does **not** yet prove senior-analyst reasoning under cross-domain questions. Treat Track 5 IERE as foundation — the next gap is **conceptual answer assembly on top of ranked evidence**, not another intelligence domain.
