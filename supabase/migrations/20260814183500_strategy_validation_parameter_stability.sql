-- Keep the append-only validation registry aligned with the promotion gates
-- enforced by Strategy Lab. Existing evidence rows are unchanged.
alter table public.strategy_validation_evidence
  drop constraint if exists strategy_validation_evidence_gate_key_check;

alter table public.strategy_validation_evidence
  add constraint strategy_validation_evidence_gate_key_check
  check (gate_key in (
    'implementation',
    'data_freshness',
    'data_completeness',
    'point_in_time',
    'corporate_actions',
    'backtest',
    'out_of_sample',
    'transaction_costs',
    'liquidity_capacity',
    'risk',
    'parameter_stability',
    'walk_forward_paper',
    'operational_controls'
  ));
