# P2.6 — Live Market Context

**Milestone:** Phase 2.1 Market & Ownership Intelligence · Sprint 1  
**Baseline:** AGIB Institutional Baseline v1.0 (FROZEN) — not modified

## Goal

Make every recommendation market-aware without changing research governance.

## Deliverables

- Live quote provider abstraction (Groww → Yahoo, fail-closed)
- Price freshness
- Liquidity
- Relative strength
- Distance to intrinsic value (hook for P2.2)
- Market context API

## Implementation PR checklist

1. What intelligence did we add?
2. What measurable metric improved?
3. What metric stayed unchanged?
4. Did IAT still pass?
5. Did UNKNOWN drift remain zero?

```bash
PYTHONPATH=. python -m live_market_context --ticker ETERNAL --json
```
