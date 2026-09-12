# Reliance Note — Buy-Side PM Review

**Reviewer persona:** Buy-side portfolio manager  
**Artifact:** `RELIANCE_INVESTMENT_NOTE.md`  
**As of:** 2026-07-30

---

## Overall score

| Area | Score |
| --- | ---: |
| Business understanding | **9/10** |
| Structure | **10/10** |
| Institutional tone | **9/10** |
| Investment reasoning | **6/10** |
| Financial analysis | **3/10** |
| Valuation | **3/10** |
| Evidence | **2/10** |
| Actionability | **5/10** |

**Overall: 67/100**

Not publication-ready. Very good institutional scaffold.

**PM one-liner:** *"Good first draft. Don't publish it yet."*

---

## What is excellent

1. **Institutional writing** — reads like an IC memo, not ChatGPT.
2. **Correct uncertainty** — “No fabricated EPS, GRM, or ARPU” builds trust.
3. **Structure** — Exec → Business → Financials → Valuation → Catalysts → Risks → Scenarios → Conclusion.
4. **claim_safe honesty** — refusing to overstate confidence is platform-correct.

---

## Where it fails

1. **No numbers** — O2C / Retail / Jio / Capex discussed without revenue mix, EBITDA, ROCE, debt, FCF, margins.
2. **Valuation almost empty** — “Neutral” without EV/EBITDA, P/E, SOTP, FCF yield, peers, upside/downside.
3. **Missing evidence** — 0 primary filings; every material claim needs AR / results / presentation / exchange filing.
4. **Contradiction** — SELL → Neutral → Monitor → “Own only if…” must be rejected before the note reaches the analyst.

---

## Missing for an 85+/100 report

1. Investment Thesis (3–5 evidence-backed bullets)  
2. Key Financial Metrics (5-year + TTM)  
3. Segment Economics (O2C, Retail, Jio, New Energy)  
4. Valuation (SOTP + peers + sensitivity)  
5. Decision Triggers (upgrade / downgrade)  
6. Evidence Links (primary filings per material claim)  
7. Contradiction Check (single recommendation only)  

Also: scenario **probabilities**; explicit BUY/SELL because bullets.

---

## Product implication

Aligns with IB-01 / productivity findings:

* AGIB accelerates structured institutional notes.
* Analyst still must validate facts, attach evidence, value, remove contradictions, finalize the view.

**Priority for research quality (not new engines):**

1. Evidence attachment gate  
2. Contradiction rejection  
3. Financial + valuation density requirements  
4. Decision-trigger template  
5. Publication blocked until gates pass  

Encoded in: `institutional_grade_benchmark/publication_gates.py`
