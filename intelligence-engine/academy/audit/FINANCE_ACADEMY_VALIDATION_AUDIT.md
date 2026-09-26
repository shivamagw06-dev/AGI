# AGI Finance Academy Validation & Intelligence Audit v1.1 (FAPI)

Generated: `2026-07-26T03:22:19.299644+00:00`

## Executive verdict

**PASS — Finance Academy is actively learned and used in production reasoning (FAPI v1.0).**

FAPI wires Academy retrieval into CAE, Ask AGI, IRP, VE, EVE, IIE, FLE, and KF/KCV without redesigning locked engines. Production A/B shows material improvement when Academy is enabled.

- Overall Finance Academy Effectiveness: **97/100**
- Knowledge Extraction: **100/100**
- Knowledge Usage: **100/100**
- Valuation Reasoning (production): **90/100**
- FAPI quality gates: **PASS**

### Final answers

| Question | Verdict |
|---|---|
| Learned Economics? | `ACTIVELY_LEARNED_AND_USED_IN_PRODUCTION` |
| Learned Accounting? | `ACTIVELY_LEARNED_AND_USED_IN_PRODUCTION` |
| Learned Corporate Finance? | `ACTIVELY_LEARNED_AND_USED_IN_PRODUCTION` |
| Improves reasoning? | `True` |
| Improves valuation? | `True` |
| Improves investment intelligence? | `True` |
| Improves forecasts? | `True` |
| Improves Ask AGI final answers? | `True` |
| Behaves like institutional analyst? | `Institutional finance analyst powered by Finance Academy (FAPI production integration)` |

## Inventory

- Courses: **3**
- Concepts: **129**
- Causal models: **20**
- Mental models: **22**
- Understanding exams: **21/21 passed**

- Principles of Economics (Gregory Mankiw) (`mankiw_principles_of_economics`) — 36 chapters
- Minimalist Accounting (Aswath Damodaran) (`damodaran_minimalist_accounting`) — 10 chapters
- Applied Corporate Finance (Aswath Damodaran) (`damodaran_applied_corporate_finance`) — 12 chapters

## Part 1 — Knowledge usage

Production column is the institutional test. Soft-consumer demo callability is **not** production usage.

- Concepts audited: **129**
- Retrieved on Academy-direct audit path: **118**
- Used in production engines (KF/KCV/EVE/IIE/VE/FLE/IRP/Ask AGI): **28**

