# Phase 3 — Institutional Knowledge Intelligence (IKI)

> Transform financial knowledge from stored frameworks into executable institutional judgement.

**Not** more knowledge ingestion. Soft-wire under `institutional_reasoning/iki/`.

## Pipeline

```text
Question
  → Institutional Planner
  → Applicable Frameworks (scored)
  → Cross-framework Reasoning
  → Conflict Resolution
  → Decision Policy
  → Committee
  → Answer
```

## Modules

| Module | Path |
| --- | --- |
| Framework Registry | `registry.py` |
| Applicability Engine | `applicability.py` |
| Confidence Calibration | `confidence.py` (IES-seeded; live later) |
| Mental Models | `mental_models.py` (Buffett / Graham / Damodaran) |
| Decision Policies | `decision_policies.py` |
| IKG Relations | `graph_relations.py` (+ soft EDGE_TYPES) |
| Institutional Planner | `planner.py` → wired in `execution_governance.py` |
| Debate | `debate.py` |
| Knowledge Compiler V2 | `compiler_v2.py` |
| Judgement Suite | `judgement_suite.py` |

## Acceptance

| Question | Expected |
| --- | --- |
| Should DCF be used for HDFC Bank? | Applicability **No**; Financial Institution; Alternative **Residual Income** |
| Value Zomato | Relative preferred; Graham/Buffett **reject**; growth/relative dominates |
| Compare Buffett and Damodaran on Zomato | Conflict **explained** with evidence shown |

## Run

```bash
cd intelligence-engine
python3 -c "from institutional_reasoning.iki.production import quality_gates; print(quality_gates())"
python3 -m pytest tests/test_phase3_iki.py -q
```

## Definition of Done

AGIB selects frameworks by applicability, explains rejections, represents author philosophies as executable policies, detects/explains conflicts, and passes the Institutional Judgement Suite — not a bag of calculators.
