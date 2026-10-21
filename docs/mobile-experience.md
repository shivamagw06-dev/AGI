# Mobile experience

Phone layout applies up to 700px; desktop uses existing components and layout.

- Shared compact header, collapsible market strip, five-item bottom navigation and scrollable full menu.
- Simple semantic tables gain labeled card presentation. Matrices remain scrollable. Editable tables are excluded; `data-mobile-table="off"` opts out.
- India portfolio cards prioritize return and chart. Detail pages show the continuous portfolio ledger before supporting historical factor research. Supporting research and collection details are expandable.
- USA portfolio and signal-history filters use a native modal bottom sheet with keyboard dismissal.
- Early Radar uses paginated cards with stage, direction, dated trigger and quote observations, before-cost directional change and preserved stale warnings. Phone initially selects Triggered; all stages remain available.
- Shared touch targets, readable form text, safe-area spacing and article readability.

Validation: production build passed. Browser checks at 320px and 390px covered public India/USA portfolios, portfolio detail, filters and recorded radar data. Main menu opens and Escape closes. Research, IPO, institutions, global markets and Live Desk layouts were checked at 320px without page-level horizontal overflow. Desktop India portfolio checked at 1440px; bottom navigation hidden and original grid retained.

Some research content was unavailable in the local preview due to missing local service configuration; this was a layout check, not verification of all authenticated data or every admin workflow. No backend, strategy, portfolio allocation or return calculations changed. Not deployed as part of this build.
