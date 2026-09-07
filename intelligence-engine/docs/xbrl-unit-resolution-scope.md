# Scope: resolve declared units from NSE XBRL

Read-only scope. No code path changed, no production write, guard stays off.

## Correction carried into this design

An earlier note of mine proposed reading `unitRef` **and `decimals`** to
establish scale. That was wrong about `decimals` and the error is worth stating
plainly, because acting on it would have corrupted every value it touched.

`decimals` is a **precision assertion**, not a scale factor. It says how many
digits are reliable, not what the number must be multiplied by. Reliance's
quarterly revenue in a real filing on disk:

```xml
<in-bse-fin:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-7">
  2407150000000.00
</in-bse-fin:RevenueFromOperations>
```

The value is already full scale: ₹2,407,150,000,000. `decimals="-7"` says the
last seven digits are not significant. Multiplying by 10⁻⁷ yields 240,715 —
which reads as a perfectly plausible figure in crore and is silently wrong. That
is the same class of defect this whole effort exists to remove.

Scale in XBRL comes from `ix:nonFraction/@scale`, which is an **Inline XBRL**
attribute. Whether it applies here is an empirical question, answered below.

## What NSE actually serves

Surveyed all 113 filings on disk across 12 companies
(`financial_statements_engine/data/raw/*/*.xbrl`):

| | |
| --- | --- |
| document format | **plain XBRL (`<xbrli:xbrl>`) — 113 of 113** |
| Inline XBRL (`ix:nonFraction`) | **0 of 113** |
| taxonomy | BSE `in-bse-fin` 2020-03-31, SEBI roles |

**There is no `scale` attribute to read.** Inline XBRL is not in use on this
path, so `sign` and `format`/`ixt:` transformations do not arise either. Values
are reported at full scale in the unit's currency, which is the plain-XBRL
contract.

This simplifies the work considerably and should be stated in the design rather
than defended against: the scope must still *detect* Inline XBRL and fail closed
if it ever appears, but must not invent handling for attributes this feed does
not send.

## Units actually present

```
iso4217:INR                 104 filings     money, absolute rupees
xbrli:pure                   94 filings     ratios
xbrli:shares                 57 filings     share counts
iso4217:INR / xbrli:shares  104 filings     compound (xbrli:divide) — per share
```

`decimals` observed: `-7` (57,888 facts), `-6`, `-5`, `-4`, `INF`, `2`, `0`.
Had any of these been treated as scale, values would be wrong by 10⁴–10⁷.

## Design

### 1. Unit resolution

Parse `<xbrli:unit>` into `id → measures`, then resolve each fact's `unitRef`
against it. Three outcomes, and only the first is usable as aggregate money:

| resolved | treatment |
| --- | --- |
| single `iso4217:XXX` | money in that currency, absolute, full scale |
| `xbrli:shares`, `xbrli:pure` | not money — never scale-tested, never converted |
| `xbrli:divide` (compound) | per-share or per-unit — **fail closed**, not an aggregate |
| missing / unknown `unitRef` | **fail closed** |
| currency other than INR | **fail closed** — no cross-currency conversion here |

`INRPerShare` appears in all 104 money filings and carries EPS. Treating it as
INR would put a per-share figure in an aggregate column, so compound units fail
closed by construction rather than by a currency check.

### 2. What is captured per fact

Recorded, never re-derived:

- `raw_value` — the literal text as filed
- `normalised_value` — the value after unit conversion, with the factor applied
- `unit_ref`, `unit_measures`, `currency`
- `decimals` — **stored as precision metadata only**; the code must have no
  arithmetic path that reads it
- `scale`, `sign`, `format` — captured when Inline XBRL is present; absent here
- `source_url` — the filing's `xbrl_url`
- `provider` — which upstream answered
- `transform` — the ordered list of operations applied, so the normalised value
  can be re-derived from the raw one and checked

### 3. Provenance paths kept separate

`earnings_intelligence_p21` has two paths that must never share a unit method:

| path | unit basis | method |
| --- | --- | --- |
| NSE XBRL fact | `unitRef` → `iso4217:INR` | `declared` |
| integrated-summary lakhs fallback (`xbrl.py:405–413`) | the comment "often in lakhs" | `assumed`, and fails closed |

