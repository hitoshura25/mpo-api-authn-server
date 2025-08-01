-- Initial WebAuthn secure storage schema
-- Creates tables for encrypted user and credential data

-- Users table with encrypted data
CREATE TABLE webauthn_users_secure (
    user_handle_hash CHAR(64) PRIMARY KEY,
    username_hash CHAR(64) UNIQUE NOT NULL,
    encrypted_user_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Credentials table with encrypted data
CREATE TABLE webauthn_credentials_secure (
    credential_id_hash CHAR(64) PRIMARY KEY,
    user_handle_hash CHAR(64) NOT NULL REFERENCES webauthn_users_secure(user_handle_hash) ON DELETE CASCADE,
    encrypted_credential_data TEXT NOT NULL,
    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance (on hashes only)
CREATE INDEX idx_webauthn_users_secure_username ON webauthn_users_secure(username_hash);
CREATE INDEX idx_webauthn_credentials_secure_user ON webauthn_credentials_secure(user_handle_hash);

-- Comments for documentation
COMMENT ON TABLE webauthn_users_secure IS 'Stores WebAuthn user data with application-level encryption';
COMMENT ON TABLE webauthn_credentials_secure IS 'Stores WebAuthn credentials with application-level encryption';
COMMENT ON COLUMN webauthn_users_secure.user_handle_hash IS 'SHA-256 hash of user handle for indexing';
COMMENT ON COLUMN webauthn_users_secure.username_hash IS 'SHA-256 hash of username for indexing';
COMMENT ON COLUMN webauthn_users_secure.encrypted_user_data IS 'AES-256-GCM encrypted user account data';
COMMENT ON COLUMN webauthn_credentials_secure.credential_id_hash IS 'SHA-256 hash of credential ID for indexing';
COMMENT ON COLUMN webauthn_credentials_secure.encrypted_credential_data IS 'AES-256-GCM encrypted credential data';