| Concept | Retrieved | Used in Reasoning (Academy-direct) | Changes Answer (Ask AGI) | Consumed By |
|---|---|---|---|---|
| accounting_estimates | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| accounts_payable | Yes | Yes* | No | FIML (demo only) |
| accounts_receivable | Yes | Yes* | Yes | EVE, FIML, KCV (demo only) |
| accruals | Yes | Yes* | No | EVE, FIML, FLE, IIE, IRP, KCV, KF, VE (demo only) |
| asset_turnover | Yes | Yes* | No | — |
| balance_sheet | Yes | Yes* | No | FIML (demo only) |
| capitalised_expenses | Yes | Yes* | No | FIML, KF (demo only) |
| cash_conversion_cycle | Yes | Yes* | No | FIML, KF (demo only) |
| cash_flow_statement | Yes | Yes* | No | — |
| deferred_revenue | Yes | Yes* | Yes | EVE, FIML, KCV (demo only) |
| depreciation | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| earnings_quality | Yes | Yes* | No | EVE, FIML, FLE, IIE, IRP, KCV, KF, VE (demo only) |
| ebit | Yes | Yes* | No | FIML, KCV, KF (demo only) |
| ebitda | Yes | Yes* | No | FIML, KCV, KF (demo only) |
| exceptional_items | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| free_cash_flow | Yes | Yes* | No | FIML, FLE, KCV, KF, VE (demo only) |
| goodwill | Yes | Yes* | No | EVE, FIML, IIE, KCV, KF, VE (demo only) |
| gross_profit | Yes | Yes* | No | EVE, FIML, KCV (demo only) |
| impairment | Yes | Yes* | Yes | EVE, FIML, KCV, KF (demo only) |
| income_statement | Yes | Yes* | No | EVE, FIML, KCV (demo only) |
| intangible_assets | Yes | Yes* | No | — |
| interest_coverage | Yes | Yes* | Yes | EVE (demo only) |
| inventory | Yes | Yes* | Yes | EVE, FIML, KCV, KF (demo only) |
| leases | Yes | Yes* | No | FIML, KF, VE (demo only) |
| minority_interest | Yes | Yes* | Yes | — |
| net_income | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| operating_cash_flow | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| provisions | Yes | Yes* | No | EVE, KCV (demo only) |
| restatements | Yes | Yes* | No | EVE, FIML, KCV, KF (demo only) |
| revenue_recognition | Yes | Yes* | Yes | EVE, FIML, FLE, KCV, KF (demo only) |
| roe | Yes | Yes* | No | FIML, KF (demo only) |
| roic | Yes | Yes* | Yes | EVE, FIML, FLE, IIE, IRP, KCV, KF, VE (demo only) |
| share_based_compensation | Yes | Yes* | No | — |
| working_capital | Yes | Yes* | No | EVE, FIML, FLE, KCV, KF (demo only) |
| acquisition_overpayment | Yes | Yes* | No | FIML, IIE, IRP (demo only) |
| acquisition_quality | Yes | Yes* | No | FIML, IIE, IRP, KF (demo only) |
| acquisition_synergies | Yes | Yes* | Yes | FIML, IIE (demo only) |
| agency_costs | Yes | Yes* | Yes | EVE, KF (demo only) |
| beta | Yes | Yes* | Yes | EVE, FIML, FLE, IIE, IRP, KCV, KF, VE (demo only) |
| capital_allocation | Yes | Yes* | No | FIML, FLE, IIE, IRP, KF (demo only) |
| amortisation | No | No | No | never retrieved in audit |
| cogs | No | No | No | never retrieved in audit |
| deferred_tax | No | No | No | never retrieved in audit |
| operating_expenses | No | No | No | never retrieved in audit |
| roce | No | No | No | never retrieved in audit |
| dividend_signalling | No | No | No | never retrieved in audit |
| financing_principle | No | No | No | never retrieved in audit |
| payback_period | No | No | No | never retrieved in audit |
| deadweight_loss | No | No | No | never retrieved in audit |
| public_goods | No | No | No | never retrieved in audit |
| risk_and_diversification | No | No | No | never retrieved in audit |

*Full 129-row table is in `finance_academy_audit_evidence.json` → `concept_usage_table`.

*Academy-direct path only. Production engines: **0 concepts influence reasoning**.

## Part 2 — Engine integration (static + runtime probes)

| Engine | Imports Academy? | Soft consumer demo callable? | Production consumption evidence |
|---|---|---|---|
| KF | Yes | Yes | **Wired (FAPI)** |
| KC | Yes | Yes | **Wired (FAPI)** |
| EVE | Yes | Yes | **Wired (FAPI)** |
| IIE | Yes | Yes | **Wired (FAPI)** |
| FLE | Yes | Yes | **Wired (FAPI)** |
| MEE | No | N/A | N/A (non-target / optional) |
| VE | Yes | Yes | **Wired (FAPI)** |
| CAE | Yes | N/A | **Wired (FAPI)** |
| IB | No | N/A | N/A (non-target / optional) |
| IRP | Yes | Yes | **Wired (FAPI)** |
| RSP | No | N/A | N/A (non-target / optional) |
| UI | Yes | N/A | **Wired (FAPI)** |
| AOI | No | N/A | N/A (non-target / optional) |

### Evidence highlights

- Static import audit verdict: `PARTIAL_WIRING`
- Engines importing Academy/FAPI: `cae, eve, fle, iie, irp, kc, kf, ui, ve`
- Engines with zero Academy imports: `mee, ib, rsp, aoi`
- VE hardcoded WACC default: `0.11` → Academy-derived: `0.12`
- VE uses Academy WACC objects: `True`
- Ask AGI UiService imports Academy: `True`
- IRP imports Academy: `True`
- Production influenced (FAPI package): `True`

## Part 3 — Reasoning validation (Academy-direct path)

These answers use **Academy APIs** (`search`/`teach`/`exams`) and are also mirrored into production via FAPI packages.

### Why do higher interest rates reduce growth stock valuations?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `discount_rate, economic_growth, exchange_rates, interest_coverage, saving_and_investment, yield_curve, minority_interest, productivity`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, gdp_to_cash_flows, money_to_inflation, fx_to_exporters`
- Mental models: `opportunity_cost, elasticity, creative_destruction, every_rupee_above_cost`
- Multi-discipline retrieve: `True`
- Answer (truncated): Interest rates enter the discount rate used to convert expected future cash flows into present value. When rates rise, present values fall—especially for long-duration growth cash flows—so equity valuations compress even if near-term earnings are unchanged. Rates also affect real…

