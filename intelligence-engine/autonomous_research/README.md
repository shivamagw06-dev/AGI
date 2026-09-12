# P6 — Autonomous Research Office (ARO)

Continuously plans, drafts, and organises institutional research using existing AGIB intelligence and the Investment Operations Layer.

**Does not replace analysts. Does not make investment decisions. No BUY/SELL.**

Governed by Constitution, CID, Decision Engine, and Committee Certification.

## Capabilities

Research Planner · Research Generator · Coverage Manager · Watchlist Manager · Theme Intelligence · Evidence Monitor · Portfolio Review · Publication Pipeline · Institutional QA · Learning Feedback

## APIs

```
GET /v1/autonomous-research/status
GET /v1/autonomous-research/planner
GET /v1/autonomous-research/tasks
GET /v1/autonomous-research/watchlists
GET /v1/autonomous-research/themes
GET /v1/autonomous-research/coverage
GET /v1/autonomous-research/research/{ticker}
GET /v1/autonomous-research/publications
GET /v1/autonomous-research/qa
GET /v1/autonomous-research/learning
```

## CLI

```bash
python -m autonomous_research --status
python -m autonomous_research --ic10
python -m autonomous_research TCS
```
