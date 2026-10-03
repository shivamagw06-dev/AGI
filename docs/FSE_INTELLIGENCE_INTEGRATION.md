# FSE → Intelligence Soft-Wire

## Intent

Merge the Financial Statements Engine stack (including FSE-02.3 Source Registry and FSE-FDO Phase 1) into AGIB **intelligence surfaces** without redesigning engines.

Success metrics remain **coverage, freshness, throughput, reliability**.

## Soft-wired surfaces

| Surface | Path |
| --- | --- |
| Mission Control aggregate | `mission_control/aggregate.py` → `financial_data_operations`, `financial_statements_engine`, `fse_source_coverage` |
| Agent map | `mission_control/agent_map.py` → FSE + FDO ops agents |
| Node proxies | `server/routes/intelligence.js` → `/api/intelligence/financial-statements/*` |
| Frontend clients | `src/lib/intelligenceApi.js` |
| Admin page | `/admin/financial-statements` |
| Mission Control UI | FDO board section |

## Non-goals

- No Decision Engine / BUY-SELL changes
- No consumer migration off HD dual-write
- No redesign of collectors, parser, VFQE, warehouse, DME, orchestrator, verification

## Upstream packages included

- FSE-01 … FSE-07, ECD, FSE-00 (+ autostart/DLQ), FSE-02.1, FSE-02.2 (already on `main`)
- **FSE-02.3** Official Source Registry (merged into this integrate branch)
- **FSE-FDO Phase 1** (already on `main` via #341)