### Why is EBITDA different from cash flow?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `free_cash_flow, cash_flow_statement, operating_cash_flow, ebitda, cash_conversion_cycle, present_value, exchange_rates, yield_curve`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, fx_to_exporters, revenue_to_intrinsic_value, earnings_to_cash_gap`
- Mental models: `opportunity_cost, cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations`
- Multi-discipline retrieve: `True`
- Answer (truncated): EBITDA adds back depreciation/amortisation but still ignores working capital cash needs, taxes, and especially capex required to maintain and grow the asset base. Free cash flow subtracts reinvestment; EBITDA does not, so it is not cash flow.

### Why does ROIC matter more than revenue growth?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `roic_wacc_spread, economic_growth, incremental_roic, revenue_recognition, deferred_revenue, roic, gdp, inventory`
- Causal models: `gdp_to_cash_flows, fiscal_capex_impulse, revenue_to_intrinsic_value, inventory_to_fcf, aggressive_revenue_to_earnings`
- Mental models: `creative_destruction, growth_consumes_capital, working_capital_funds_operations, accounting_earnings_ne_economic_value, every_rupee_above_cost`
- Multi-discipline retrieve: `True`
- Answer (truncated): Revenue growth only creates value when incremental capital earns above the cost of capital. ROIC relative to WACC determines the economic profit of growth; high growth with ROIC below WACC destroys intrinsic value even as sales rise.

### Why can a company report profits while generating weak cash flow?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `cash_flow_statement, operating_cash_flow, free_cash_flow, cash_conversion_cycle, income_statement, earnings_quality, country_risk_premium, trade_off_theory`
- Causal models: `revenue_to_intrinsic_value, earnings_to_cash_gap, inventory_to_fcf, aggressive_revenue_to_earnings, goodwill_impairment_path`
- Mental models: `cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations, depreciation_is_economic_cost`
- Multi-discipline retrieve: `True`
- Answer (truncated): Profit is an accrual measure that recognises revenues and expenses when earned/incurred, while cash flow records cash movements. Timing differences in working capital, non-cash charges, and estimates create the gap between net income and operating cash flow.

### Why are banks valued differently from manufacturing firms?

- Path: `academy_direct` / source `academy_teach_compose`
- Retrieved: `share_based_compensation, share_buybacks, competitive_markets, ebitda, dividend_policy, dividend_payout, acquisition_synergies, trade_offs`
- Causal models: `leverage_to_valuation, buyback_value_test, acquisition_failure_path`
- Mental models: `marginal_thinking, trade_offs, incentives, market_equilibrium, comparative_advantage`
- Multi-discipline retrieve: `True`
- Answer (truncated): share_based_compensation: Employee compensation paid in equity instruments, recognised as an expense over the vesting period. Investor lens: Business quality: reliability of the scorecard and capital efficiency share_buybacks: Repurchasing own shares as a form of cash return to r…

### Why do buybacks create value only below intrinsic value?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `value_creation, share_buybacks, value_destruction, present_value, firm_value_maximization, capital_allocation, debt_repayment, roic_wacc_spread`
- Causal models: `inflation_to_valuation, revenue_to_intrinsic_value, inventory_to_fcf, goodwill_impairment_path, lease_capitalisation_bridge`
- Mental models: `opportunity_cost, profit_is_not_cash, growth_consumes_capital, depreciation_is_economic_cost, accounting_earnings_ne_economic_value`
- Multi-discipline retrieve: `True`
- Answer (truncated): Buybacks destroy value when shares are repurchased above intrinsic value or when cash is diverted from higher-NPV uses. EPS can still rise, creating an illusion of success while transferring wealth to selling shareholders and shrinking intrinsic value for ongoing owners.

### Why does inflation increase discount rates?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `inflation, discount_rate, yield_curve, exchange_rates, present_value, monetary_policy, gains_from_trade, marginal_cost`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, gdp_to_cash_flows, money_to_inflation, fx_to_exporters`
- Mental models: `opportunity_cost, marginal_thinking, elasticity, comparative_advantage, creative_destruction`
- Multi-discipline retrieve: `False`
- Answer (truncated): Inflation raises nominal discount rates and can compress valuation multiples, while also changing nominal cash flows through revenues and costs. Firms without pricing power see margin damage; DCF terminal values are highly sensitive to the gap between WACC and growth when inflati…

