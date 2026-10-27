-- ==============================================================================
-- 01_init_schemas_roles.sql
-- SismoWatch: Schemas creation and Least Privilege RBAC in PostgreSQL
-- ==============================================================================

-- 1. Crear esquemas de la arquitectura Medallion + Auth
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS auth;

-- 2. Crear roles de servicio con mínimo privilegio si no existen
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ingest_user') THEN
        CREATE USER ingest_user WITH PASSWORD 'ingest_secret_2026';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'transform_user') THEN
        CREATE USER transform_user WITH PASSWORD 'transform_secret_2026';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'api_user') THEN
        CREATE USER api_user WITH PASSWORD 'api_secret_2026';
    END IF;
END $$;

-- 3. Privilegios para ingest_user (Capa Bronze / raw)
GRANT USAGE ON SCHEMA raw TO ingest_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE ON TABLES TO ingest_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT USAGE, SELECT ON SEQUENCES TO ingest_user;

-- 4. Privilegios para transform_user (Capa Silver y Gold / staging y curated)
GRANT USAGE ON SCHEMA raw TO transform_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO transform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO transform_user;

GRANT USAGE ON SCHEMA staging TO transform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL PRIVILEGES ON TABLES TO transform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL PRIVILEGES ON SEQUENCES TO transform_user;

GRANT USAGE ON SCHEMA curated TO transform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT ALL PRIVILEGES ON TABLES TO transform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT ALL PRIVILEGES ON SEQUENCES TO transform_user;

-- 5. Privilegios para api_user (Consumo restringido)
-- Solo lectura en curated
GRANT USAGE ON SCHEMA curated TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO api_user;

-- Lectura/escritura en auth para usuarios y sesiones
GRANT USAGE ON SCHEMA auth TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT USAGE, SELECT ON SEQUENCES TO api_user;

-- Lectura específica en staging.quarantine_events (solo rol admin en backend)
GRANT USAGE ON SCHEMA staging TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO api_user;

-- Lectura para monitor de pipeline (conteo Bronze y métricas de ingesta)
GRANT USAGE ON SCHEMA raw TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO api_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO api_user;
