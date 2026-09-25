# AGI Tax Intelligence — build specification

Status: design, not implemented or approved for client reliance. September 25, 2026.

## Product outcome
Enable supported Indian taxpayers to understand, reconcile, plan and prepare their taxes with evidence attached to each result. Measure performance against independently reviewed cases. Do not claim universal CA replacement or measured superiority before validation. Software must not impersonate a practising CA or issue reserved professional certifications.

## Initial scope
Resident individuals with salary, bank interest and ordinary rental income, including multiple properties and ownership shares. Begin with intake and reconciliation; release tax calculations only for independently verified year-specific rules. Add investment capital gains next, then sole-proprietor business and GST workflows. NRI, HUF, trusts, companies, international tax, disputed ownership, complex losses and statutory audit cases remain explicitly unsupported until separate modules pass review.

## Current implementation gap
The existing wealthTax.js estimates ordinary tax from already-computed taxable income for FY 2025–26 / AY 2026–27. It does not compute taxable income from source records. Current TY 2026–27 is blocked pending its own verified rules. It has no client database, AIS reconciliation, tax filing integration, statutory certification or year-round monitoring. Do not relabel it a complete tax intelligence engine.

## First implementation slice
1. Client case with taxpayer identity, entity, residency, tax period, owner shares and consent. Avoid full PAN until needed; isolate client records with server authorization and database row-level rules.
2. Evidence import: structured AIS/26AS, Form 16, bank interest certificates and rental ledger. Uploaded documents remain private. OCR produces candidate values, never silently accepted facts. Every extracted item records document/page, date, currency, gross amount, tax withheld, taxpayer and confidence.
3. Reconciliation: match amounts/periods/payers across sources; separate duplicates from independently earned receipts. A bank credit is not automatically taxable income. Do not sum AIS and bank entries for the same receipt. Flag unmatched TDS, missing rent, conflicting ownership and incomplete periods.
4. Case readiness: missing evidence, unsupported tax heads, unresolved mismatches, applicable rule version and next action. Missing inputs stay unknown; no default zero taxes.
5. Review export: reconciled ledger, source links, proposed classifications, open issues and a calculation trace. No filing or payment is triggered by exporting a case.

## Calculation architecture
- Deterministic calculations with decimal arithmetic and statutory rounding. LLM explains results and proposes classifications; it does not invent rates or calculate the authoritative liability.
- Rule registry keyed by jurisdiction, entity, residency, tax year, effective date and transaction class. Store official source, retrieval date, reviewer, version and tests. AY and TY labels must never be conflated.
- Income-head computations before regime comparison. Keep eligibility, deductions, losses, rebates, surcharge, cess, credits and interest as separate traceable steps.
- Scenario engine compares baseline and permitted alternatives after eligibility checks. Show tax, cash cost, lock-in, risk, assumptions and evidence. No guaranteed savings or arbitrary reassignment of income between relatives.
- Unsupported or uncertain classifications yield review-required findings instead of authoritative numbers.

## Later modules
- Investment tax ledger: trade lots, holding periods, corporate actions, capital-gain classifications, loss set-off, carry-forward and broker/AIS reconciliation.
- Rental/property intelligence: legal ownership, rental classification, municipal taxes, interest, transfers and capital-gain exemption eligibility.
- Business/GST: books, permitted expenses, depreciation, invoices, input-credit reconciliation, return preparation, TDS/TCS and applicability checks. Rate and threshold rules are separately verified.
- Compliance calendar: deadlines based on actual case applicability and current official extensions. Persistent scheduled service, delivery logs and explicit notification preferences.
- Filing: supported official schemas or authorized intermediary integration, preflight validation, taxpayer review/authorization, submission receipt and amendment history. No claim that direct government API access already exists.
- Professional handoff: share a specific case only with client consent; create a narrow review task and evidence pack. Statutory audits/certificates require the appropriately authorized practising professional.

## Release gates
- Independently prepared expected results spanning boundary amounts, year transitions, joint ownership, duplicate receipts, missing credits, losses and unsupported cases.
- No material unexplained liability difference in the supported benchmark. Publish coverage and failures; no invented accuracy percentage.
- Reconciliation tests must prove zero double-counted receipts and correct preservation of unresolved items in benchmark fixtures.
- Cross-client isolation, upload access, encrypted storage, deletion, retention, audit logs and authorized sharing verified before real client data.
- No client-facing definitive result when material evidence is missing, rule verification is pending or the case is out of scope.
- Every filing requires taxpayer authorization and a retained receipt. Every required certification remains a professional action.

## Definition of success
Track calculation accuracy, missed/false discrepancy rates, unsupported-case routing, preparation time, reviewed savings actually eligible, and cost per completed supported case. The promise is dependable tax work within stated coverage; professional independence is evaluated case by case.

## Official reference points checked
- https://www.incometax.gov.in/iec/foportal/help/ca/servicesavailable — statutory form filing and CA digital-signature workflow.
- https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-tax-forms — transition between the old Act's forms and tax-year-specific forms; certain certificates remain CA certifications.
- https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/register-e-filing-ca — CA filing role for returns, audits and statutory forms.
- https://tutorial.gst.gov.in/downloads/news/welcome_kit_for_new_taxpyers.pdf — GST compliance/practitioner overview. Actual rates, deadlines and case eligibility require separate verification.