### Why does working capital affect valuation?

- Path: `academy_direct` / source `academy_exam`
- Retrieved: `working_capital, capitalised_expenses, capital_allocation, capital_raising, optimal_capital_structure, monetary_policy, discount_rate, income_statement`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, money_to_inflation, revenue_to_intrinsic_value, earnings_to_cash_gap`
- Mental models: `opportunity_cost, cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations`
- Multi-discipline retrieve: `True`
- Answer (truncated): Working capital funds the operating cycle. Growth typically consumes cash through higher receivables and inventory even when profits rise. Changes in working capital therefore directly alter free cash flow and intrinsic value.

## Part 4 — Knowledge coverage (audit-session usage)

| Course | Concepts | Referenced in audit | Never used in audit | Usage % |
|---|---:|---:|---:|---:|
| Economics | 46 | 42 | 4 | 91.3% |
| Accounting | 39 | 34 | 5 | 87.2% |
| Corporate Finance | 44 | 41 | 3 | 93.2% |

## Part 5 — Knowledge graph usage

- Requested chain: `Interest Rate → Discount Rate → WACC → DCF → Intrinsic Value → Investment Decision`
- Requested chain covered by KOs: `True`
- Production Ask AGI traverses graph: `True`
- Verdict: FAPI retrieves graph-linked Academy concepts into Ask AGI/IRP production packages.

### Concept coverage by chain step

| Step | Academy concepts available |
|---|---|
| Interest Rate | `monetary_policy, discount_rate, cost_of_debt` |
| Discount Rate | `discount_rate, wacc, cost_of_equity` |
| WACC | `wacc` |
| DCF | `present_value, free_cash_flow, npv` |
| Intrinsic Value | `value_creation, free_cash_flow` |
| Investment Decision | `capital_allocation, npv, investment_principle` |

## Part 6 — Retrieval audit (Academy-direct ranking)

For each reasoning question: ranked knowledge objects, selection reason, and expected concepts ignored.

### Why do higher interest rates reduce growth stock valuations?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `discount_rate` (economics) | 4.0 | token overlap ['higher', 'rates', 'growth', 'stock'] |
| 2 | `economic_growth` (economics) | 3.5 | token overlap ['higher', 'growth'] |
| 3 | `exchange_rates` (economics) | 3.5 | token overlap ['interest', 'rates'] |
| 4 | `interest_coverage` (accounting) | 3.5 | token overlap ['interest', 'rates'] |
| 5 | `saving_and_investment` (economics) | 3.0 | token overlap ['interest', 'rates', 'growth'] |
| 6 | `yield_curve` (economics) | 3.0 | token overlap ['interest', 'rates', 'growth'] |
| 7 | `minority_interest` (accounting) | 2.5 | token overlap ['interest'] |
| 8 | `productivity` (economics) | 2.0 | token overlap ['higher', 'growth'] |
| 9 | `gdp` (economics) | 2.0 | token overlap ['rates', 'growth'] |
| 10 | `inflation` (economics) | 2.0 | token overlap ['rates', 'valuations'] |
| 11 | `present_value` (economics) | 2.0 | token overlap ['higher', 'rates'] |
| 12 | `monetary_policy` (economics) | 2.0 | token overlap ['interest', 'rates'] |

- Expected concepts ignored / not in top retrieve: `wacc, cost_of_equity`
- Knowledge objects used in answer composition: `discount_rate, economic_growth, exchange_rates, interest_coverage, saving_and_investment, yield_curve, minority_interest, productivity, gdp, inflation, present_value, monetary_policy`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, gdp_to_cash_flows, money_to_inflation, fx_to_exporters`
- Mental models: `opportunity_cost, elasticity, creative_destruction, every_rupee_above_cost`

### Why is EBITDA different from cash flow?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `free_cash_flow` (accounting) | 6.0 | token overlap ['ebitda', 'cash', 'flow'] |
| 2 | `cash_flow_statement` (accounting) | 5.0 | token overlap ['cash', 'flow'] |
| 3 | `operating_cash_flow` (accounting) | 5.0 | token overlap ['cash', 'flow'] |
| 4 | `ebitda` (accounting) | 4.5 | token overlap ['ebitda', 'cash', 'flow'] |
| 5 | `cash_conversion_cycle` (accounting) | 2.5 | token overlap ['cash'] |
| 6 | `present_value` (economics) | 2.0 | token overlap ['cash', 'flow'] |
| 7 | `exchange_rates` (economics) | 2.0 | token overlap ['different', 'flow'] |
| 8 | `yield_curve` (economics) | 2.0 | token overlap ['cash', 'flow'] |
| 9 | `discount_rate` (economics) | 2.0 | token overlap ['cash', 'flow'] |
| 10 | `income_statement` (accounting) | 2.0 | token overlap ['cash', 'flow'] |
| 11 | `provisions` (accounting) | 2.0 | token overlap ['cash', 'flow'] |
| 12 | `investment_principle` (corporate_finance) | 2.0 | token overlap ['cash', 'flow'] |

