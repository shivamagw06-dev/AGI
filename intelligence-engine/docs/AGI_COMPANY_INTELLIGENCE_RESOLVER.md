# AGI Company Intelligence Resolver

The Company Intelligence Resolver composes existing governed layers:

`canonical company identity → industry framework → required KPIs → warehouse facts / AFE → research protocol`

It does not create a company database or infer an industry. Canonical company identity remains authoritative. A company without an approved classification returns `COMPANY_CLASSIFICATION_UNAVAILABLE`.

## KPI coverage states

- `CALCULATED`: all required inputs resolved and AFE can reproduce the KPI.
- `SOURCE_AVAILABLE`: the requested-period canonical observation exists with provenance.
- `MISSING`: the KPI mapping exists but the required observation or calculation input does not.
- `UNMAPPED`: AGI has not approved a canonical mapping for that industry KPI.

Coverage counts only `CALCULATED` and `SOURCE_AVAILABLE`. Older-period or future-published observations do not satisfy a requested period/as-of date.

Multi-segment companies may provide explicit segment-to-industry assignments and weights. The resolver applies each industry framework and combines the required KPI set without forcing the company into one model. It does not infer segment weights from narrative text.

Ask AGI accesses the profile through the governed `GET_COMPANY_ANALYSIS` read tool. The output supplies analytical structure and data gaps; it does not itself issue an investment recommendation.
