-- KAIP / IKO storage — Sprint 6.2 institutional knowledge model.

CREATE TABLE IF NOT EXISTS raw_events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    collector_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    company_symbol TEXT,
    payload_json TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    checksum TEXT NOT NULL,
    validation_status TEXT,
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_events_source_checksum
    ON raw_events(source, company_symbol, checksum, timestamp);

CREATE TABLE IF NOT EXISTS knowledge_objects (
    object_id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    company_symbol TEXT,
    sector_key TEXT,
    market_key TEXT,
    version INTEGER NOT NULL,
    previous_object_id TEXT,
    changed_fields_json TEXT NOT NULL DEFAULT '[]',
    change_summary TEXT,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    entity_refs_json TEXT NOT NULL,
    source_event_ids_json TEXT NOT NULL,
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ko_subject_type_version
    ON knowledge_objects(object_type, subject_key, version DESC);

CREATE INDEX IF NOT EXISTS idx_ko_symbol_type
    ON knowledge_objects(company_symbol, object_type, version DESC);

CREATE TABLE IF NOT EXISTS company_profiles (
    company_symbol TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    entity_refs_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    as_of TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_symbol_asof
    ON market_snapshots(company_symbol, as_of DESC);

CREATE TABLE IF NOT EXISTS corporate_events (
    event_object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    event_date TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corp_events_symbol
    ON corporate_events(company_symbol, event_date DESC);

CREATE TABLE IF NOT EXISTS corporate_actions (
    action_object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    ex_date TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corp_actions_symbol
    ON corporate_actions(company_symbol, ex_date DESC);

CREATE TABLE IF NOT EXISTS financial_statements (
    statement_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    statement_type TEXT NOT NULL,
    period_end TEXT,
    knowledge_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_financials_symbol
    ON financial_statements(company_symbol, statement_type, period_end DESC);

CREATE TABLE IF NOT EXISTS ownership (
    ownership_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    as_of TEXT,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ownership_symbol
    ON ownership(company_symbol, version DESC);

CREATE TABLE IF NOT EXISTS analyst_consensus (
    consensus_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyst_symbol
    ON analyst_consensus(company_symbol, version DESC);

CREATE TABLE IF NOT EXISTS news_events (
    news_id TEXT PRIMARY KEY,
    company_symbol TEXT,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    event_date TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_symbol
    ON news_events(company_symbol, event_date DESC);

CREATE TABLE IF NOT EXISTS sector_knowledge (
    sector_key TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_knowledge (
    market_key TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    knowledge_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_events (
    learning_id TEXT PRIMARY KEY,
    company_symbol TEXT,
    sector_key TEXT,
    market_key TEXT,
    category TEXT NOT NULL,
    category_label TEXT,
    importance TEXT NOT NULL,
    confidence TEXT,
    field_name TEXT NOT NULL,
    previous_value_json TEXT,
    new_value_json TEXT,
    delta_json TEXT,
    materiality TEXT NOT NULL,
    materiality_score REAL NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    observation TEXT,
    evidence TEXT,
    affected_json TEXT NOT NULL DEFAULT '[]',
    object_type TEXT,
    object_id TEXT,
    source_event_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_learning_symbol
    ON learning_events(company_symbol, created_at DESC);

CREATE TABLE IF NOT EXISTS relationship_edges (
    edge_id TEXT PRIMARY KEY,
    from_type TEXT NOT NULL,
    from_key TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    to_type TEXT NOT NULL,
    to_key TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_from
    ON relationship_edges(from_type, from_key);

CREATE TABLE IF NOT EXISTS entity_registry (
    company_symbol TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    company_name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    indexes_json TEXT NOT NULL DEFAULT '[]',
    peers_json TEXT NOT NULL DEFAULT '[]',
    clients_json TEXT NOT NULL DEFAULT '[]',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS publication_log (
    publication_id TEXT PRIMARY KEY,
    envelope_json TEXT NOT NULL,
    published_at TEXT NOT NULL
);

-- Sprint 6.3 Institutional Learning Engine collections

CREATE TABLE IF NOT EXISTS sector_learning (
    learning_id TEXT PRIMARY KEY,
    sector TEXT NOT NULL,
    sector_key TEXT NOT NULL,
    observation TEXT NOT NULL,
    supporting_companies_json TEXT NOT NULL,
    field_name TEXT,
    importance TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sector_learning_key
    ON sector_learning(sector_key, created_at DESC);

CREATE TABLE IF NOT EXISTS market_learning (
    learning_id TEXT PRIMARY KEY,
    theme TEXT NOT NULL,
    observation TEXT NOT NULL,
    beneficiaries_json TEXT NOT NULL,
    supporting_sectors_json TEXT NOT NULL,
    historical_confidence TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_market_learning_theme
    ON market_learning(theme, created_at DESC);

CREATE TABLE IF NOT EXISTS relationship_changes (
    change_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    field_name TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_changes_symbol
    ON relationship_changes(company_symbol, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_conflicts (
    conflict_id TEXT PRIMARY KEY,
    company_symbol TEXT,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    previous_assumption TEXT NOT NULL,
    new_observation TEXT NOT NULL,
    field_name TEXT NOT NULL,
    previous_value_json TEXT,
    new_value_json TEXT,
    object_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conflicts_symbol
    ON knowledge_conflicts(company_symbol, created_at DESC);

CREATE TABLE IF NOT EXISTS learning_timeline (
    entry_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    year INTEGER NOT NULL,
    label TEXT NOT NULL,
    detail TEXT NOT NULL,
    field_name TEXT NOT NULL,
    importance TEXT NOT NULL,
    object_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_symbol_year
    ON learning_timeline(company_symbol, year, created_at);

CREATE TABLE IF NOT EXISTS institutional_memory (
    memory_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    narrative TEXT NOT NULL,
    category TEXT NOT NULL,
    importance TEXT NOT NULL,
    source_learning_fields_json TEXT NOT NULL,
    object_id TEXT,
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_symbol
    ON institutional_memory(company_symbol, created_at DESC);

CREATE TABLE IF NOT EXISTS sector_signals (
    signal_id TEXT PRIMARY KEY,
    sector_key TEXT NOT NULL,
    field_name TEXT NOT NULL,
    direction INTEGER NOT NULL,
    company_symbol TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sector_signals
    ON sector_signals(sector_key, field_name, direction, created_at DESC);

CREATE TABLE IF NOT EXISTS market_theme_signals (
    signal_id TEXT PRIMARY KEY,
    theme TEXT NOT NULL,
    sector TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_theme_signals
    ON market_theme_signals(theme, created_at DESC);

-- Sprint 6.4 KRIG storage

CREATE TABLE IF NOT EXISTS knowledge_bundle_cache (
    cache_key TEXT PRIMARY KEY,
    bundle_json TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bundle_cache_expires
    ON knowledge_bundle_cache(expires_at);

CREATE TABLE IF NOT EXISTS retrieval_logs (
    log_id TEXT PRIMARY KEY,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrieval_logs_created
    ON retrieval_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS freshness_registry (
    object_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT,
    age_seconds INTEGER,
    sla_label TEXT,
    current_as_of TEXT,
    PRIMARY KEY (object_type, subject_key)
);

CREATE TABLE IF NOT EXISTS confidence_registry (
    object_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    confidence_pct REAL NOT NULL,
    label TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (object_type, subject_key)
);

CREATE TABLE IF NOT EXISTS knowledge_dependencies (
    subject TEXT PRIMARY KEY,
    depends_on_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retrieval_metrics (
    metric_key TEXT PRIMARY KEY,
    query_type TEXT NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    misses INTEGER NOT NULL DEFAULT 0,
    total_latency_ms REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