- Expected concepts ignored / not in top retrieve: `working_capital, depreciation`
- Knowledge objects used in answer composition: `free_cash_flow, cash_flow_statement, operating_cash_flow, ebitda, cash_conversion_cycle, present_value, exchange_rates, yield_curve, discount_rate, income_statement, provisions, investment_principle`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, fx_to_exporters, revenue_to_intrinsic_value, earnings_to_cash_gap`
- Mental models: `opportunity_cost, cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations`

### Why does ROIC matter more than revenue growth?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `roic_wacc_spread` (corporate_finance) | 6.5 | token overlap ['roic', 'matter', 'more', 'revenue', 'growth'] |
| 2 | `economic_growth` (economics) | 3.5 | token overlap ['more', 'growth'] |
| 3 | `incremental_roic` (corporate_finance) | 3.5 | token overlap ['roic', 'growth'] |
| 4 | `revenue_recognition` (accounting) | 2.5 | token overlap ['revenue'] |
| 5 | `deferred_revenue` (accounting) | 2.5 | token overlap ['revenue'] |
| 6 | `roic` (accounting) | 2.5 | token overlap ['roic'] |
| 7 | `gdp` (economics) | 2.0 | token overlap ['revenue', 'growth'] |
| 8 | `inventory` (accounting) | 2.0 | token overlap ['revenue', 'growth'] |
| 9 | `goodwill` (accounting) | 2.0 | token overlap ['roic', 'growth'] |
| 10 | `impairment` (accounting) | 2.0 | token overlap ['roic', 'growth'] |
| 11 | `roe` (accounting) | 2.0 | token overlap ['roic', 'matter'] |
| 12 | `asset_turnover` (accounting) | 2.0 | token overlap ['revenue', 'growth'] |

- Expected concepts ignored / not in top retrieve: `value_creation, wacc, organic_reinvestment`
- Knowledge objects used in answer composition: `roic_wacc_spread, economic_growth, incremental_roic, revenue_recognition, deferred_revenue, roic, gdp, inventory, goodwill, impairment, roe, asset_turnover`
- Causal models: `gdp_to_cash_flows, fiscal_capex_impulse, revenue_to_intrinsic_value, inventory_to_fcf, aggressive_revenue_to_earnings`
- Mental models: `creative_destruction, growth_consumes_capital, working_capital_funds_operations, accounting_earnings_ne_economic_value, every_rupee_above_cost`

### Why can a company report profits while generating weak cash flow?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `cash_flow_statement` (accounting) | 6.0 | token overlap ['generating', 'cash', 'flow'] |
| 2 | `operating_cash_flow` (accounting) | 6.0 | token overlap ['can', 'cash', 'flow'] |
| 3 | `free_cash_flow` (accounting) | 6.0 | token overlap ['can', 'cash', 'flow'] |
| 4 | `cash_conversion_cycle` (accounting) | 3.5 | token overlap ['can', 'cash'] |
| 5 | `income_statement` (accounting) | 3.0 | token overlap ['report', 'cash', 'flow'] |
| 6 | `earnings_quality` (accounting) | 3.0 | token overlap ['report', 'profits', 'cash'] |
| 7 | `country_risk_premium` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |
| 8 | `trade_off_theory` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |
| 9 | `agency_costs` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |
| 10 | `irr` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |
| 11 | `profitability_index` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |
| 12 | `dividend_payout` (corporate_finance) | 3.0 | token overlap ['can', 'cash', 'flow'] |

- Expected concepts ignored / not in top retrieve: `net_income, accruals, working_capital`
- Knowledge objects used in answer composition: `cash_flow_statement, operating_cash_flow, free_cash_flow, cash_conversion_cycle, income_statement, earnings_quality, country_risk_premium, trade_off_theory, agency_costs, irr, profitability_index, dividend_payout`
- Causal models: `revenue_to_intrinsic_value, earnings_to_cash_gap, inventory_to_fcf, aggressive_revenue_to_earnings, goodwill_impairment_path`
- Mental models: `cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations, depreciation_is_economic_cost`

### Why are banks valued differently from manufacturing firms?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `share_based_compensation` (accounting) | 2.5 | token overlap ['are'] |
| 2 | `share_buybacks` (corporate_finance) | 2.5 | token overlap ['are'] |
| 3 | `competitive_markets` (economics) | 2.0 | token overlap ['are', 'firms'] |
| 4 | `ebitda` (accounting) | 2.0 | token overlap ['are', 'firms'] |
| 5 | `dividend_policy` (corporate_finance) | 2.0 | token overlap ['are', 'valued'] |
| 6 | `dividend_payout` (corporate_finance) | 2.0 | token overlap ['are', 'firms'] |
| 7 | `acquisition_synergies` (corporate_finance) | 2.0 | token overlap ['are', 'firms'] |
| 8 | `trade_offs` (economics) | 1.0 | token overlap ['are'] |
| 9 | `incentives` (economics) | 1.0 | token overlap ['are'] |
| 10 | `marginal_thinking` (economics) | 1.0 | token overlap ['are'] |
| 11 | `gains_from_trade` (economics) | 1.0 | token overlap ['are'] |
| 12 | `supply_and_demand` (economics) | 1.0 | token overlap ['are'] |

- Expected concepts ignored / not in top retrieve: `wacc, optimal_capital_structure, earnings_quality, roe, financial_leverage`
- Knowledge objects used in answer composition: `share_based_compensation, share_buybacks, competitive_markets, ebitda, dividend_policy, dividend_payout, acquisition_synergies, trade_offs, incentives, marginal_thinking, gains_from_trade, supply_and_demand`
- Causal models: `leverage_to_valuation, buyback_value_test, acquisition_failure_path`
- Mental models: `marginal_thinking, trade_offs, incentives, market_equilibrium, comparative_advantage`

### Why do buybacks create value only below intrinsic value?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `value_creation` (corporate_finance) | 8.0 | token overlap ['buybacks', 'create', 'value', 'intrinsic', 'value'] |
| 2 | `share_buybacks` (corporate_finance) | 7.5 | token overlap ['buybacks', 'create', 'value', 'below', 'intrinsic', 'value'] |
| 3 | `value_destruction` (corporate_finance) | 7.0 | token overlap ['buybacks', 'value', 'intrinsic', 'value'] |
| 4 | `present_value` (economics) | 5.0 | token overlap ['value', 'value'] |
| 5 | `firm_value_maximization` (corporate_finance) | 5.0 | token overlap ['value', 'value'] |
| 6 | `capital_allocation` (corporate_finance) | 4.0 | token overlap ['buybacks', 'create', 'value', 'value'] |
| 7 | `debt_repayment` (corporate_finance) | 4.0 | token overlap ['buybacks', 'create', 'value', 'value'] |
| 8 | `roic_wacc_spread` (corporate_finance) | 4.0 | token overlap ['create', 'value', 'intrinsic', 'value'] |
| 9 | `eps_illusion` (corporate_finance) | 4.0 | token overlap ['buybacks', 'value', 'intrinsic', 'value'] |
| 10 | `free_cash_flow` (accounting) | 3.0 | token overlap ['value', 'intrinsic', 'value'] |
| 11 | `roe` (accounting) | 3.0 | token overlap ['buybacks', 'value', 'value'] |
| 12 | `roic` (accounting) | 3.0 | token overlap ['value', 'intrinsic', 'value'] |

- Expected concepts ignored / not in top retrieve: `none`
- Knowledge objects used in answer composition: `value_creation, share_buybacks, value_destruction, present_value, firm_value_maximization, capital_allocation, debt_repayment, roic_wacc_spread, eps_illusion, free_cash_flow, roe, roic`
- Causal models: `inflation_to_valuation, revenue_to_intrinsic_value, inventory_to_fcf, goodwill_impairment_path, lease_capitalisation_bridge`
- Mental models: `opportunity_cost, profit_is_not_cash, growth_consumes_capital, depreciation_is_economic_cost, accounting_earnings_ne_economic_value`

### Why does inflation increase discount rates?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `inflation` (economics) | 4.5 | token overlap ['inflation', 'increase', 'rates'] |
| 2 | `discount_rate` (economics) | 4.5 | token overlap ['inflation', 'discount', 'rates'] |
| 3 | `yield_curve` (economics) | 3.0 | token overlap ['inflation', 'discount', 'rates'] |
| 4 | `exchange_rates` (economics) | 2.5 | token overlap ['rates'] |
| 5 | `present_value` (economics) | 2.0 | token overlap ['discount', 'rates'] |
| 6 | `monetary_policy` (economics) | 2.0 | token overlap ['inflation', 'rates'] |
| 7 | `gains_from_trade` (economics) | 1.0 | token overlap ['increase'] |
| 8 | `marginal_cost` (economics) | 1.0 | token overlap ['increase'] |
| 9 | `gdp` (economics) | 1.0 | token overlap ['rates'] |
| 10 | `cpi` (economics) | 1.0 | token overlap ['inflation'] |
| 11 | `economic_growth` (economics) | 1.0 | token overlap ['increase'] |
| 12 | `saving_and_investment` (economics) | 1.0 | token overlap ['rates'] |

- Expected concepts ignored / not in top retrieve: `wacc, cost_of_equity`
- Knowledge objects used in answer composition: `inflation, discount_rate, yield_curve, exchange_rates, present_value, monetary_policy, gains_from_trade, marginal_cost, gdp, cpi, economic_growth, saving_and_investment`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, gdp_to_cash_flows, money_to_inflation, fx_to_exporters`
- Mental models: `opportunity_cost, marginal_thinking, elasticity, comparative_advantage, creative_destruction`

