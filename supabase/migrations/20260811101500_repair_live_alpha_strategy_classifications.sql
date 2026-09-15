-- Forward-only repair for environments where the original classification
-- expansion did not apply. All values are research classifications only.
alter table public.live_alpha_signals
  drop constraint if exists live_alpha_signals_classification_check;

alter table public.live_alpha_signals
  add constraint live_alpha_signals_classification_check check (classification in (
    'positive_research_candidate', 'negative_research_candidate', 'neutral', 'filtered',
    'abnormal_accumulation_candidate', 'abnormal_distribution_candidate',
    'upside_opening_breakout_candidate', 'downside_opening_breakout_candidate', 'invalid_opening_range',
    'negative_shock_rebound_candidate', 'positive_shock_pullback_candidate',
    'market_stress_filtered', 'event_volume_filtered', 'trend_filtered',
    'long_buildup_candidate', 'short_buildup_candidate',
    'short_covering_candidate', 'long_unwinding_candidate'
  ));

comment on constraint live_alpha_signals_classification_check on public.live_alpha_signals is
  'Research-only classifications emitted by the five Live Alpha engines.';
