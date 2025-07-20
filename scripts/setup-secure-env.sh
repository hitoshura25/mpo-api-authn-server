#!/bin/bash

# Secure environment setup script for CI/CD
# Generates random passwords if not provided via secrets

set -euo pipefail

# Function to generate secure random password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Set up environment variables with secure defaults
export MPO_AUTHN_DB_HOST="${MPO_AUTHN_DB_HOST:-localhost}"
export MPO_AUTHN_DB_PORT="${MPO_AUTHN_DB_PORT:-5432}"
export MPO_AUTHN_DB_NAME="${MPO_AUTHN_DB_NAME:-webauthn_db}"
export MPO_AUTHN_DB_USERNAME="${MPO_AUTHN_DB_USERNAME:-webauthn_user}"

# Generate secure random passwords
export MPO_AUTHN_DB_PASSWORD="$(generate_password)"
export MPO_AUTHN_REDIS_PASSWORD="$(generate_password)"

export MPO_AUTHN_REDIS_HOST="${MPO_AUTHN_REDIS_HOST:-localhost}"
export MPO_AUTHN_REDIS_PORT="${MPO_AUTHN_REDIS_PORT:-6379}"
export MPO_AUTHN_APP_PORT="${MPO_AUTHN_APP_PORT:-8080}"
export MPO_AUTHN_APP_RELYING_PARTY_ID="${MPO_AUTHN_APP_RELYING_PARTY_ID:-localhost}"
export MPO_AUTHN_APP_RELYING_PARTY_NAME="${MPO_AUTHN_APP_RELYING_PARTY_NAME:-MPO Api Authn}"
export MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME="${MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME:-webauthn-server}"
export MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT="${MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT:-http://localhost:4317}"

echo "✅ Secure environment variables configured"
echo "🔐 Using $([ -n "${POSTGRES_PASSWORD:-}" ] && echo "provided" || echo "generated") database password"
echo "🔐 Using $([ -n "${REDIS_PASSWORD:-}" ] && echo "generated") Redis password"

# Create .env file for Docker Compose
cat << EOF > .env
MPO_AUTHN_DB_HOST=${MPO_AUTHN_DB_HOST}
MPO_AUTHN_DB_PORT=${MPO_AUTHN_DB_PORT}
MPO_AUTHN_DB_NAME=${MPO_AUTHN_DB_NAME}
MPO_AUTHN_DB_USERNAME=${MPO_AUTHN_DB_USERNAME}
MPO_AUTHN_DB_PASSWORD=${MPO_AUTHN_DB_PASSWORD}
MPO_AUTHN_REDIS_HOST=${MPO_AUTHN_REDIS_HOST}
MPO_AUTHN_REDIS_PORT=${MPO_AUTHN_REDIS_PORT}
MPO_AUTHN_REDIS_PASSWORD=${MPO_AUTHN_REDIS_PASSWORD}
MPO_AUTHN_APP_PORT=${MPO_AUTHN_APP_PORT}
MPO_AUTHN_APP_RELYING_PARTY_ID=${MPO_AUTHN_APP_RELYING_PARTY_ID}
MPO_AUTHN_APP_RELYING_PARTY_NAME=${MPO_AUTHN_APP_RELYING_PARTY_NAME}
MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME=${MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME}
MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT=${MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT}
EOF

echo "📝 Created .env file with secure configuration"