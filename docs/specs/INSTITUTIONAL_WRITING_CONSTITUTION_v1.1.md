# Institutional Writing Constitution v1.1 — Narrative Update

**Status:** Production  
**Layer:** Institutional Research Engine (IRE)

## v1.1 Changes (investor-facing)

### 1. Narrative hierarchy (replaces "Investment Meaning")

```text
Executive Summary
↓
What Matters Most          (default template)
↓
The Investment Debate      (new — institutional analyst voice)
↓
Supporting Evidence
↓
Key Uncertainties
↓
Research Conclusion
↓
Questions Before You Decide
```

### 2. Varied evidence phrasing

No longer repeats "Evidence suggests..." on every line. Rotates through institutional templates:

- Current evidence indicates...
- Historical evidence shows...
- Recent developments suggest...
- etc.

### 3. Response planning pipeline

```text
Research → Response Planning → Writing
```

`response_planner.py` decides template, top 3 insights, sections to expand, and detail level before writing.

### 4. Intent-aware templates (10 patterns, 5 shipped)

| Template | Use case |
|----------|----------|
| investment_assessment | Should I invest? |
| earnings_review | What changed after earnings? |
| valuation | Premium/discount/fair value |
| peer_comparison | Compare X vs Y |
| risk_review | Key risks, invalidation |
| narrative_default | General research |

### 5. Institutional Readability Score

Investor-facing metric with: clarity, institutional tone, prioritization, evidence integration, narrative flow, investor usefulness.

Forward test: *Would a portfolio manager forward this to the investment committee without editing?*

See full spec: `docs/specs/INSTITUTIONAL_WRITING_CONSTITUTION_SPEC_v1.0.md` (v1.0 base; v1.1 extends in code).