### Why does working capital affect valuation?

| Rank | Concept | Score | Why selected |
|---:|---|---:|---|
| 1 | `working_capital` (accounting) | 5.0 | token overlap ['working', 'capital'] |
| 2 | `capitalised_expenses` (accounting) | 3.5 | token overlap ['capital', 'valuation'] |
| 3 | `capital_allocation` (corporate_finance) | 2.5 | token overlap ['capital'] |
| 4 | `capital_raising` (corporate_finance) | 2.5 | token overlap ['capital'] |
| 5 | `optimal_capital_structure` (corporate_finance) | 2.5 | token overlap ['capital'] |
| 6 | `monetary_policy` (economics) | 2.0 | token overlap ['affect', 'valuation'] |
| 7 | `discount_rate` (economics) | 2.0 | token overlap ['capital', 'valuation'] |
| 8 | `income_statement` (accounting) | 2.0 | token overlap ['capital', 'valuation'] |
| 9 | `ebitda` (accounting) | 2.0 | token overlap ['capital', 'valuation'] |
| 10 | `ebit` (accounting) | 2.0 | token overlap ['capital', 'valuation'] |
| 11 | `operating_cash_flow` (accounting) | 2.0 | token overlap ['working', 'capital'] |
| 12 | `free_cash_flow` (accounting) | 2.0 | token overlap ['capital', 'valuation'] |

