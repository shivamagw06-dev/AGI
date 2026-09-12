# Phase 2 Deferred Refinements — Backlog (NOT implemented, post-freeze only)

**Status:** Phase 1 (`financial_foundations` v1.0.0) and Phase 2
(`financial_statement_intelligence` v1.0.0) are **frozen** as of the
Institutional Accounting Exam (Level 1) release-gate pass (93.7% overall,
all release-gate criteria met — see `run_exam.py` output / the exam PR).

Per the freeze policy (`RELEASE_STATUS["policy"] = "no_new_features_bug_fixes_only"`
in both packages' `schema.py`), nothing below has been implemented. This
document exists solely to record specific, concrete refinements identified
while reviewing the exam's actual answers, so they are not lost — and so a
future increment can pick them up without re-deriving them from scratch.

None of these are correctness bugs (all are documented and covered by the
exam's 100% accounting-correctness / 100% statement-linkage / 0%
hallucination results). They are depth-of-interpretation upgrades.

---

## 1. Broader hypothesis enumeration for ambiguous single-signal questions

**Where:** `rule_library.py` scenario explanations (e.g. `revenue_vs_inventory`,
surfaced in exam Q7); `ebitda_vs_capex` (Q12).

**Current behavior (Q7 — Inventory doubles, Revenue flat):**
> "may indicate demand slowdown (unsold stock building) or a deliberate
> strategic build ahead of expected demand."

**Requested additional hypotheses:** product-launch preparation,
supply-chain buffering, commodity-price-expectation-driven stocking,
seasonal stocking patterns.

**Design note for the future implementer:** these are genuinely
*non-derivable from the two-metric delta alone* — they require either (a)
an explicit `context_hints` parameter callers can supply (season, product
launch calendar, commodity outlook), analogous to the `drivers` parameter
already accepted by `narrative_generator.generate_narrative()`, or (b) a
larger `PLAUSIBLE_CAUSES`-style catalog (see `uncertainty_guard.py`) keyed
by scenario type, listed as *additional untested hypotheses* rather than
asserted causes — to avoid quietly turning a 2-signal rule into an
overconfident 6-hypothesis claim.

## 2. Capex classification (maintenance / growth / capacity / regulatory / technology)

**Where:** `metric_concepts.py` (`free_cash_flow`, `capex_vs_depreciation`
pair in `rule_library.py`); surfaced in exam Q12.

**Current behavior:** capex doubling is described only as a
"reinvestment-phase pattern."

**Requested:** classify capex by purpose. This is valuable for capital
allocation analysis (a natural Phase 3 concern) but requires a new input
field on `StatementPeriod` (e.g. `capex_breakdown: dict[str, float]` with
keys `maintenance`, `growth`, `capacity`, `regulatory`, `technology`) since
the generic schema currently only carries a single `capex` total. This is
a schema addition, not a Phase 2 logic bug — flagged for Phase 3 or a
dedicated Phase 2.1 increment, whichever comes first.

## 3. Deeper goodwill/M&A interpretation (PPA effects, overpayment, synergies)

**Where:** `metric_concepts.py` (`goodwill_and_intangibles`);
`red_flag_detector.py` (`_large_goodwill_jump`); surfaced in exam Q21.

**Current behavior:** goodwill tripling is interpreted as integration-lag
risk and future impairment-concentration risk.

**Requested additional depth:** Purchase Price Allocation (PPA) effects
(how much of the premium was allocated to identifiable intangibles vs.
residual goodwill), explicit overpayment framing (premium vs. peer
multiples), and forward-looking synergy realisation tracking. The last
two require data Phase 2's generic schema does not carry (deal terms,
peer multiples, synergy targets/actuals) — this is naturally an
`institutional_stack` / M&A-specific extension, not a `StatementPeriod`
field, and should be scoped separately from the core FSI engine.

## 4. Investment-committee-memo style prose for the analyst note

**Where:** `narrative_generator.generate_long_form_note()`; surfaced in
the Section F case study.

**Current style (metric-forward):**
> "Revenue declined 7.7%. Gross margins expanded 488 basis points —
> improved pricing power or cost control per unit sold."

**Requested style (institutional-memo-forward):**
> "Revenue declined primarily due to weaker volume, but management
> preserved profitability through pricing discipline and operating-cost
> control. Cash conversion strengthened despite lower accounting profit,
> suggesting underlying operating resilience. However, receivables
> expanded faster than revenue, warranting monitoring over subsequent
> quarters."

**Design note:** this is a genuine prose-quality upgrade (subordinate
clauses, causal connectors, an implicit "so what" framing) rather than a
new capability — every fact in both versions traces to the same computed
evidence. The right place to build it is a second narrative "voice" in
`narrative_generator.py` (e.g. `style="metric_forward"` vs.
`style="memo_forward"`) so the existing evidence-grounding guarantees are
preserved while the sentence construction becomes more sophisticated.
Deferred past the freeze because it is a "nice to have" wording
refinement, not a correctness or coverage gap.

---

## Explicitly out of scope for Phase 2 (belongs to Phase 3+)

Per the Phase 3 direction (business models, unit economics, competitive
advantage/moats, industry structure, pricing power, customer economics,
cost structure, operating leverage, network effects, capital intensity,
growth strategy, management quality) — none of the above 4 items should
be expanded into full business-strategy reasoning within Phase 2. Phase 2
remains "how do I read the numbers"; Phase 3 is "why do the numbers look
this way."
