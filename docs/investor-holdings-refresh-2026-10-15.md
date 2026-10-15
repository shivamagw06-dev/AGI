# Holdings refresh — 15 October 2026

Checked all 271 profiles linked by the four Trendlyne directories: 61 India individuals, 123 India institutions, 71 US individuals and 16 US institutions. Also checked both retained historical routes, for 273 checked profiles in total. Refreshed 259 source extracts; 14 Indian profiles returned no latest-quarter table. Prior snapshots remain dated and visible in those cases. Two older directory profiles remain available for historical continuity, giving 273 routes.

India data comes from 172 downloaded CSV exports. Values are absolute rupees in the export and converted to crore by dividing by 10,000,000. Ownership history remains in source order. September 2026 filings are incomplete: `Filing Awaited` is unknown, not zero or an exit. Rows missing current ownership display their latest available historical ownership period.

US data comes from 87 rendered holdings tables because CSV exports omitted security names. Only outer holdings rows are imported; nested holder tables are excluded to avoid double counting. The source's aggregate quantities are retained, including potentially overlapping holder names. These are not independently reconciled positions. US tables do not supply per-security filing dates and can retain historical securities. Company ownership percentages must not be read as portfolio weights. Large extracts are marked partial when capped or below the source count.

Existing official SEC/fund filings remain the default where available. A separate source selector opens the newly checked Trendlyne extract. The snapshots are never combined. Price-based values require the exact snapshot fingerprint; stale valuations are withheld until the scheduled refresh prices the new holdings.

The companion JSON records every checked source and outcome. Raw inbound downloads and DOM captures are retained locally under `/private/tmp/agi-holdings-refresh` and Downloads. No login credentials are included.
