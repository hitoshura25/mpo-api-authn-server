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
      default: 'http://localhost:8000'
    },
    'forward-port': {
      type: 'string',
      short: 'P',
      default: '8082'
    },
    framework: {
      type: 'string',
      short: 'f',
      default: 'vanilla'
    },
    // Infrastructure ports
    'postgres-host-port': {
      type: 'string',
      default: '5432'
    },
    'redis-host-port': {
      type: 'string',
      default: '6379'
    },
    'gateway-host-port': {
      type: 'string',
      default: '8000'
    },
    'gateway-admin-port': {
      type: 'string',
      default: '9901'
    },
    // Jaeger ports
    'jaeger-ui-port': {
      type: 'string',
      default: '16686'
    },
    'jaeger-collector-http-port': {
      type: 'string',
      default: '14268'
    },
    'jaeger-collector-grpc-port': {
      type: 'string',
      default: '14250'
    },
    'jaeger-otlp-grpc-port': {
      type: 'string',
      default: '4317'
    },
    'jaeger-otlp-http-port': {
      type: 'string',
      default: '4318'
    },
    'jaeger-agent-compact-port': {
      type: 'string',
      default: '6831'
    },
    'jaeger-agent-binary-port': {
      type: 'string',
      default: '6832'
    },
    'jaeger-agent-config-port': {
      type: 'string',
      default: '5778'
    },
    // JWT Key Rotation Configuration (HOCON format)
    'jwt-rotation-interval': {
      type: 'string',
      default: '180d'
    },
    'jwt-grace-period': {
      type: 'string',
      default: '1h'
    },
    'jwt-retention': {
      type: 'string',
      default: '1h'
    },
    'jwks-cache-duration-seconds': {
      type: 'string',
      default: '300'
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
  -p, --path <path>                      Directory to create web client (default: ./web-client)
  -s, --server <url>                     Envoy Gateway URL (zero-trust entry point, default: http://localhost:8000)
  -P, --forward-port <port>              Port to forward for web client dev server (default: 8082)
  -f, --framework <name>                 Framework: vanilla|react|vue (default: vanilla)
  -h, --help                             Show this help message

INFRASTRUCTURE PORT CUSTOMIZATION (to avoid conflicts with existing services):
  --postgres-host-port <port>            PostgreSQL host port (default: 5432)
  --redis-host-port <port>               Redis host port (default: 6379)
  --gateway-host-port <port>             Envoy Gateway host port (default: 8000)
  --gateway-admin-port <port>            Envoy admin host port (default: 9901)

JAEGER TRACING PORT CUSTOMIZATION:
  --jaeger-ui-port <port>                Jaeger UI port (default: 16686)
  --jaeger-collector-http-port <port>    Jaeger collector HTTP (default: 14268)
  --jaeger-collector-grpc-port <port>    Jaeger collector gRPC (default: 14250)
  --jaeger-otlp-grpc-port <port>         Jaeger OTLP gRPC (default: 4317)
  --jaeger-otlp-http-port <port>         Jaeger OTLP HTTP (default: 4318)
  --jaeger-agent-compact-port <port>     Jaeger agent compact thrift UDP (default: 6831)
  --jaeger-agent-binary-port <port>      Jaeger agent binary thrift UDP (default: 6832)
  --jaeger-agent-config-port <port>      Jaeger agent config HTTP (default: 5778)

JWT KEY ROTATION CONFIGURATION (HOCON duration format):
  --jwt-rotation-interval <duration>     Time between key rotations (default: 180d)
  --jwt-grace-period <duration>          Grace period before retiring old key (default: 1h)
  --jwt-retention <duration>             How long to keep retired keys (default: 1h)
  --jwks-cache-duration-seconds <sec>    JWKS endpoint cache duration (default: 300)

EXAMPLES:
  # Generate vanilla TypeScript client
  npx @vmenon25/mcp-server-webauthn-client

  # Custom path and server URL
  npx @vmenon25/mcp-server-webauthn-client \\
    --path ./auth-client \\
    --server http://localhost:9000

  # Custom forward port
  npx @vmenon25/mcp-server-webauthn-client \\
    --path ./web-client \\
    --forward-port 3000

  # Avoid port conflicts with existing infrastructure
  npx @vmenon25/mcp-server-webauthn-client \\
    --postgres-host-port 5433 \\
    --redis-host-port 6380 \\
    --gateway-host-port 8001 \\
    --jaeger-ui-port 16687

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

// Validate and parse all ports
const validatePort = (portStr: string | undefined, name: string, defaultValue: string): number => {
  const port = parseInt(portStr || defaultValue, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    console.error(`❌ Error: Invalid ${name} '${portStr}'`);
    console.error(`   Port must be a number between 1 and 65535`);
    process.exit(1);
  }
  return port;
};

const forwardPort = validatePort(values['forward-port'], 'forward port', '8082');
const postgresHostPort = validatePort(values['postgres-host-port'], 'postgres-host-port', '5432');
const redisHostPort = validatePort(values['redis-host-port'], 'redis-host-port', '6379');
const gatewayHostPort = validatePort(values['gateway-host-port'], 'gateway-host-port', '8000');
const gatewayAdminPort = validatePort(values['gateway-admin-port'], 'gateway-admin-port', '9901');
const jaegerUiPort = validatePort(values['jaeger-ui-port'], 'jaeger-ui-port', '16686');
const jaegerCollectorHttpPort = validatePort(values['jaeger-collector-http-port'], 'jaeger-collector-http-port', '14268');
const jaegerCollectorGrpcPort = validatePort(values['jaeger-collector-grpc-port'], 'jaeger-collector-grpc-port', '14250');
const jaegerOtlpGrpcPort = validatePort(values['jaeger-otlp-grpc-port'], 'jaeger-otlp-grpc-port', '4317');
const jaegerOtlpHttpPort = validatePort(values['jaeger-otlp-http-port'], 'jaeger-otlp-http-port', '4318');
const jaegerAgentCompactPort = validatePort(values['jaeger-agent-compact-port'], 'jaeger-agent-compact-port', '6831');
const jaegerAgentBinaryPort = validatePort(values['jaeger-agent-binary-port'], 'jaeger-agent-binary-port', '6832');
const jaegerAgentConfigPort = validatePort(values['jaeger-agent-config-port'], 'jaeger-agent-config-port', '5778');
const jwksCacheDurationSeconds = validatePort(values['jwks-cache-duration-seconds'], 'jwks-cache-duration-seconds', '300');

// Generate web client
console.log('🚀 WebAuthn Client Generator');
console.log('═══════════════════════════════════════');
console.log(`📁 Path:         ${values.path}`);
console.log(`🌐 Server:       ${values.server}`);
console.log(`🔌 Forward Port: ${forwardPort}`);
console.log(`🎨 Framework:    ${values.framework}`);
console.log('═══════════════════════════════════════\n');

try {
  const result = await generateWebClient({
    project_path: values.path!,
    server_url: values.server,
    forward_port: forwardPort,
    framework: values.framework as 'vanilla' | 'react' | 'vue',
    // Infrastructure ports
    postgres_host_port: postgresHostPort,
    redis_host_port: redisHostPort,
    gateway_host_port: gatewayHostPort,
    gateway_admin_port: gatewayAdminPort,
    // Jaeger ports
    jaeger_ui_port: jaegerUiPort,
    jaeger_collector_http_port: jaegerCollectorHttpPort,
    jaeger_collector_grpc_port: jaegerCollectorGrpcPort,
    jaeger_otlp_grpc_port: jaegerOtlpGrpcPort,
    jaeger_otlp_http_port: jaegerOtlpHttpPort,
    jaeger_agent_compact_port: jaegerAgentCompactPort,
    jaeger_agent_binary_port: jaegerAgentBinaryPort,
    jaeger_agent_config_port: jaegerAgentConfigPort,
    // JWT Key Rotation (HOCON format)
    jwt_rotation_interval: values['jwt-rotation-interval'],
    jwt_grace_period: values['jwt-grace-period'],
    jwt_retention: values['jwt-retention'],
    jwks_cache_duration_seconds: jwksCacheDurationSeconds
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
