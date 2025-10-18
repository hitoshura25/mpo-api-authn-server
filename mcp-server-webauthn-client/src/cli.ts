#!/usr/bin/env node

import { generateWebClient } from './lib/generator.js';
import { parseArgs } from 'util';

// Parse command line arguments
const { values } = parseArgs({
  options: {
    path: {
      type: 'string',
      short: 'p',
      default: './web-client'
    },
    server: {
      type: 'string',
      short: 's',
      default: 'http://localhost:8080'
    },
    port: {
      type: 'string',
      short: 'P',
      default: '8082'
    },
    framework: {
      type: 'string',
      short: 'f',
      default: 'vanilla'
    },
    help: {
      type: 'boolean',
      short: 'h',
      default: false
    }
  },
  allowPositionals: false
});

// Show help message
if (values.help) {
  console.log(`
WebAuthn Client Generator - CLI

Generate a complete WebAuthn web client that connects to an existing webauthn-server instance.

USAGE:
  npx @vmenon25/mcp-server-webauthn-client [OPTIONS]

OPTIONS:
  -p, --path <path>         Directory to create web client (default: ./web-client)
  -s, --server <url>        WebAuthn server URL (default: http://localhost:8080)
  -P, --port <port>         Client dev server port (default: 8082)
  -f, --framework <name>    Framework: vanilla|react|vue (default: vanilla)
  -h, --help               Show this help message

EXAMPLES:
  # Generate vanilla TypeScript client
  npx @vmenon25/mcp-server-webauthn-client

  # Custom path and server URL
  npx @vmenon25/mcp-server-webauthn-client \\
    --path ./auth-client \\
    --server http://localhost:9000

  # Custom client port
  npx @vmenon25/mcp-server-webauthn-client \\
    --path ./web-client \\
    --port 3000

NEXT STEPS (after generation):
  1. cd <path>
  2. npm install
  3. npm run build
  4. npm start
  5. Open http://localhost:<port>

For more information:
  https://github.com/hitoshura25/mpo-api-authn-server/tree/main/mcp-server-webauthn-client
`);
  process.exit(0);
}

// Validate framework
const validFrameworks = ['vanilla', 'react', 'vue'];
if (values.framework && !validFrameworks.includes(values.framework)) {
  console.error(`❌ Error: Invalid framework '${values.framework}'`);
  console.error(`   Valid options: ${validFrameworks.join(', ')}`);
  process.exit(1);
}

// Validate port
const clientPort = parseInt(values.port || '8082', 10);
if (isNaN(clientPort) || clientPort < 1 || clientPort > 65535) {
  console.error(`❌ Error: Invalid port '${values.port}'`);
  console.error(`   Port must be a number between 1 and 65535`);
  process.exit(1);
}

// Generate web client
console.log('🚀 WebAuthn Client Generator');
console.log('═══════════════════════════════════════');
console.log(`📁 Path:      ${values.path}`);
console.log(`🌐 Server:    ${values.server}`);
console.log(`🔌 Port:      ${clientPort}`);
console.log(`🎨 Framework: ${values.framework}`);
console.log('═══════════════════════════════════════\n');

try {
  const result = await generateWebClient({
    project_path: values.path!,
    server_url: values.server,
    client_port: clientPort,
    framework: values.framework as 'vanilla' | 'react' | 'vue'
  });

  // MCP returns structured result, CLI just needs the text
  if (result.content && result.content.length > 0) {
    console.log(result.content[0].text);
  } else {
    console.log('✅ Web client generated successfully!');
  }

  process.exit(0);
} catch (error: any) {
  console.error('❌ Error generating web client:');
  console.error(error.message);
  process.exit(1);
}
