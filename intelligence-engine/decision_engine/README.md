# AGIB Investment Decision Engine (soft-wire)

Architecture **v1.0.1 LOCKED** — additive soft-wire only. Not an engine redesign.

For questions like “Should I buy X?”, Ask AGI must not jump Company → Buy/Sell.

It runs the institutional hierarchy:

Macro → Industry → Company → Financials → Management → Valuation → Market Expectations → Technical → Risk → Catalysts → Probability → Expected Return → **Decision (last)**

Every layer is always present. Incomplete evidence lowers score/confidence — it never deletes the layer.

Client payloads never expose CID/IRP/LEO/SIF/provider names.
