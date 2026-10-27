-- ==============================================================================
-- 02_create_tables.sql
-- SismoWatch: Table DDL with constraints, indices and foreign keys
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. ESQUEMA RAW (BRONZE)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.usgs_earthquakes_raw (
    id VARCHAR(64) PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_id VARCHAR(128) NOT NULL,
    source_feed VARCHAR(512) NOT NULL,
    http_status INTEGER NOT NULL DEFAULT 200
);

CREATE TABLE IF NOT EXISTS raw.ingestion_metrics (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(128) NOT NULL,
    feed_url VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL, -- SUCCESS, EMPTY, ERROR
    events_extracted INTEGER NOT NULL DEFAULT 0,
    response_time_ms FLOAT NOT NULL DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 2. ESQUEMA STAGING (SILVER)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.usgs_earthquakes_staging (
    event_id VARCHAR(64) PRIMARY KEY,
    magnitude DOUBLE PRECISION,
    mag_type VARCHAR(32),
    place VARCHAR(512),
    event_time TIMESTAMPTZ NOT NULL,
    updated_time TIMESTAMPTZ NOT NULL,
    tsunami INTEGER NOT NULL DEFAULT 0,
    sig INTEGER,
    status VARCHAR(64),
    event_type VARCHAR(64),
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    url VARCHAR(1024),
    source_execution_id VARCHAR(128) NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.quarantine_events (
    quarantine_id SERIAL PRIMARY KEY,
    raw_event_id VARCHAR(64),
    execution_id VARCHAR(128) NOT NULL,
    raw_payload JSONB NOT NULL,
    rejection_reason TEXT NOT NULL,
    failed_rules JSONB NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 3. ESQUEMA CURATED (GOLD)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.events (
    event_id VARCHAR(64) PRIMARY KEY,
    magnitude DOUBLE PRECISION NOT NULL,
    mag_type VARCHAR(32),
    place VARCHAR(512) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    updated_time TIMESTAMPTZ NOT NULL,
    tsunami BOOLEAN NOT NULL DEFAULT FALSE,
    sig INTEGER,
    status VARCHAR(64),
    event_type VARCHAR(64),
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    severity_level VARCHAR(32) NOT NULL, -- LOW, MODERATE, HIGH, CRITICAL
    url VARCHAR(1024),
    ingestion_batch_id VARCHAR(128) NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_events_time ON curated.events(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_curated_events_mag ON curated.events(magnitude DESC);
CREATE INDEX IF NOT EXISTS idx_curated_events_coords ON curated.events(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_curated_events_tsunami ON curated.events(tsunami) WHERE tsunami = TRUE;

CREATE TABLE IF NOT EXISTS curated.daily_kpis (
    kpi_date DATE PRIMARY KEY,
    total_events INTEGER NOT NULL DEFAULT 0,
    max_magnitude DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_magnitude DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    tsunami_alerts_count INTEGER NOT NULL DEFAULT 0,
    active_regions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    mag_distribution_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curated.daily_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    report_date DATE NOT NULL,
    executive_summary TEXT NOT NULL,
    metrics_json JSONB NOT NULL,
    ai_model VARCHAR(64) NOT NULL,
    generation_status VARCHAR(64) NOT NULL, -- AI_GENERATED, DETERMINISTIC_FALLBACK
    tokens_used INTEGER DEFAULT 0,
    latency_ms FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON curated.daily_reports(report_date DESC);

CREATE TABLE IF NOT EXISTS curated.anomaly_alerts (
    alert_id SERIAL PRIMARY KEY,
    alert_type VARCHAR(64) NOT NULL, -- MAGNITUDE_SPIKE, SEISMIC_SWARM, SPATIAL_CLUSTER
    region VARCHAR(255) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    z_score DOUBLE PRECISION NOT NULL,
    event_count INTEGER NOT NULL,
    avg_magnitude DOUBLE PRECISION NOT NULL,
    explanation TEXT NOT NULL,
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_created ON curated.anomaly_alerts(created_at DESC);

CREATE TABLE IF NOT EXISTS curated.quality_metrics (
    metric_id SERIAL PRIMARY KEY,
    execution_id VARCHAR(128) NOT NULL,
    rules_evaluated INTEGER NOT NULL,
    rules_passed INTEGER NOT NULL,
    rules_failed INTEGER NOT NULL,
    quality_score DOUBLE PRECISION NOT NULL,
    total_records_processed INTEGER NOT NULL,
    valid_records_count INTEGER NOT NULL,
    quarantined_records_count INTEGER NOT NULL,
    freshness_delay_minutes FLOAT DEFAULT 0.0,
    status VARCHAR(32) NOT NULL, -- PASSED, BLOCKED
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_metrics_created ON curated.quality_metrics(created_at DESC);

-- ------------------------------------------------------------------------------
-- 4. ESQUEMA AUTH
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth.audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth.users(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 5. ASIGNAR PERMISOS EXPLÍCITOS A LOS ROLES
-- ------------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO ingest_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw TO ingest_user;

GRANT SELECT ON ALL TABLES IN SCHEMA raw TO transform_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO transform_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA staging TO transform_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA curated TO transform_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA curated TO transform_user;

GRANT SELECT ON ALL TABLES IN SCHEMA curated TO api_user;
GRANT SELECT ON staging.quarantine_events TO api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO api_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO api_user;
