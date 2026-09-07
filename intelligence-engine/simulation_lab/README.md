# Institutional Simulation & Strategy Lab (SSL) V1

**Primary question:** What happens if this decision is taken?

Soft institutional experimentation layer. No redesign of FIL/FDI/MII/ACI/EIL/PIL/CIG/IKG/FIE/ILM, analysts, committee, CIO, research writer, ACS, IRS, providers, or UI engines.

## Flag

`SIMULATION_LAB=true` (`simulation_lab` in settings)

## API

- `GET /v1/simulation/health`
- `GET /v1/simulation/scenarios`
- `POST /v1/simulation/run`
- `POST /v1/simulation/portfolio`
- `GET /v1/simulation/history`
- `GET /v1/simulation/quality-gates`
- `GET /v1/admin/simulation-lab`

## Rule

Simulations are reproducible, assumptions are explicit, outcomes are probabilistic distributions with stress, replay and opportunity-cost analysis — never unsupported deterministic trade instructions.