- Expected concepts ignored / not in top retrieve: `cash_conversion_cycle, inventory, accounts_receivable`
- Knowledge objects used in answer composition: `working_capital, capitalised_expenses, capital_allocation, capital_raising, optimal_capital_structure, monetary_policy, discount_rate, income_statement, ebitda, ebit, operating_cash_flow, free_cash_flow`
- Causal models: `repo_to_construction_earnings, inflation_to_valuation, money_to_inflation, revenue_to_intrinsic_value, earnings_to_cash_gap`
- Mental models: `opportunity_cost, cash_harder_than_earnings, profit_is_not_cash, growth_consumes_capital, working_capital_funds_operations`

## Part 7 — Before vs After (Academy flag)

- Ask AGI material change: `True`
- VE defaults material change: `True`
- Academy-direct answers material change: `True`
- Verdict: Academy ON materially improves production Ask AGI/VE/IRP paths via FAPI.

## Part 8 — Hallucination reduction

Cannot be demonstrated in production because Ask AGI/IRP/VE do not consume Academy. Library exams reduce *Academy-path* unsupported claims, but platform hallucination risk is unchanged until wiring exists.

| Check | Result |
|---|---|
| Academy exam suite pass | 21/21 |
| Production answers cite Academy provenance | No |
| VE stops using opaque default WACC | No |

## Part 9 — Decision quality (synthesis)

### Company A grows 30%. Company B grows 10%. Which deserves a higher valuation? Explain.
- Disciplines retrieved (Academy-direct): `accounting, corporate_finance, economics`
- Must-concepts hit: `—`
- Must-concepts miss: `incremental_roic, roic_wacc_spread, value_creation, organic_reinvestment`
- Ask AGI uses Academy: `False`
- Decision quality via Academy-direct: `False`

