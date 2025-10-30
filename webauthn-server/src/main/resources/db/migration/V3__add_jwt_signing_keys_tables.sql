-- Migration: Add JWT signing keys tables for key rotation support
-- Purpose: Enable JWT key rotation with PostgreSQL persistence and audit trail
-- Date: 2025-10-24
-- Version: V3

-- ============================================================================
-- Table: jwt_signing_keys
-- Description: Stores JWT signing keys with encrypted private keys
-- ============================================================================
CREATE TABLE jwt_signing_keys (
    -- Primary identification
    key_id VARCHAR(64) PRIMARY KEY,

    -- Key material
    private_key_pem TEXT NOT NULL,                     -- Encrypted RSA private key (PEM format)
    public_key_pem TEXT NOT NULL,                      -- RSA public key (PEM format) - not encrypted
    algorithm VARCHAR(16) NOT NULL DEFAULT 'RS256',    -- Signing algorithm (RS256, RS384, RS512)
    key_size INTEGER NOT NULL DEFAULT 2048,            -- Key size in bits (2048, 3072, 4096)

    -- Lifecycle state
    status VARCHAR(16) NOT NULL,                       -- PENDING, ACTIVE, RETIRED, DELETED

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),       -- When key was generated
    activated_at TIMESTAMP,                            -- When key became ACTIVE
    retired_at TIMESTAMP,                              -- When key became RETIRED
    expires_at TIMESTAMP,                              -- When key should be deleted

    -- Metadata (JSONB for flexibility)
    metadata JSONB,                                    -- { reason, rotation_policy, rotated_by, etc. }

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'ACTIVE', 'RETIRED', 'DELETED'))
    -- Partial unique index created separately below to enforce single ACTIVE key
);

-- Partial unique index to ensure only one ACTIVE key exists at a time
CREATE UNIQUE INDEX single_active_key ON jwt_signing_keys(status) WHERE (status = 'ACTIVE');

-- Indexes for performance
CREATE INDEX idx_jwt_keys_status ON jwt_signing_keys(status);
CREATE INDEX idx_jwt_keys_expires ON jwt_signing_keys(expires_at) WHERE status = 'RETIRED';
CREATE INDEX idx_jwt_keys_created ON jwt_signing_keys(created_at DESC);

-- ============================================================================
-- Table: jwt_key_audit_log
-- Description: Audit trail for all JWT key lifecycle events
-- ============================================================================
CREATE TABLE jwt_key_audit_log (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(64) NOT NULL,                       -- FK to jwt_signing_keys
    event VARCHAR(32) NOT NULL,                        -- GENERATED, ACTIVATED, RETIRED, DELETED, MANUAL_ROTATION
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,                                    -- Additional context (admin_user, reason, etc.)

    -- Foreign key constraint
    CONSTRAINT fk_key_id FOREIGN KEY (key_id) REFERENCES jwt_signing_keys(key_id) ON DELETE CASCADE
);

-- Indexes for querying audit events
CREATE INDEX idx_jwt_audit_key_id ON jwt_key_audit_log(key_id);
CREATE INDEX idx_jwt_audit_timestamp ON jwt_key_audit_log(timestamp DESC);
CREATE INDEX idx_jwt_audit_event ON jwt_key_audit_log(event);

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE jwt_signing_keys IS 'Stores JWT signing keys with lifecycle management for key rotation';
COMMENT ON COLUMN jwt_signing_keys.key_id IS 'Unique identifier for the key (e.g., webauthn-2025-10-24)';
COMMENT ON COLUMN jwt_signing_keys.private_key_pem IS 'Encrypted private key in PEM format (encrypted at application level)';
COMMENT ON COLUMN jwt_signing_keys.public_key_pem IS 'Public key in PEM format (not encrypted, published in JWKS)';
COMMENT ON COLUMN jwt_signing_keys.status IS 'Lifecycle state: PENDING (grace period), ACTIVE (signing), RETIRED (verifying only), DELETED (removed)';
COMMENT ON COLUMN jwt_signing_keys.metadata IS 'Flexible JSONB field for rotation metadata (reason, policy, previous_key_id, etc.)';
COMMENT ON INDEX single_active_key IS 'Partial unique index ensuring exactly one ACTIVE key at any time';

COMMENT ON TABLE jwt_key_audit_log IS 'Audit trail for all JWT key lifecycle events';
COMMENT ON COLUMN jwt_key_audit_log.event IS 'Event type: GENERATED, ACTIVATED, RETIRED, DELETED, MANUAL_ROTATION';
