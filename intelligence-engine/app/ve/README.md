# AGI Valuation Engine (VE) v1.0

Institutional valuation & intrinsic value platform.

## Mission

> What is this business worth?

## Position

```text
EVE → IIE → FLE → MEE → VE → CAE → IRP → Ask AGI
```

Architecture **v1.0.1 LOCKED**. Additive only — consumes structured intel from EVE/IIE/FLE/MEE; never raw documents; never executes trades.

## Models

DCF (FCFF/FCFE) · Relative (P/E, EV/EBITDA, EV/Sales, P/B, PEG, P/CF) · SOTP · DDM · Residual Income · Asset-based · Replacement Cost

Plugin registry supports future models without redesign.

## APIs

`/v1/ve/health` · `/dashboard` · `/company` · `/model` · `/history` · `/scenarios` · `/compare` · `/sensitivity` · `/search` · `/consult` · `/value` · `/valuation/{id}`

Admin: `/admin/valuation`

## Out of scope (v2/v3)

Monte Carlo, real options, AI assumption generation — not implemented in v1.
