# Institutional Probability & Confidence Intelligence (IPCI) — Sprint 9.4

Assigns evidence-based **probabilities** and independent **confidence** to Bull / Base / Bear scenarios.

## Primary question

**How likely is each scenario, and how confident are we?**

## Rules

- Probabilities always sum to 100%  
- Confidence ≠ probability  
- No guessing, no trading recommendations  
- Missing evidence is explicit  

## APIs

- `GET /v1/probability/company/{ticker}`
- `GET /v1/probability/sector/{sector}`
- `GET /v1/confidence/company/{ticker}`
- `GET /v1/forecast/assessment/{ticker}`

## Tests

```bash
cd intelligence-engine
python -m pytest institutional_probability_confidence/tests -q
```
