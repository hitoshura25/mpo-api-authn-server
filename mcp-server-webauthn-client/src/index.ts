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
            client_port: {
              type: 'number',
              description: 'Port for the web client dev server',
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
