# Step 0: unit evidence for `earnings_intelligence_p21` and `financial_connector`

Read-only investigation. No code path was changed and nothing was applied.

**Conclusion: neither source may be given a source-wide default unit.** Both are
demonstrably non-uniform, in the code and in the stored data. The correct
treatment is to fail closed, not to pick a default.

---

## `earnings_intelligence_p21`

### Upstream provider and endpoint

| | |
| --- | --- |
| provider | **NSE India** — corporate filings |
| discovery | `https://www.nseindia.com/api/corporates-financial-results` (`discovery.py:17`), `api/top-corp-info` (`discovery.py:20`) |
| document | IND-AS / Integrated Filing **XBRL**, fetched from the filing's `xbrl_url` (`xbrl.py:357–366`) |
| transport | `download_xbrl` via `nse_session_opener`, Referer `https://www.nseindia.com/` (`xbrl.py:78–90`) |

### Unit and currency at ingestion

**Not read.** `_facts_for_context` (`xbrl.py:104–122`) matches each tag with a
regex and takes the first numeric run of text that follows:

```python
vm = re.match(r"\s*([-+]?[0-9]*\.?[0-9]+)", rest)
```

It filters on `contextRef` only. There is no reference to `unitRef`, `decimals`,
`scale`, `iso4217` or any currency measure anywhere in the file. Whatever
magnitude the filer wrote is taken verbatim, and the declared currency is never
checked.

XBRL carries both `unitRef` and `decimals` on every numeric fact. This parser
discards both. That is the mechanism by which units vary by filing.

### Does the unit vary?

**Yes, by filing — and the code says so in a comment.** When XBRL is thin there
is a fallback (`xbrl.py:405–413`):

```python
# Integrated feed often in lakhs
inc["revenue_from_operations"] = float(summary["income"]) * 100_000.0
out["scaled_from_integrated_lakhs"] = True
```

"often in lakhs" is an assumption stated as a heuristic, applied to one field
(`revenue_from_operations`) on one path. So the unit varies **by field and by
path within a single filing**, not only between filings.

### Transformations before warehouse insertion

1. `×100_000` on the lakhs fallback path, `revenue_from_operations` only.
2. `_derive_income` recomputes dependent income fields from the scaled value.
3. `store.py:_write_hd` maps pack fields into a `pit_record` payload. **No unit
   field is carried.**

### Raw payload unit metadata and importer assumptions

The pipeline generates exactly one piece of unit provenance —
`scaled_from_integrated_lakhs` — and **drops it**. `grep` finds the flag set at
`xbrl.py:412` and read nowhere. It never reaches the warehouse row.

The importer's assumption is therefore implicit and unrecorded: *whatever the
filer wrote is already correct*.

### Stored evidence of non-uniformity

Annual revenue, 63 rows, magnitude histogram:

```
10^4:1  10^5:10  |  10^8:12  10^9:10  10^10:9  10^11:18  10^12:3
```

Two clusters with a four-order gap between them. **17.5% sit below 1e8**, which
is impossible if the source were uniformly rupees. Quarterly shows the same
shape: 330 of 5,095 rows (6.5%) below 1e8.

---

## `financial_connector`

### Upstream provider and endpoint

The connector declares two providers under one label
(`institutional_data/connectors/financials.py:31`):

```python
official_source = "NSE IND-AS XBRL (primary) / Yahoo Finance quoteSummary (failover)"
```

| | |
| --- | --- |
| primary | NSE IND-AS XBRL — filer-dependent magnitude, as above |
| failover | `https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}` (`financials.py:16`) |

### Unit and currency at ingestion

**Not read, for either provider.** The only value handling is Yahoo's wrapper
shape (`financials.py:482–484`):

```python
if isinstance(v, dict) and "raw" in v:
    return float(v["raw"])
```

No unit, scale, currency or multiplier logic exists in the file.

### Does the unit vary?

**Yes, by filing and by which provider answered.** A row's magnitude depends on
whether NSE or Yahoo served it, and the NSE branch is filer-dependent on top of
that. The two providers do not share a convention.

Worse, **which provider answered is not recorded**. Every row is stamped
`source="financial_connector"` (`financials.py:315`, `336`, `359`, `376`)
regardless of origin, so the provider identity is erased at the point of write
and cannot be recovered from a stored row.

### Stored evidence of non-uniformity

Annual revenue, 1,860 rows:

```
10^4:16  10^5:18  10^6:5  10^7:9  |  10^8:27  10^9:588  10^10:978  10^11:192  10^12:27
```

48 rows (2.6%) below 1e8; quarterly 63 of 4,327 (1.5%). Small but real clusters
at 10^4–10^7 alongside a bulk at 10^9–10^10.

---

## Why neither gets a source-wide default

`units.SOURCE_DEFAULT_UNIT` contains neither source, so `resolve_unit` falls
through to "treat the value as already canonical" and stores raw rupees in a
column meaning INR million. That is the live defect.

Adding `"rupee"` for either one would fix the majority and **newly corrupt the
minority cluster** — the rows already in millions or lakhs would be divided by a
million and become wrong in the opposite direction. Roughly 11 annual
`earnings_intelligence_p21` rows and 48 annual `financial_connector` rows sit in
that cluster today.

A default is a claim of uniformity. The documentation does not support it for
either source, and the stored data contradicts it.

## Recommended treatment: fail closed

1. **Do not add SOURCE_DEFAULT_UNIT entries for either source.**
2. Read the unit that is already in the data. NSE XBRL carries `unitRef` and
   `decimals` on every fact; the parser discards them. Reading them makes the
   unit *declared* rather than assumed, per row, which is what the canonical
   rules already ask for.
3. Persist `scaled_from_integrated_lakhs` — the flag exists and is thrown away.
4. Record which provider answered in `financial_connector`, so a row's origin is
   recoverable.
5. Until 2–4 land, route rows from undocumented sources to `report` and then
   `isolate` via `scale_guard`, rather than letting them become canonical by
   default. `resolve_unit`'s fallback should be the guard's input, not silent
   acceptance.

## Evidence index

| claim | evidence |
| --- | --- |
| NSE endpoints | `earnings_intelligence/discovery.py:17,20`; `xbrl.py:78–90,357–366` |
| XBRL units ignored | `xbrl.py:104–122` — no `unitRef`/`decimals`/`iso4217` in file |
| lakhs assumption | `xbrl.py:405–413` |
| unit flag dropped | `xbrl.py:412` set; no other reference in repo |
| two providers, one label | `institutional_data/connectors/financials.py:31` |
| Yahoo endpoint | `financials.py:16` |
| no unit handling | `financials.py` — only `v["raw"]` unwrap at `482–484` |
| provider identity erased | `financials.py:315,336,359,376` |
| neither source defaulted | `institutional_warehouse/units.py` `SOURCE_DEFAULT_UNIT` |
| non-uniform magnitudes | census of 69,156 + 33,666 rows, histograms above |
