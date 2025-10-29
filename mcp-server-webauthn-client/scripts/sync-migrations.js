#!/usr/bin/env node

/**
 * Sync Migrations from WebAuthn Server to MCP Templates
 *
 * This script maintains single source of truth for database migrations
 * by copying them from webauthn-server to MCP templates during build.
 *
 * Source: webauthn-server/src/main/resources/db/migration/
 * Destination: mcp-server-webauthn-client/src/templates/vanilla/docker/
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Source: webauthn-server migrations (single source of truth)
const serverMigrations = path.join(__dirname, '../../webauthn-server/src/main/resources/db/migration');

// Destination: MCP templates
const templateDest = path.join(__dirname, '../src/templates/vanilla/docker');

// Copy V3 JWT migration
const v3Migration = path.join(serverMigrations, 'V3__add_jwt_signing_keys_tables.sql');
const destFile = path.join(templateDest, 'jwt-migration.sql.hbs');

console.log('📋 Syncing migrations from server to MCP templates...');
console.log(`   Source: ${v3Migration}`);
console.log(`   Dest:   ${destFile}`);

if (!fs.existsSync(v3Migration)) {
  console.error('❌ Source migration file not found!');
  console.error(`   Expected: ${v3Migration}`);
  process.exit(1);
}

// Ensure destination directory exists
if (!fs.existsSync(templateDest)) {
  console.error('❌ Destination directory not found!');
  console.error(`   Expected: ${templateDest}`);
  process.exit(1);
}

// Copy the file
try {
  fs.copyFileSync(v3Migration, destFile);
  console.log('✅ Migration synced successfully');
} catch (error) {
  console.error('❌ Failed to copy migration file:', error.message);
  process.exit(1);
}
