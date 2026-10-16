# Sprint 6.3 — Institutional Learning Engine (ILE)

## Goal

Don't just store new data. Understand what changed, why it matters, what it affects, and how AGI's understanding of companies, sectors and markets evolves.

## Contract

Authoritative: [`knowledge-platform/docs/ILE_PLATFORM_CONTRACT.md`](../knowledge-platform/docs/ILE_PLATFORM_CONTRACT.md)

**Materiality Policy first** — PE 24.10→24.12 is ignored; revenue growth 18%→26% learns with a score.

## Pipeline

```text
New KO → Previous Version → Compare → Materiality Engine
→ Impact / Relationships → Learning Event Builder
→ Sector Learning / Market Learning / Contradiction Engine
→ Institutional Memory → Learning Timeline → Publish
```

## New collections

`sector_learning` · `market_learning` · `relationship_changes` · `knowledge_conflicts` · `learning_timeline` · `institutional_memory`

## Success path

Infosys earnings update (no user ask) → revenue accelerated, margins/cash/debt assessed, learning events scored, memory narrative written, timeline updated, sector/relationship impact recorded, publication envelope marked ready for Evidence Graph / IE.

## Verification

```bash
cd knowledge-platform && pytest -q
```

## Non-goals

New collectors · LLM prose · Evidence Graph service (6.4) · Ops dashboards (6.5)
