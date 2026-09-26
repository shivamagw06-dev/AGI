from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8100

    # Shared service auth between Node gateway and this engine
    intelligence_engine_token: str = "dev-intelligence-token"

    # AGIB Node cached APIs (agents must not call third-party APIs directly)
    agib_api_base_url: str = "http://127.0.0.1:3001"
    agib_service_token: str = ""

    # Optional LLMs for Phase 2 CIO synthesis (stub works without them)
    # Prefer Gemini when set; OpenAI remains a soft fallback.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    # Supabase / Postgres (optional — falls back to in-memory store)
    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Embedding dimension for pgvector (text-embedding-3-small)
    embedding_dimensions: int = 1536

    # WS02 Market Data Platform providers (engines never call these directly)
    indian_api_key: str = ""
    indian_api_base_url: str = "https://stock.indianapi.in"
    finnhub_api_key: str = ""
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    fmp_api_key: str = ""
    fmp_base_url: str = "https://financialmodelingprep.com/api/v3"

    # YFP V1 — Yahoo Finance Institutional Provider (secondary; MarketData adapter only)
    yahoo_provider: bool = True
    yahoo_profile: bool = True
    yahoo_financials: bool = True
    yahoo_earnings: bool = True
    yahoo_valuation: bool = True
    yahoo_ownership: bool = True
    yahoo_options: bool = True
    yahoo_financial_history: bool = True  # YAHOO_FINANCIAL_HISTORY
    yahoo_valuation_history: bool = True  # YAHOO_VALUATION_HISTORY
    yahoo_cid_enrichment: bool = True  # YAHOO_CID_ENRICHMENT
    yahoo_yfinance_fallback: bool = True  # YAHOO_YFINANCE_FALLBACK (get_income_stmt path)
    yahoo_base_url: str = "https://query1.finance.yahoo.com"
    yahoo_quote_summary_base: str = "https://query2.finance.yahoo.com"

    # E01 Macro & Regime Engine feature flags (P0 defaults)
    e01_p0: bool = True
    e01_hmm: bool = False
    e01_ml: bool = False

    # E14 Risk & Crowding Overlay feature flags (P0 defaults)
    e14_p0: bool = True
    e14_ml: bool = False
    e14_bayes: bool = False

    # E02 Factor & Style Engine feature flags (P0 defaults)
    e02_p0: bool = True
    e02_timing: bool = False
    e02_rotation: bool = False
    e02_smart_beta: bool = False
    e02_ml: bool = False

    # E03 Cross-Sectional Quant Engine feature flags (P0/M0 defaults)
    e03_p0: bool = True
    e03_parity: bool = True
    e03_composite: bool = False
    e03_xs_mode: bool = False
    e03_ml: bool = False

    # L4 Composite Intelligence feature flags (P0 Shadow defaults)
    l4_shadow: bool = True
    l4_primary: bool = False
    l4_bayes: bool = False
    l4_ml: bool = False
    l4_probability: bool = False

    # E10 Portfolio Construction feature flags (P0 defaults)
    e10_p0: bool = True
    e10_optimizer: bool = False
    e10_hrp: bool = False
    e10_mvo: bool = False

    # E13 Equity Fundamental L/S feature flags (P0 defaults)
    e13_p0: bool = True
    e13_revisions: bool = False
    e13_moat: bool = False
    e13_ml: bool = False

    # E08 Volatility & Options Intelligence feature flags (P0 defaults)
    e08_p0: bool = True
    e08_gamma: bool = False
    e08_dealer: bool = False
    e08_surface: bool = False
    e08_ml: bool = False

    # E09 CTA Trend Engine feature flags (P0 defaults)
    e09_p0: bool = True
    e09_breakout: bool = False
    e09_cross_asset: bool = False
    e09_ml: bool = False

    # E04 Statistical Arbitrage & Relative Value feature flags (P0 defaults)
    e04_p0: bool = True
    e04_kalman: bool = False
    e04_dynamic_hedge: bool = False
    e04_etf_basis: bool = False
    e04_ml: bool = False

    # E05 Event-Driven & Special Situations feature flags (P0 defaults)
    e05_p0: bool = True
    e05_deal_probability: bool = False
    e05_transcripts: bool = False
    e05_ml: bool = False

    # E11 Sentiment & Alternative Data feature flags (P0 defaults)
    e11_p0: bool = True
    e11_social: bool = False
    e11_transcripts: bool = False
    e11_llm: bool = False
    e11_ml: bool = False
    e11_altdata: bool = False

    # Validation & Backtesting platform flags (P0 defaults)
    backtest: bool = True
    live: bool = False

    # Continuous Research Evaluation platform flags (P0 defaults)
    cre: bool = True
    promotion: bool = False

    # Knowledge Intelligence Platform flags (P0 defaults)
    kip: bool = True
    kip_rag: bool = True
    kip_graph: bool = True
    kip_versioning: bool = True
    kip_ocr: bool = True
    kip_llm_summary: bool = True
    # KIP P1 — Continuous Knowledge Acquisition & House Intelligence
    kip_auto_ingest: bool = True
    kip_house_view: bool = True
    kip_prediction_tracking: bool = True
    kip_timeline: bool = True

    # Reasoning & Research Synthesis Platform flags (P0 defaults)
    rsp: bool = True
    rsp_consensus: bool = True
    rsp_contradictions: bool = True
    rsp_reasoning: bool = True

    # Research Management System flags (P0 defaults)
    rms: bool = True
    rms_review: bool = True
    rms_approval: bool = True
    rms_publish: bool = True

    # AGI Analyst Workspace flags (P0 defaults)
    aws: bool = True
    aws_copilot: bool = True
    aws_replay: bool = True
    aws_cre: bool = True

    # Investment Operations Centre flags (P0 defaults)
    ioc: bool = True
    ioc_alerts: bool = True
    ioc_reports: bool = True

    # Alpha Improvement Programme flags (research programme; not a platform)
    aip: bool = True
    aip_experiments: bool = True
    aip_promotion: bool = False

    # UI Aggregation Layer (client facade; not a platform redesign)
    ui: bool = True

    # Institutional Reasoning Pipeline (above KIP/RSP, below Ask AGI)
    irp: bool = True
    irp_learning: bool = True
    irp_validation: bool = True

    # Knowledge Foundation V1 (structured knowledge objects over KIP)
    kf: bool = True
    kf_auto_build: bool = True
    kf_company: bool = True
    kf_sector: bool = True
    kf_theme: bool = True
    kf_macro: bool = True
    kf_predictions: bool = True

    # Knowledge Corpus V1 (populate / improve KF; no KF redesign)
    kc: bool = True
    kc_auto_populate: bool = True
    kc_broker: bool = True
    kc_earnings: bool = True
    kc_gaps: bool = True
    kc_learning: bool = True
    kc_quality: bool = True

    # AGI Open Intelligence v1 (public acquisition → KC/KF; no core redesign)
    aoi: bool = True
    aoi_scheduler: bool = True
    aoi_publish: bool = True
    aoi_live_fetch: bool = False
    aoi_company_ir: bool = True
    aoi_nse: bool = True
    aoi_bse: bool = True
    aoi_rbi: bool = True
    aoi_sebi: bool = True
    aoi_mof: bool = True
    aoi_mospi: bool = True
    aoi_fred: bool = True
    aoi_imf: bool = True
    aoi_worldbank: bool = True
    aoi_pib: bool = True

    # Evidence & Verification Engine v1 (between AOI and KCV/KF; no core redesign)
    eve: bool = True
    eve_auto_verify: bool = True
    eve_gate_publish: bool = True
    eve_conflicts: bool = True
    eve_timeline: bool = True
    eve_daily_jobs: bool = True

    # Investment Intelligence Engine v1 (after EVE/KCV/KF, before reasoning; no core redesign)
    iie: bool = True
    iie_auto_analyse: bool = True
    iie_scenarios: bool = True
    iie_catalysts: bool = True
    iie_risks: bool = True
    iie_compare: bool = True

    # Forecasting & Learning Engine v1 (after IIE, before reasoning; no core redesign)
    fle: bool = True
    fle_auto_resolve: bool = True
    fle_learning: bool = True
    fle_calibration: bool = True
    fle_scenarios: bool = True

    # Market Event Engine v1 (after FLE; event backbone; no core redesign)
    mee: bool = True
    mee_auto_detect: bool = True
    mee_propagate: bool = True
    mee_impact: bool = True
    mee_similar: bool = True

    # Finance Retrieval Engine v1 (intelligence acquisition; evidence only; no core redesign)
    fre: bool = True
    fre_query_planner: bool = True
    fre_acquisition: bool = True
    fre_hybrid_search: bool = True
    fre_rerank: bool = True
    fre_evidence: bool = True
    fre_graph: bool = True
    fre_scheduler: bool = True
    fre_soft_publish_kip: bool = True
    fre_ask_agi: bool = True

    # Finance Acquisition Agent v1 (upstream live acquisition; feeds FRE; no core redesign)
    faa: bool = True
    faa_discovery: bool = True
    faa_fetch: bool = True
    faa_processing: bool = True
    faa_index: bool = True
    faa_live_fetch: bool = False
    faa_search_api: bool = True
    faa_playwright: bool = True  # headless Chromium for JS pages + free web search (soft-fail if missing)
    faa_pdf: bool = True
    faa_notify_fre: bool = True
    faa_scheduler: bool = True
    faa_max_workers: int = 6

    # Context Assembly Engine v1 (Ask AGI orchestration gateway; no core redesign)
    cae: bool = True
    cae_cache: bool = True
    cae_compress: bool = True
    cae_parallel: bool = True
    cae_ask_agi_gateway: bool = True

    # Intelligence Bus v1 (event-driven backbone; no core redesign)
    ib: bool = True
    ib_persist: bool = True
    ib_retry: bool = True
    ib_dlq: bool = True
    ib_replay: bool = True
    ib_cache_invalidate: bool = True
    ib_soft_handlers: bool = True
    ib_ask_agi_emit: bool = True

    # Valuation Engine v1 (after FLE/MEE structured intel; no core redesign)
    ve: bool = True
    ve_auto_value: bool = True
    ve_scenarios: bool = True
    ve_sensitivity: bool = True
    ve_relative: bool = True
    ve_ibus_updates: bool = True

    # FIML v1 — Financial Intelligence Model Library (shared domain models; not an engine)
    fiml: bool = True
    fiml_persist_analyses: bool = True

    # AGI Finance Academy v1 — institutional curriculum library (not an engine)
    academy: bool = True
    academy_provenance: bool = True
    academy_exams: bool = True
    academy_production: bool = True  # FAPI — production integration into locked engines
    academy_books: bool = True  # ACADEMY_BOOKS — curated book → structured knowledge
    academy_books_v3: bool = True  # ACADEMY_BOOKS_V3 — institutional knowledge transformation
    academy_validation_suite: bool = True  # AVS — demonstrate institutional knowledge (not ingest checks)
    academy_certification_suite: bool = True  # ACS — institutional intelligence certification / merge gate
    institutional_regression_suite: bool = True  # IRS — did this PR make AGIB smarter?
    evidence_intelligence_layer: bool = True  # EIL — sources / peers / history / explainable confidence
    peer_intelligence: bool = True  # PIL — how does this company compare to best/relevant peers?
    pil_peers: bool = True
    pil_history: bool = True
    pil_percentiles: bool = True
    pil_rankings: bool = True
    pil_benchmarks: bool = True
    pil_commentary: bool = True
    pil_scorecards: bool = True
    filing_intelligence: bool = True  # FIL — what do the company's own filings actually say?
    fil_statements: bool = True
    fil_notes: bool = True
    fil_segments: bool = True
    fil_guidance: bool = True
    fil_risks: bool = True
    fil_management: bool = True
    fil_history: bool = True
    fil_evidence: bool = True
    filing_diff_engine: bool = True  # FDI — what materially changed since the previous filing?
    fdi_statements: bool = True
    fdi_guidance: bool = True
    fdi_risks: bool = True
    fdi_management: bool = True
    fdi_segments: bool = True
    fdi_accounting: bool = True
    fdi_capital: bool = True
    fdi_governance: bool = True
    fdi_ownership: bool = True
    management_intelligence: bool = True  # MII — can management be trusted to compound value?
    mii_credibility: bool = True
    mii_guidance: bool = True
    mii_execution: bool = True
    mii_capital_allocation: bool = True
    mii_governance: bool = True
    mii_communication: bool = True
    mii_incentives: bool = True
    mii_succession: bool = True
    institutional_stack: bool = True  # IIS — soft FIL→FDI→MII→EIL→PIL integration
    institutional_stack_auto_chain: bool = True
    institutional_stack_ask_agi: bool = True
    institutional_stack_admin: bool = True
    accounting_intelligence: bool = True  # ACI — can the financial statements be trusted?
    aci_earnings: bool = True
    aci_cash: bool = True
    aci_accruals: bool = True
    aci_forensics: bool = True
    aci_revenue: bool = True
    aci_working_capital: bool = True
    aci_balance_sheet: bool = True
    aci_policies: bool = True
    aci_behaviour: bool = True
    portfolio_intelligence: bool = True  # PIO — does this improve this specific portfolio?
    pio_allocation: bool = True
    pio_risk: bool = True
    pio_diversification: bool = True
    pio_factors: bool = True
    pio_scenarios: bool = True
    pio_optimisation: bool = True
    pio_position_sizing: bool = True
    pio_overlap: bool = True
    pio_quality: bool = True
    causal_intelligence: bool = True  # CIG — why did this happen?
    cig_transmission: bool = True
    cig_propagation: bool = True
    cig_counterfactual: bool = True
    cig_sector_models: bool = True
    cig_portfolio_impact: bool = True
    cig_historical: bool = True
    cig_confidence: bool = True
    forecast_intelligence: bool = True  # FIE — what future paths are plausible?
    fie_scenarios: bool = True
    fie_catalysts: bool = True
    fie_triggers: bool = True
    fie_sensitivity: bool = True
    fie_expectations: bool = True
    fie_consensus: bool = True
    fie_uncertainty: bool = True
    fie_probability: bool = True
    knowledge_graph: bool = True  # IKG — what is connected?
    ikg_entity_resolution: bool = True
    ikg_supply_chain: bool = True
    ikg_ownership: bool = True
    ikg_macro: bool = True
    ikg_events: bool = True
    ikg_thesis: bool = True
    ikg_query: bool = True
    ikg_dependency: bool = True
    institutional_memory: bool = True  # ILM — what has AGIB learned over time?
    ilm_thesis: bool = True
    ilm_analyst: bool = True
    ilm_committee: bool = True
    ilm_forecast: bool = True
    ilm_portfolio: bool = True
    ilm_learning: bool = True
    ilm_accuracy: bool = True
    ilm_mistake_intelligence: bool = True
    simulation_lab: bool = True  # SSL — what happens if this decision is taken?
    ssl_scenario: bool = True
    ssl_portfolio: bool = True
    ssl_macro: bool = True
    ssl_stress: bool = True
    ssl_strategy: bool = True
    ssl_decision: bool = True
    ssl_sensitivity: bool = True
    ssl_monte_carlo: bool = True
    ssl_replay: bool = True
    decision_engine_v2: bool = True  # IDE V2 — final constitutional orchestrator (architecture frozen)
    idev2_orchestrator: bool = True
    idev2_constitution: bool = True
    idev2_weighting: bool = True
    idev2_conflicts: bool = True
    idev2_uncertainty: bool = True
    idev2_confidence: bool = True
    idev2_recommendation_gate: bool = True
    idev2_monitoring: bool = True
    idev2_audit: bool = True
    idev2_learning_hooks: bool = True
    academy_frameworks: bool = True  # ACADEMY_FRAMEWORKS
    academy_formulas: bool = True  # ACADEMY_FORMULAS
    academy_graph: bool = True  # ACADEMY_GRAPH
    academy_spreadsheets: bool = True  # ACADEMY_SPREADSHEETS — xlsx/xls/ods/csv models
    academy_books_dir: str = ""  # ACADEMY_BOOKS_DIR — personal library root
    sif: bool = True  # SIF — Sector Intelligence Framework (additive analysis lens)
    leo: bool = True  # LEO — Live Evidence Orchestrator (additive evidence acquisition)
    cid: bool = True  # CID — Company Intelligence Dossier (permanent institutional memory)

    # DVC V1 — Data Validation & Consensus (Market Data platform layer; not an engine)
    dvc: bool = True
    dvc_multi_provider: bool = True
    dvc_auto_attach_cid: bool = True
    dvc_provider_priority: str = ""  # e.g. "official_exchange:1,indianapi:2,finnhub:3,fmp:4,yahoo:5"

    # ECP V1 — Evidence Completion Pipeline (orchestration layer; not an engine)
    ecp: bool = True
    ecp_before_irp: bool = True
    ecp_before_gate: bool = True

    # Ask AGI Intelligence Construction V2 + Answer Construction V3 (soft orchestration; not engines)
    intelligence_construction: bool = True
    ask_agi_intelligence_v2: bool = True
    answer_construction_v3: bool = True
    ask_agi_answer_construction_v3: bool = True

    # Editorial Intelligence Layer — provider is the writer only; AGIB remains the brain.
    editorial_layer: bool = True
    ask_agi_editorial_layer: bool = True
    editorial_provider: str = "openai"  # openai | gemini | claude | mistral | deepseek
    # Contradiction Reasoning Soft Layer — step-by-step conflict answers (not a top-level engine)
    contradiction_reasoning: bool = True
    ask_agi_contradiction_reasoning: bool = True
    # Institutional Reasoning Soft Policy — how to think before answering
    institutional_reasoning: bool = True
    ask_agi_institutional_reasoning: bool = True

    # Institutional Analyst Framework V1 — Answer Construction ownership (not engines)
    institutional_analysts: bool = True
    ask_agi_iaf: bool = True

    # Institutional Analyst Intelligence V1/V2 — per-analyst brain upgrade (soft; one analyst at a time)
    institutional_analyst_intelligence: bool = True
    iai_business_analyst: bool = True
    iai_business_analyst_v2: bool = True
    iai_business_analyst_v2_1: bool = True
    iai_financial_analyst: bool = True
    iai_valuation_analyst: bool = True

    # Investment Committee Intelligence V1 — deliberation / vote / minutes (not an engine)
    investment_committee_intelligence: bool = True
    ask_agi_ici: bool = True

    # Institutional Research Writer V1 — presentation/writing layer after CIO (not an engine)
    institutional_research_writer: bool = True
    ask_agi_irw: bool = True

    # AGIB Investment Decision Engine — multi-layer investment decisions (soft-wire; not an engine redesign)
    decision_engine: bool = True
    ask_agi_decision_engine: bool = True

    # Company Analysis Engine V1 — institutional company-specific reasoning (not Context Assembly)
    # Master flag COMPANY_ANALYSIS (cae remains Context Assembly). Subflags match programme brief.
    company_analysis: bool = True
    cae_financial: bool = True
    cae_sector: bool = True
    cae_business: bool = True
    cae_valuation: bool = True
    cae_investment_thesis: bool = True

    # Company Monitoring System V1 — continuous living analyst (not an engine)
    company_monitor: bool = True
    cms_auto_pipeline: bool = True
    cms_ask_agi: bool = True
    cms_research_writer: bool = True
    cms_house_view_hints: bool = True

    # Investment Office V1 — executive operating layer (not an engine)
    investment_office: bool = True
    io_morning_brief: bool = True
    io_analyst_queue: bool = True
    io_research_queue: bool = True
    io_coverage: bool = True
    io_risk_center: bool = True
    io_executive_copilot: bool = True

    # Mission Control V1 — administrator operations centre (read-only; not an engine)
    mission_control: bool = True
    mission_control_apis: bool = True
    mission_control_platforms: bool = True
    mission_control_coverage: bool = True
    mission_control_knowledge: bool = True
    mission_control_alerts: bool = True
    mission_control_events: bool = True
    mission_control_reports: bool = True

    # AGIB Intelligence Layer V2 — living institutional research (soft-wire; not FAA/FRE/CAE redesign)
    ail: bool = True
    ail_cde: bool = True
    ail_ede: bool = True
    ail_te: bool = True
    ail_pe: bool = True
    ail_cme: bool = True
    ail_el: bool = True
    ail_graph: bool = True
    ail_timeline: bool = True
    ail_ask_agi: bool = True
    ail_redis_cache: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
