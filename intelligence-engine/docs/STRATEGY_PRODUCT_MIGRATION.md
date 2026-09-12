# Strategy product migration manifest

Product-facing names do not own evidence. Each resolves to one immutable
research-family definition; only that canonical definition may advance through
the validation gates. Scanner availability, confidence labels, candidate counts
and comparable-observation counts cannot promote a strategy.

| Product identity | Canonical definition | Purpose |
| --- | --- | --- |
| Value | `relative_value_v1` | Relative valuation research |
| Quality | `quality_v1` | Financial quality research |
| Dividend Quality | `value_quality_v1` | Income and value-quality research |
| Growth | `growth_v1` | Growth-factor research |
| Momentum / Technical Trend | `momentum_v1` | Price-leadership research |
| Conviction | `consensus_revisions_v1` | Expectations-revision research |
| Stress | `stress_v1` | Downside-risk research |
| Pairs | `pairs_v1` | Relative-value pair research |
| Alpha / Live Alpha confluence / Equity Opportunities | `multi_factor_v1` | Research shortlist overlay |
| Sector Rotation | `sector_rotation_v1` | Sector-allocation research |
| Opening Range | `opening_range_v1` | Intraday breakout research |
| Intraday Reversion | `mean_reversion_v1` | Intraday dislocation research |
| Volume / Flow Anomaly | `volume_anomaly_v1` | Liquidity and flow research |
| Derivatives Positioning | `derivatives_positioning_v1` | Derivatives positioning research |

All mappings are fail-closed at `DEFINED`, `RESEARCH_ONLY`, and
`capital_allowed=false` until the central registry records the required
point-in-time, costed, out-of-sample, paper and live evidence.
