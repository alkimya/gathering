-- Migration 006: Auth Users and Token Blacklist
-- Phase 1: Auth + Security Foundation
-- Creates persistent storage for user accounts and revoked tokens

-- Ensure auth schema exists
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS audit;

-- =============================================================================
-- auth.users - Persistent user accounts
-- =============================================================================

CREATE TABLE IF NOT EXISTS auth.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id VARCHAR(36) NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL,
    email_lower VARCHAR(255) GENERATED ALWAYS AS (LOWER(email)) STORED,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(72) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_email_lower ON auth.users(email_lower);
CREATE INDEX IF NOT EXISTS idx_auth_users_external_id ON auth.users(external_id);

-- Updated_at trigger (reuse public.update_updated_at if exists, otherwise create)
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_auth_users_updated_at ON auth.users;
CREATE TRIGGER update_auth_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- =============================================================================
-- auth.token_blacklist - Persisted revoked tokens
-- =============================================================================

CREATE TABLE IF NOT EXISTS auth.token_blacklist (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(36),
    reason VARCHAR(50) DEFAULT 'logout'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_token_blacklist_hash ON auth.token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON auth.token_blacklist(expires_at);

-- =============================================================================
-- audit.security_events - Security event logging (create if not exists)
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit.security_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    user_id VARCHAR(36),
    ip_address INET,
    message TEXT,
    details JSONB DEFAULT '{}',
    request_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_events_type ON audit.security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON audit.security_events(severity) WHERE severity IN ('high', 'critical');
CREATE INDEX IF NOT EXISTS idx_security_events_ip ON audit.security_events(ip_address);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON audit.security_events(created_at DESC);