The fallback multiplies by 100,000 on an assumption. It cannot produce a
declared unit and must not be allowed to look like one. Its existing flag
`scaled_from_integrated_lakhs` is set at `xbrl.py:412` and read nowhere; it
becomes part of the recorded transform evidence.

### 4. `financial_connector` provider identity

The connector declares `"NSE IND-AS XBRL (primary) / Yahoo Finance quoteSummary
(failover)"` and stamps every row `financial_connector` regardless of which
answered. The scope records the provider per row. Without it a row's unit basis
is not recoverable, and the two providers do not share a convention.

### 5. Fail closed

Missing, compound, unsupported, non-INR, or Inline-XBRL-with-scale all resolve
to *unknown*, which routes to `scale_guard` in `report` and later `isolate`.
Unknown must never fall through to "assume canonical" — that fallback is the
origin of this entire defect.

## Compatibility and migration

**Nothing is removed.** The existing regex parser keeps working and keeps its
outputs. Unit resolution is added alongside it and populates new fields only.

1. **Shadow.** Resolve units and record them without changing any stored value.
   Compare the resolved unit against what the row currently carries and report
   disagreement. No behaviour change.
2. **Declare, forward only.** New writes carry `sys_unit_method='declared'` with
   the resolved currency. Stored rows are untouched.
3. **Guard to report**, then `isolate`, once the shadow disagreement rate is
   understood.
4. **Backfill stored rows** — separate, later, and only against the audited run
   tables in PR #774 so it reverses against the exact rows it touched.

Steps 1–3 are reversible by configuration. Step 4 is the only one that changes a
stored value and is out of this scope.

## Quantified impact

Rows from the two undocumented sources, from the full census of 102,822 rows:

| | annual | quarterly | total |
| --- | ---: | ---: | ---: |
| rows from these sources | 2,009 | 9,472 | **11,481** |
| values look like absolute rupees | 1,997 | 9,310 | **11,307** |
| already at a smaller scale | 12 | 162 | **174** |

**Would become `declared`:** every fact arriving by the NSE XBRL path with a
resolvable `unitRef` — all 104 money filings surveyed carry `iso4217:INR`, so
the rate on that path is expected to be near total.

**Would remain unknown:** facts from the lakhs fallback, compound-unit facts
(EPS via `INRPerShare`), `pure` and `shares` facts, and everything from the
Yahoo failover, which carries no unit metadata at all.

**Would change value:** 11,307 rows hold values that look like absolute rupees
and would be divided by 1e6 once declared — *if and only if* they are confirmed
to have come by the XBRL path. That confirmation does not exist for stored rows,
which is why this scope records provider and path going forward and defers the
backfill.

**The 174 rows matter more than their count.** They are already at a smaller
scale, and a blanket rupee default would divide them by a million in the wrong
direction. They are the reason the unit is resolved per fact rather than per
source.

## Fixtures required

Built from the real filings on disk, plus synthetic cases for what they do not
contain:

| fixture | asserts |
| --- | --- |
| INR aggregate, `decimals="-7"` | value unchanged by `decimals`; converts by unit only |
| INR aggregate, `decimals="INF"` | precision absent is not a scale signal |
| `xbrli:shares` | share counts never converted, never scale-tested |
| `xbrli:pure` | ratios never converted |
| `iso4217:INR / xbrli:shares` (EPS) | compound unit fails closed, not read as INR |
| negative value (`capex`, `cff`) | sign preserved through conversion |
| lakh path (`×100_000`) | recorded as `assumed`, fails closed, flag preserved |
| crore-scaled input | converts by unit, not by magnitude |
| missing `unitRef` | fails closed |
| `unitRef` naming an undefined unit | fails closed, does not default |
| two facts, same concept, conflicting units | fails closed rather than picking |
| non-INR currency | fails closed, no conversion attempted |
| Inline XBRL with `scale` | detected and failed closed until explicitly supported |

## What this scope does not do

No stored value is changed, no row retired or quarantined, the guard stays off,
and PR #774 stays draft. Establishing a declared unit is a prerequisite for the
remediation, not the remediation.
