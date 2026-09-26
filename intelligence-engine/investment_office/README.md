# Investment Office V1

**Architecture status:** v1.0.1 LOCKED  
**Role:** Executive operating cockpit above AGI platforms.  
**Not:** intelligence engine · recommendation engine · portfolio manager · redesign

## Soft path

… → Company Analysis → Company Monitor → IRP → **Investment Office** → Ask AGI / Home

## Flags

`INVESTMENT_OFFICE`, `IO_MORNING_BRIEF`, `IO_ANALYST_QUEUE`, `IO_RESEARCH_QUEUE`, `IO_COVERAGE`, `IO_RISK_CENTER`, `IO_EXECUTIVE_COPILOT`

## Admin

`/admin/investment-office`

## Home

`/` uses the existing dark Investment Office shell, fed by `/v1/investment-office/dashboard` (+ `/v1/ui/home`).
