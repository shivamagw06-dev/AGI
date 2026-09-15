# Sprint 8.1 — Historical Acquisition Platform (HAP)

## Mission

Start **Phase 8 – Historical Intelligence Platform (HIP)** by building bulk historical ingestion with an explicit coverage policy.

```text
Phase 6 = Live knowledge
Phase 8 = Historical knowledge
```

## Roadmap context

| Sprint | Module |
|---|---|
| **8.1 HAP** | Bulk historical ingestion ← this sprint |
| 8.2 HKO | Historical Knowledge Objects (richer institutional shaping) |
| 8.3 | Timeline Intelligence |
| 8.4 | Historical Relationship Engine |
| 8.5 | Pattern & Cycle Intelligence |

## What shipped

- Standalone `historical-platform/` service (port **8092**)
- Historical coverage policy (measurable completeness)
- Collectors: Yahoo / NSE / BSE / Company IR (fixture + optional live)
- Append-only raw archive + typed historical tables
- Validation, normalization, entity resolution, versioned HKO builder
- Retrieval APIs with `providers_queried: []` guarantee
- Success path: Infosys revenue FY2015–FY2025 + valuation cycles from store only

## Contracts

- `historical-platform/docs/HAP_PLATFORM_CONTRACT.md`
- `historical-platform/docs/HISTORICAL_COVERAGE_POLICY.md`

## Verification

```bash
cd historical-platform && pytest -q
```

## Next

Sprint **8.2 — Historical Knowledge Objects (HKO)** — deepen institutional historical object model (timelines-ready sections, richer fiscal period ontology).
