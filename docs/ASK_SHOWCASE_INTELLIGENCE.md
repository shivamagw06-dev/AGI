# AGIB Ask — Showcase Intelligence Path

Ask answers the institutional showcase questions by routing through **UKO → KUL**
to warehouse-backed engines. No vendor calls at Ask time.

## Question families → engines

| Family | Lead engines |
|---|---|
| Company / IC intelligence | RIE → FIE → MIE → UVE → HVIE → VARIE → VPAE → Market Intel → Warehouse |
| Valuation | UVE → HVIE → VARIE → VPAE |
| Forecast | FIE → MIE → RIE → HVIE |
| Historical valuation | HVIE → VARIE → UVE |
| Hedge fund screen | Hedge Fund Lab → FIE → RIE → UVE → VARIE |
| Macro | MIE → Market Intel → FIE → RIE |
| Comparison | RIE → UVE → HVIE → VARIE → FIE |
| Market summary | Market Intel → MIE → HVIE → Warehouse |
| Premium attribution | VARIE → HVIE → VPAE → UVE → RIE → FIE → MIE |

## Hard short-circuit providers

Warehouse engines (RIE/FIE/MIE/UVE/HVIE/VARIE/VPAE/Market Intelligence /
`institutional_warehouse` / `historical_intelligence`) are allowed to
short-circuit Ask when they return hard evidence.

## Nightly dependency

Answers quality tracks the warehouse refresh (~18:45 IST), including
`hedge_fund_factors` and the Hedge Fund Lab snapshot stage.
