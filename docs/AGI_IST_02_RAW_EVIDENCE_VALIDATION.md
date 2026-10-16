# AGI Institutional Stress Test #2 (IST-02)

## Raw Evidence Institutional Research Validation

| Field | Value |
| --- | --- |
| **Status** | Production — Validation |
| **Workstream** | IST-02 |
| **Depends on** | IST-01 (orchestration) COMPLETE |
| **Package** | `intelligence-engine/institutional_stress_tests/` |
| **Pass** | ≥ 85 / 100 |

> IST-01 proved AGI can orchestrate.  
> IST-02 proves AGI can reason from **raw evidence**.

---

## Mission

Begin with only raw company evidence and independently reconstruct a balanced, evidence-backed institutional research view.

**No fixture answers. No pre-written conclusions.**

---

## Allowed inputs

Financial statements · Annual / quarterly reports · Earnings call transcripts · Investor presentations · Regulatory filings · Exchange announcements · Corporate actions · Historical prices · Peer financials

## Allowed modules (reuse only)

FSE · FIL · FIRE-01…06 · IO · CIO · CW · WO · Office SDK · PEB

No new intelligence engines.

---

## Process

1. Load raw evidence  
2. Build evidence graph  
3. Run existing FIRE modules (soft façades + corpus-grounded extraction fallback)  
4. Assemble institutional report  
5. Evaluate report quality  

---

## Report structure

Executive Summary · Historical Timeline · What Happened · Business Context · Financial Analysis · Business Quality · Management Assessment · Evidence Supporting · Evidence Contradicting · Alternative Interpretations · Peer Comparison · Outstanding Unknowns · Monitoring Framework · Confidence Discussion · Evidence Appendix · Counterfactual Analysis

---

## Mandatory

- Every conclusion cites evidence (id, source, date, type, confidence contribution)  
- Every interpretation lists supporting / contradictory / unknown evidence  
- Confidence explains increasing drivers, reducing drivers, missing evidence, and why it cannot be higher  
- Counterfactual: *What evidence would change this conclusion?*  
- Monitoring: Next Quarter · Six Month · Twelve Month (each linked to evidence/metrics)  

---

## Failure codes

`UNSUPPORTED_CONCLUSION` · `NO_COUNTER_EVIDENCE` · `NO_UNKNOWNS` · `NO_MONITORING_FRAMEWORK` · `PROVENANCE_MISSING` · `CONFIDENCE_UNJUSTIFIED` · `HALLUCINATED_FACT` · `PEER_ANALYSIS_MISSING` · `EVIDENCE_CHAIN_BROKEN` · `FIXTURE_ANSWER_USED` · `RAW_CORPUS_EMPTY`

---

## CLI

```bash
python -m institutional_stress_tests --case IST-02 --run --show-report
python -m institutional_stress_tests --case IST-02 --inject-fixture-answers   # must FAIL
```

## API

`POST /v1/institutional-stress-tests/run-raw`  
`POST /v1/institutional-stress-tests/run` with `{"case_id":"IST-02"}`
