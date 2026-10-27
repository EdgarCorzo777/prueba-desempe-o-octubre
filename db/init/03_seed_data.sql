-- ==============================================================================
-- 03_seed_data.sql
-- SismoWatch: Seed initial users with bcrypt hashes and default baseline data
-- ==============================================================================

-- 1. Insertar usuarios iniciales (Admin y Viewer)
-- Contraseñas hasheadas con bcrypt (factor de trabajo 12)
-- Admin: admin@sismowatch.internal / AdminSecure2026!*
-- Viewer: viewer@sismowatch.internal / ViewerSecure2026!*
INSERT INTO auth.users (email, password_hash, full_name, role, is_active)
VALUES 
    (
        'admin@sismowatch.internal',
        '$2b$12$x.HDijBi146mdAm9NbZiIeUbugUioQMVjlDVWhofpt1bt6wrHScYy',
        'Administrador SismoWatch',
        'admin',
        TRUE
    ),
    (
        'viewer@sismowatch.internal',
        '$2b$12$lZmgQuw74Ogy9iJ8neI3zOBZdfaVYOVQFUMYjvdij7dQzGZxRmiT6',
        'Operador Viewer',
        'viewer',
        TRUE
    )
ON CONFLICT (email) DO NOTHING;

-- 2. Registro inicial en métricas de calidad para arranque del sistema
INSERT INTO curated.quality_metrics (
    execution_id,
    rules_evaluated,
    rules_passed,
    rules_failed,
    quality_score,
    total_records_processed,
    valid_records_count,
    quarantined_records_count,
    freshness_delay_minutes,
    status,
    details
)
VALUES (
    'INIT_SYSTEM_SEED',
    6,
    6,
    0,
    100.0,
    0,
    0,
    0,
    0.0,
    'PASSED',
    '{"system_status": "Ready for initial ingestion"}'::jsonb
)
ON CONFLICT DO NOTHING;
