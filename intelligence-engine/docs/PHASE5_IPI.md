# Phase 5 — Institutional Portfolio Intelligence (IPI)

> Transform institutional research into portfolio decisions that are evidence-backed, risk-aware, and policy-governed.

```text
Research Package → Portfolio Evidence → Risk → Exposure → Scenario
  → Policy → Position Sizing → Portfolio Committee → PDG → Decision
```

Soft-wire under `institutional_reasoning/ipi/`. Architecture v1.0.1 LOCKED.

Research tells you **what is true**. Portfolio Intelligence tells you **what to do**.

## Modules

| Module | Path | What |
| --- | --- | --- |
| Portfolio Evidence | `evidence.py` | Research → Portfolio Evidence Pack (no raw fetch downstream) |
| Position Sizing | `sizing.py` | Weights, not Buy/Sell |
| Risk Intelligence | `risk.py` | Vol, beta, VaR, ES, risk contribution, risk budget |
| Exposure Intelligence | `exposure.py` | Sector/country/factor/theme limits |
| Scenario Intelligence | `scenarios.py` | Bull/base/bear/stress + named shocks |
| Portfolio Policy | `policy.py` | Executable mandate constraints |
| Portfolio Committee | `committee.py` | Increase/Reduce/Hold/Exit/Watch/Replace/Hedge |
| Downside Intelligence | `downside.py` | Missing downside → **Withhold** |
| Portfolio Memory | `memory.py` | Snapshots only — no learning |
| Portfolio Decision Graph | `pdg.py` | Traceability linked to research DJGs |
| Institutional Portfolio Suite | `portfolio_suite.py` | ≥95% with 0 unsupported recommendations |

## Attach point

`execution_governance.govern_answer`:

1. After Phase 2 IE pack → inject `packs["institutional_portfolio"]` (contract aliases).
2. After DJG attach → run `decide_portfolio` for portfolio / investment_decision paths → `record["ipi"]` + `portfolio_decision_graph`.

Phases 1–4, DJG, KIP, and IKG are not redesigned.

## Run

```bash
cd intelligence-engine
python3 -c "from institutional_reasoning.ipi.production import quality_gates; print(quality_gates())"
python3 -m pytest tests/test_phase5_ipi.py -q
```

## Phase 5 exit gate

| Criterion | Status |
| --- | --- |
| Research package → Portfolio Evidence Pack | ✅ |
| Evidence-backed position sizing | ✅ |
| Risk contribution + downside + exposure | ✅ |
| Executable portfolio policies | ✅ |
| Withhold when portfolio evidence missing | ✅ |
| PDG linked to research DJGs | ✅ |
| Institutional Portfolio Suite ≥95%, 0 unsupported | ✅ |

## Non-goals

No Phase 1–4 redesign, no DJG replacement, no new top-level engines, no full-covariance portfolio optimiser.
