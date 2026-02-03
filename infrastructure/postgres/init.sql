-- =============================================================================
-- Project Aether - PostgreSQL Initialization
-- =============================================================================
-- This script runs when the PostgreSQL container is first created.
-- It sets up the database, extensions, and initial schema requirements.
--
-- Constitution: Principle IV - State
-- PostgreSQL provides durable persistence for state snapshots and recovery.

-- =============================================================================
-- Extensions
-- =============================================================================

-- UUID generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Better JSON querying
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- Schema
-- =============================================================================
-- Note: Actual tables are managed by Alembic migrations.
-- This file only sets up extensions and any database-level configuration.

-- =============================================================================
-- Database Configuration
-- =============================================================================

-- Set default timezone to UTC
ALTER DATABASE aether SET timezone TO 'UTC';

-- Optimize for our workload
ALTER DATABASE aether SET random_page_cost = 1.1;  -- SSD storage
ALTER DATABASE aether SET effective_io_concurrency = 200;  -- SSD storage

-- =============================================================================
-- Roles (Optional - for production multi-user setup)
-- =============================================================================

-- Application role (read/write)
-- CREATE ROLE aether_app WITH LOGIN PASSWORD 'app_password';
-- GRANT CONNECT ON DATABASE aether TO aether_app;
-- GRANT USAGE ON SCHEMA public TO aether_app;

-- Read-only role (for analytics/dashboards)
-- CREATE ROLE aether_readonly WITH LOGIN PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE aether TO aether_readonly;
-- GRANT USAGE ON SCHEMA public TO aether_readonly;

-- =============================================================================
-- Logging
-- =============================================================================

-- Log slow queries (>1 second) for optimization
-- ALTER DATABASE aether SET log_min_duration_statement = 1000;

-- =============================================================================
-- Verification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Aether database initialized successfully';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_trgm';
    RAISE NOTICE 'Run Alembic migrations to create tables: alembic upgrade head';
END $$;
