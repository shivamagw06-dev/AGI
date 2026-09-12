# Management Intelligence Engine (MII) V1

**Architecture status:** v1.0.1 LOCKED  
**Primary question:** Can this management team be trusted to compound shareholder value?

Soft layer. No engine / UI / provider / FIL / FDI / EIL / PIL / Company Analysis / IC / CIO / RW / ACS / IRS redesign.

## Position

Official Filings → FIL → FDI → **MII** → EIL → PIL → Analysts → IC → CIO → RW → ACS → IRS → Production

## Rule

Not sentiment. Not “what did management say?”  
Evidence-backed longitudinal assessment of credibility, execution, capital allocation, governance and communication.

## Management DNA

Evidence-driven operating style (evolves over time):

Capital Allocator · Growth Builder · Operator · Turnaround Specialist · Financial Engineer · Founder-led Visionary · Professional Steward · Empire Builder · Value Creator · Value Destroyer

## Confidence

Credibility 35% + Execution 25% + Capital Allocation 20% + Governance 10% + Communication 10%

## Flags

`management_intelligence` / `MANAGEMENT_INTELLIGENCE`  
Sub: `mii_credibility`, `mii_guidance`, `mii_execution`, `mii_capital_allocation`, `mii_governance`, `mii_communication`, `mii_incentives`, `mii_succession`

## APIs

- `GET /v1/management-intelligence/company/{ticker}`
- `GET /v1/management-intelligence/history/{ticker}`
- `GET /v1/management-intelligence/guidance/{ticker}`
- `POST /v1/management-intelligence/analyse`
- `GET /admin/management-intelligence`
