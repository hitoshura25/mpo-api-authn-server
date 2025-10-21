#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { generateWebClient } from './lib/generator.js';

const server = new Server(
  {
    name: 'webauthn-client-generator',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'generate_web_client',
        description: 'Generate a complete WebAuthn web client with Docker Compose stack (PostgreSQL, Redis, WebAuthn Server) using auto-generated secure passwords. Includes Playwright E2E tests and production-ready Express server using @vmenon25/mpo-webauthn-client library.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: "Where to create the web client directory with complete Docker stack (e.g., './web-client')",
              default: './web-client'
            },
            framework: {
              type: 'string',
              enum: ['vanilla', 'react', 'vue'],
              description: 'Web framework to use',
              default: 'vanilla'
            },
            server_url: {
              type: 'string',
              description: 'Envoy Gateway URL (entry point for zero-trust stack) - default: http://localhost:8000',
              default: 'http://localhost:8000'
            },
            forward_port: {
              type: 'number',
              description: 'Port to forward for the web client dev server (local machine)',
              default: 8082
            },
            relying_party_id: {
              type: 'string',
              description: 'Relying Party ID for WebAuthn (default: localhost)',
              default: 'localhost'
            },
            relying_party_name: {
              type: 'string',
              description: 'Relying Party Name for WebAuthn (default: WebAuthn Demo)',
              default: 'WebAuthn Demo'
            },
            // Infrastructure port customization
            postgres_host_port: {
              type: 'number',
              description: 'Host port for PostgreSQL (default: 5432)',
              default: 5432
            },
            redis_host_port: {
              type: 'number',
              description: 'Host port for Redis (default: 6379)',
              default: 6379
            },
            gateway_host_port: {
              type: 'number',
              description: 'Host port for Envoy Gateway (default: 8000)',
              default: 8000
            },
            gateway_admin_port: {
              type: 'number',
              description: 'Host port for Envoy admin interface (default: 9901)',
              default: 9901
            },
            // Jaeger tracing ports (always included)
            jaeger_ui_port: {
              type: 'number',
              description: 'Host port for Jaeger UI (default: 16686)',
              default: 16686
            },
            jaeger_collector_http_port: {
              type: 'number',
              description: 'Host port for Jaeger collector HTTP (default: 14268)',
              default: 14268
            },
            jaeger_collector_grpc_port: {
              type: 'number',
              description: 'Host port for Jaeger collector gRPC (default: 14250)',
              default: 14250
            },
            jaeger_otlp_grpc_port: {
              type: 'number',
              description: 'Host port for Jaeger OTLP gRPC (default: 4317)',
              default: 4317
            },
            jaeger_otlp_http_port: {
              type: 'number',
              description: 'Host port for Jaeger OTLP HTTP (default: 4318)',
              default: 4318
            },
            jaeger_agent_compact_port: {
              type: 'number',
              description: 'Host port for Jaeger agent compact thrift UDP (default: 6831)',
              default: 6831
            },
            jaeger_agent_binary_port: {
              type: 'number',
              description: 'Host port for Jaeger agent binary thrift UDP (default: 6832)',
              default: 6832
            },
            jaeger_agent_config_port: {
              type: 'number',
              description: 'Host port for Jaeger agent config HTTP (default: 5778)',
              default: 5778
            }
          },
          required: ['project_path'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'generate_web_client':
        return await generateWebClient(args as any);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error: any) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing ${name}: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('WebAuthn Client Generator MCP server running on stdio');
}

run().catch(console.error);