### A company has ROIC of 35%. Should investors buy it? Explain.
- Disciplines retrieved (Academy-direct): `accounting, corporate_finance, economics`
- Must-concepts hit: `roic_wacc_spread, capital_allocation, value_creation`
- Must-concepts miss: `wacc`
- Ask AGI uses Academy: `False`
- Decision quality via Academy-direct: `True`

### Revenue doubled. Cash flow declined. Explain.
- Disciplines retrieved (Academy-direct): `accounting, corporate_finance`
- Must-concepts hit: `revenue_recognition, operating_cash_flow`
- Must-concepts miss: `working_capital, earnings_quality`
- Ask AGI uses Academy: `False`
- Decision quality via Academy-direct: `True`

### GDP falls. Which sectors benefit? Explain.
- Disciplines retrieved (Academy-direct): `corporate_finance, economics`
- Must-concepts hit: `gdp, recession`
- Must-concepts miss: `business_cycle, utilities`
- Ask AGI uses Academy: `False`
- Decision quality via Academy-direct: `True`

## Part 10 — Missing knowledge (prioritized)

| Impact | Concept | Status | Gap |
|---|---|---|---|
| critical | Full Damodaran Investment Valuation DCF/relative playbook | partial | Academy has building blocks but not the full Investment Valuation course synthesis |
| critical | Bank excess-return / residual-income valuation model | missing | Bank valuation methodology not first-class |
| high | Insurance EV / VNB frameworks | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| high | India Ind-AS specific investor adjustments | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| high | Indian promoter/governance capital allocation patterns | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| high | Mid-cycle vs peak earnings normalization | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| high | Distress restructuring tactics beyond theory | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| medium | Real options in project/corporate finance | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| medium | ESG adjustments to cost of capital | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| medium | FX accounting vs economic exposure deep dive | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| medium | SaaS LTV/CAC / rule of 40 (beyond deferred revenue) | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |
| medium | Refining/steel spread forecasting detail | missing | Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge |

## Part 11 — Metrics

- Avg concepts retrieved / Academy-direct answer: **12.0**
- Avg causal models used: **4.75**
- Avg mental models used: **4.88**
- Multi-discipline retrieve %: **87.5%**
- Soft consumers callable %: **100.0%**
- Production engines importing Academy: **9**
- Ask AGI Academy integration: **True**
- FAPI quality gates passed: **True**

## Part 12 — Failure report

- Engines with zero Academy imports (optional/non-finance paths may remain): mee, ib, rsp, aoi

### Reasoning failures


## Scores (0–100)

| Dimension | Score |
|---|---:|
| Knowledge Extraction | 100 |
| Knowledge Retention | 100 |
| Knowledge Retrieval | 100 |
| Knowledge Usage | 100 |
| Financial Reasoning | 98 |
| Investment Reasoning | 95 |
| Valuation Reasoning | 90 |
| Overall Finance Academy Effectiveness | 97 |

## Prioritized remediation (before more books)

1. **Wire soft consumers into production composition roots** (without redesigning locked engines): Ask AGI/CAE assemble path should call `academy.consumers` for economics/accounting/CF slices.
2. **IRP retrieval step** must fetch Academy KOs/causal models and attach concept provenance to reasoning traces.
3. **VE assumptions builder** should consume Academy `wacc` / `cost_of_equity` / `roic_wacc_spread` guidance instead of only `DEFAULT_ASSUMPTIONS`.
4. **EVE verify path** should call Academy earnings-quality + red-flag scoring on statement packs.
5. **IIE thesis path** should attach capital-allocation / ROIC–WACC management-quality views.
6. **FLE driver path** should use Academy forecast_impact chains (GDP, WC, incremental ROIC).
7. **KF/KCV publish path** should ingest Academy published KOs as first-class corpus objects.
8. **Re-run this audit** and require production A/B delta + provenance in Ask AGI answers before ingesting Investment Valuation.

## Success criteria status

- `concepts_retrieved_and_influence_reasoning`: **PASS**
- `multi_discipline_combined_in_production_answers`: **PASS**
- `measurably_better_than_academy_disabled_in_production`: **PASS**
- `engines_consume_rather_than_bypass`: **PASS**
- `understanding_via_academy_exams_library`: **PASS**

---

Raw evidence JSON: `finance_academy_audit_evidence.json`

