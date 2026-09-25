# US Insider Activity and paste imports

Public view: `/insider-activity?country=US`. Admin paste: `/admin/insider-trades-paste?country=US`. Template: `/templates/us-insider-trades.tsv`.

Choose United States in the paste screen, paste the header and rows, Check the normalized preview, then Publish. Existing Indian formats remain available under India. Both preview and publish require a server-verified administrator session. The engine's token remains server-side.

The US parser accepts TSV or CSV with these headers (common OpenInsider-style aliases supported): Company, Ticker, Insider Name, Title, Filing Date, Trade Date, Transaction Code, Quantity, Price, Value, Owned, 10b5-1, SEC URL, Transaction ID, Derivative. Company can fall back to an explicit ticker. Required: issuer identity, insider name, filing and transaction dates including year, supported transaction code, non-zero shares. Dollar amounts are absolute USD, not thousands/millions. Blank value remains missing, not price × shares. US slash dates are month/day/year. Finviz-style dates without a year must be completed before import.

A/S/etc. do not all mean market trading. P/S are purchase/sale codes and may cover private or derivative transactions. The US flow reports P/S transactions separately from grants, exercises, tax withholding and gifts. Intelligence excludes explicitly planned transactions and explicitly identified derivatives. Unknown status remains unknown; no discretionary trading claim is made. SEC source: https://www.sec.gov/about/forms/form4data.pdf .

`ΔOwn` describes the insider's holding change, not company equity traded. It is stored separately. Bound values such as `>999%` remain text, not exact percentages. No India promoter or pledge-only sections are presented in the US view. Values use dollars; research windows use New York dates. Watchlists use separate browser storage per country, and country changes clear company selection.

US rows live in `us_insider_trades`, a separate warehouse tab initialized by the existing schema machinery. The public service never falls back to India on a US read failure. A supplied Transaction ID (scoped to issuer) is preferred; otherwise a stable composite of issuer, person, filing timestamp, trade date, code, shares, price and security identifies a transaction. Exact repeated rows collapse. Conflicting identities in a batch fail validation. Distinct but otherwise identical transactions need distinct IDs. Form 4/A amendments require reconciliation and are rejected from this simple paste path.

Malformed rows block publication of the entire batch at parsing. Existing warehouse validation and audit rules still apply on write. The UI displays inserted/updated/unchanged counts. Source links are optional and never fabricated. Pasted hyperlinks generally lose their URL, so an explicit SEC URL column is required for document links.

Validation: parser tests, real temporary warehouse write/re-paste/isolation test, India parser regressions, US data routing and signal exclusion tests, and production frontend build. No sample records are published to production. Browser visual QA remains unavailable in this session.
