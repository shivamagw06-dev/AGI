# AGI Institutional Stress Test #1 (IST-01)

## Case

> **Should an Indian institutional investor have bought Kotak Mahindra Bank immediately after the RBI restrictions (April 2024), or waited?**

Deliberately difficult — **no obvious answer**. A good system must not collapse to Buy / Don't Buy.

---

## Design rule

**No individual module can pass this test on its own.**

The case forces AGI to orchestrate the full stack. Missing any required module → automatic orchestration failure (`MISSING_REQUIRED_MODULES` / `SINGLE_MODULE_RESPONSE`).

---

## Required modules

| Layer | Contribution |
| --- | --- |
| FSE | Financial statements before/after RBI action |
| FIL | Regulatory filings and disclosures |
| FIRE-01 | What changed financially? |
| FIRE-02 | Which drivers changed? |
| FIRE-03 | Management explanations |
| FIRE-04 | Management vs financial evidence |
| FIRE-05 | Execution vs promised remediation |
| FIRE-06 | Business quality trajectory |
| CIO-01 | Kotak vs HDFC / ICICI / Axis |
| WO-01 | Monitoring timeline |
| Ask AGI | Final institutional answer |

Optional: PO-01, CW-01, IO-01, PEB-01, Office SDK.

---

## Required questions (1–12)

1. What actually happened?  
2. What caused it?  
3. Temporary or structural?  
4. Did management diagnose correctly?  
5. Did execution match promises?  
6. How did financial quality evolve?  
7. How did competitors perform?  
8. Relative business quality gain/loss?  
9. Evidence against the thesis  
10. Evidence supporting the thesis  
11. Missing evidence  
12. **Final Institutional View** (not BUY/SELL):

```
Investment Thesis
Evidence Supporting
Evidence Against
Remaining Unknowns
Confidence
Evidence References
Questions requiring monitoring
```

---

## Rubric (100)

| Area | Weight |
| --- | ---: |
| Financial reasoning | 15 |
| Business reasoning | 15 |
| Evidence consistency | 10 |
| Management execution | 10 |
| Comparative analysis | 10 |
| Historical timeline | 10 |
| Missing evidence identification | 10 |
| Confidence calibration | 10 |
| Source traceability | 10 |

Pass threshold: **70** — and orchestration gate must pass.

---

## Automatic failures

- Buy/Sell without evidence  
- Ignores contradictory evidence  
- Hallucinated facts  
- Unattributed external info  
- Lost provenance  
- Mixes opinion with fact  
- No unknowns identified  
- **Single-module response**  
- Missing required modules  

---

## Package

- `intelligence-engine/institutional_stress_tests/`
- CLI: `python -m institutional_stress_tests --run`
- Negative: `python -m institutional_stress_tests --single-module FIRE-06` (must FAIL)
- API: `GET /v1/institutional-stress-tests/health`, `POST /v1/institutional-stress-tests/run`
