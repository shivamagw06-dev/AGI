# AGI Industry Intelligence Framework

AGI already maintains two complementary canonical stores:

- Industry DNA explains industry economics, KPIs, regulation, competition, cycles and causal context.
- SIF defines the institutional underwriting checklist, required evidence, valuation methods, risks and monitoring signals.

`industry_intelligence.framework.framework_for()` is the governed read facade over both. It does not duplicate either registry. It resolves an industry and returns one analysis contract for AFE, valuation, scenarios, causal reasoning and Ask AGI.

Coverage is explicit. A fully matched industry returns `COMPLETE`; an industry present in only one store returns `PARTIAL` with `missing_layers`; an unknown industry returns `INDUSTRY_UNAVAILABLE`. No missing industry knowledge is synthesized.

The next integration gate is company classification to this facade, followed by mapping its required KPIs to canonical warehouse facts and deterministic AFE calculations.
