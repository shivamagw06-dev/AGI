# AGI Phase 0: Freeze and Production Baseline

**Started:** 14 August 2026  
**Status:** In progress until the backup acceptance evidence is recorded  
**Purpose:** Establish a recoverable, measurable baseline before operational repairs.

## Freeze

Until Phase 0 is accepted, do not add new intelligence engines, strategy families,
product pages, or top-level architecture. Permitted changes are limited to reliability,
data integrity, coverage, observability, validation, security, performance, and bug fixes.

The freeze does not stop current market collection or research production. It prevents
new surface area from obscuring operational failures.

## Baseline Artifacts

- `production-baseline-2026-08-14.json`: redacted live API and inventory snapshot.
- `runtime-ownership.md`: authoritative process and scheduler ownership map.
- `acceptance-checklist.md`: backup and Phase 0 completion evidence.
- `scripts/capture-phase0-baseline.py`: repeatable baseline capture utility.

Regenerate the snapshot from the repository root:

```bash
python3 scripts/capture-phase0-baseline.py \
  --output docs/operations/phase0/production-baseline-$(date +%F).json
```

The utility only calls read-only public health endpoints and recursively redacts fields
whose names indicate tokens, secrets, passwords, authorization, or API keys.

## Current Baseline Conclusions

Two checkpoints were observed on 14 August 2026:

### Last verified readable state (approximately 08:33 UTC)

1. The Intelligence Engine HTTP service responded successfully.
2. The durable warehouse contained 2,438,002 rows across 57 tables, 43 populated.
3. KIP contained 1,765 documents, 31,038 chunks, 3,055 graph nodes, 12,384 graph
   edges, 1,236 predictions, and 987 articles.
4. Forecast coverage was 103 complete of a 2,710-company universe.
5. The continuous gather heartbeat was stale and continuous collection was not proven live.
6. The canonical E01-E14/L4 strategy chain was loaded but had no production runs.
7. Backtesting, continuous evaluation, and promotion evidence stores were empty.

### Captured baseline state (09:12 UTC)

All 25 read-only production probes timed out, including `/v1/health`. The generated
JSON retains every failed probe, URL, elapsed time, and error. This is accepted as a
real production availability finding, not replaced with synthetic healthy data.

The transition from readable to unavailable within the same hour indicates resource
starvation or a long-running startup/background workload. Phase 1 must reproduce and
eliminate that failure before restoring other intelligence workloads.

These are baseline facts, not Phase 1 repairs. Phase 1 begins only after the backup and
acceptance checklist is complete.
