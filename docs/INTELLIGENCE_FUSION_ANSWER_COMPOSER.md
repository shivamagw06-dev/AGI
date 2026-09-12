# Intelligence Fusion & Answer Composer (IFAC) v1.0 — Phase 9.1

IFAC is **not** another intelligence engine. It is the orchestration layer that
sits **above** warehouse-backed engines and composes institutional answers.

```text
User → /api/ui/search → UKO → KUL → Engine Router
  → Warehouse / UVE / HVIE / VPAE / VARIE / RIE / FIE / MIE / MI / Hedge Fund Lab
  → IFAC
  → Institutional Answer
```

## Design principles

- Never call vendors
- Never recalculate intelligence or invent facts
- Never override engine outputs
- Never let CapIQ / external consensus become the headline
- Always preserve observed / derived / inferred explainability
- Always cite engine provenance and expose confidence
- Always explain missing data (never "No historical conclusion.")
- Always surface conflicts instead of suppressing them

## Responsibilities

Evidence fusion · conflict detection · confidence aggregation · executive summary ·
institutional templates · engine prioritisation · supporting evidence ordering

## Engine priority (examples)

| Family | Primary | Secondary |
| --- | --- | --- |
| Company / IC | RIE | FIE |
| Valuation | UVE | HVIE |
| Historical | HVIE | VARIE |
| Forecast | FIE | RIE |
| Macro | MIE | Market Intelligence |
| Comparison | RIE | UVE / HVIE / VARIE / FIE |
| Hedge fund screen | Hedge Fund Lab | Factors / RIE / FIE |
| Attribution / premium | VARIE | HVIE |

Consensus is reference-only and appears near the end of company templates.

## Templates

`company`, `valuation`, `historical`, `forecast`, `macro`, `market`,
`comparison`, `screen`, `attribution`

## APIs

- `POST /v1/ifac/compose`
- `GET /v1/ifac/templates`
- `GET /v1/ifac/routing`
- `GET /v1/ifac/confidence`
- `GET /v1/ifac/debug`
- `GET /v1/ifac/provenance`
- `GET /v1/ifac/dashboard`
- Admin: `/admin/ifac`

## Ask wiring

`universal_knowledge.gather` runs KUL fusion, then IFAC. Ask payloads include
`sections`, `explainability`, `conflicts`, and `ifac` (template, primary engine,
provenance, DQIV, debug).

## DQIV reject conditions

Primary engine missing · unsupported evidence · confidence unavailable ·
unexplained engine conflict · consensus promoted above institutional intelligence ·
incomplete template · missing provenance
