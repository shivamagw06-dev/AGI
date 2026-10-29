# Private capital research

The `/private-markets` landing page reads a dated workbook snapshot from
`GET /api/pe/research`. The route verifies the user and AGI Plus entitlement on
the server. The snapshot is not imported into the public JavaScript bundle.
The existing transaction desk is retained under the Deal desk tab.

## Refresh

Run `scripts/import-private-capital.py <workbook.xlsx>` with a Python environment
containing openpyxl. The importer reads but never changes the original workbook.
It writes `server/data/private-capital-watchlist.json`, recording the workbook's
SHA-256 and source-sheet rows. Review the generated changes and update the dated
primary-source checks before release. This is a manual research snapshot, not a
live PitchBook/Capital IQ connection. Source verification is not inferred from a
provider label.

The current release retains the 100-company universe and reported financial
inputs. It separates space and gaming from software, keeps missing secondary
valuations null, withholds numerical management/secondary heuristics, and
withholds Info Edge core valuation until missing stake and treasury inputs are
reconciled. Three linked public announcements provide explicitly scoped context;
they do not certify the complete company record. Cumulative funding totals are
not presented because currency, financing type and source scope need review.

Shortlists persist only in the user's browser. Comparisons show up to three
companies. CSV exports contain the complete filtered universe with source rows
and snapshot date, not merely the current paginated view. CSV text is escaped
against formula injection.

## Validation

`node --test server/routes/privateCapitalResearch.test.js`

Includes universe/coverage checks, missing-value preservation, filters, CSV
escaping, anonymous and invalid-session denial, expired-membership denial,
subscription failure behaviour, and authenticated-member access.
