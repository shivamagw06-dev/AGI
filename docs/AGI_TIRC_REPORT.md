# AGI Temporal Integrity Report (TIRC)

**Company:** AGI  
**Version:** temporal-integrity-v1.0.0  
**Certification:** CERTIFIED  
**Date:** 2026-07-28

## Metrics

- Future leakage count: **0**
- Replay accuracy (historical): **100.0%**
- IEL pass (1,025 full): **99.9%**
- CIO-25 pass: **100%**
- Rejected sources (examples): `imai_surface_bullet`, `institutional_analog`

## Institutional guarantee

Historical replay answers use only information that was available at the requested `as_of` point in time. Future-year labels, post-`as_of` analogs, and future graph edges are rejected — never silently substituted.

## Remaining risks

None for the certification gates. Non-blocking: CIO-Q11/Q16 intent dimension (Industry vs Macro/CrossDomain) remains at 99.8% suite intent accuracy.
