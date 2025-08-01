#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execSync, spawn } from 'child_process';
import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';

const server = new Server(
  {
    name: 'webauthn-dev-tools',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Development tools for the WebAuthn project
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'run_tests',
        description: 'Run project tests with optional filters',
        inputSchema: {
          type: 'object',
          properties: {
            testPattern: {
              type: 'string',
              description: 'Test pattern or class name to run (optional)',
            },
            testType: {
              type: 'string',
              enum: ['unit', 'integration', 'all'],
              description: 'Type of tests to run',
              default: 'all'
            }
          },
          required: [],
        },
      },
      {
        name: 'build_project',
        description: 'Build the project with Gradle',
        inputSchema: {
          type: 'object',
          properties: {
            clean: {
              type: 'boolean',
              description: 'Clean build (gradle clean build)',
              default: false
            },
            skipTests: {
              type: 'boolean', 
              description: 'Skip tests during build',
              default: false
            }
          },
          required: [],
        },
      },
      {
        name: 'start_dev_server',
        description: 'Start the development server with dependencies',
        inputSchema: {
          type: 'object',
          properties: {
            withDependencies: {
              type: 'boolean',
              description: 'Start with PostgreSQL and Redis dependencies',
              default: true
            },
            port: {
              type: 'number',
              description: 'Port to run the server on',
              default: 8080
            }
          },
          required: [],
        },
      },
      {
        name: 'stop_dev_server',
        description: 'Stop the development server and dependencies',
        inputSchema: {
          type: 'object',
          properties: {},
          required: [],
        },
      },
      {
        name: 'analyze_code_structure',
        description: 'Analyze the project code structure and organization',
        inputSchema: {
          type: 'object',
          properties: {
            path: {
              type: 'string',
              description: 'Specific path to analyze (default: src/main/kotlin)',
              default: 'src/main/kotlin'
            },
            depth: {
              type: 'number',
              description: 'Maximum depth for analysis',
              default: 3
            }
          },
          required: [],
        },
      },
      {
        name: 'check_dependencies',
        description: 'Check project dependencies and their status',
        inputSchema: {
          type: 'object',
          properties: {
            outdated: {
              type: 'boolean',
              description: 'Check for outdated dependencies',
              default: false
            }
          },
          required: [],
        },
      },
      {
        name: 'generate_api_clients',
        description: 'Generate API client libraries',
        inputSchema: {
          type: 'object',
          properties: {
            language: {
              type: 'string',
              enum: ['typescript', 'java', 'python', 'csharp', 'all'],
              description: 'Client language to generate',
              default: 'all'
            }
          },
          required: [],
        },
      },
      {
        name: 'database_status',
        description: 'Check database connection and schema status',
        inputSchema: {
          type: 'object',
          properties: {},
          required: [],
        },
      },
      {
        name: 'view_logs',
        description: 'View application logs',
        inputSchema: {
          type: 'object',
          properties: {
            lines: {
              type: 'number',
              description: 'Number of log lines to show',
              default: 50
            },
            level: {
              type: 'string',
              enum: ['DEBUG', 'INFO', 'WARN', 'ERROR', 'ALL'],
              description: 'Log level filter',
              default: 'ALL'
            }
          },
          required: [],
        },
      },
      {
        name: 'test_api_endpoint',
        description: 'Test a specific API endpoint',
        inputSchema: {
          type: 'object',
          properties: {
            endpoint: {
              type: 'string',
              description: 'API endpoint to test (e.g., /health, /register/start)',
            },
            method: {
              type: 'string',
              enum: ['GET', 'POST', 'PUT', 'DELETE'],
              description: 'HTTP method',
              default: 'GET'
            },
            body: {
              type: 'string',
              description: 'Request body (JSON string)'
            },
            baseUrl: {
              type: 'string',
              description: 'Base URL for the API',
              default: 'http://localhost:8080'
            }
          },
          required: ['endpoint'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'run_tests':
        return await runTests(args);
      case 'build_project':
        return await buildProject(args);
      case 'start_dev_server':
        return await startDevServer(args);
      case 'stop_dev_server':
        return await stopDevServer(args);
      case 'analyze_code_structure':
        return await analyzeCodeStructure(args);
      case 'check_dependencies':
        return await checkDependencies(args);
      case 'generate_api_clients':
        return await generateApiClients(args);
      case 'database_status':
        return await databaseStatus(args);
      case 'view_logs':
        return await viewLogs(args);
      case 'test_api_endpoint':
        return await testApiEndpoint(args);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
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

async function runTests(args = {}) {
  const { testPattern, testType = 'all' } = args;
  
  let command = './gradlew :webauthn-server:test';
  
  if (testPattern) {
    command += ` --tests "*${testPattern}*"`;
  }
  
  try {
    const output = execSync(command, { 
      encoding: 'utf8',
      cwd: process.cwd(),
      timeout: 300000 // 5 minutes
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `Tests completed successfully!\n\nOutput:\n${output}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Test execution failed:\n${error.stdout || error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function buildProject(args = {}) {
  const { clean = false, skipTests = false } = args;
  
  let command = './gradlew';
  if (clean) command += ' clean';
  command += ' :webauthn-server:build';
  if (skipTests) command += ' -x test';
  
  try {
    const output = execSync(command, { 
      encoding: 'utf8',
      cwd: process.cwd(),
      timeout: 600000 // 10 minutes
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `Build completed successfully!\n\nOutput:\n${output}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Build failed:\n${error.stdout || error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function startDevServer(args = {}) {
  const { withDependencies = true, port = 8080 } = args;
  
  try {
    if (withDependencies) {
      // Start dependencies first
      execSync('docker-compose -f webauthn-server/docker-compose.yml up -d postgres redis', {
        encoding: 'utf8',
        cwd: process.cwd()
      });
      
      // Wait a moment for services to start
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    
    // Start the application (non-blocking)
    const appProcess = spawn('./gradlew', [':webauthn-server:run'], {
      cwd: process.cwd(),
      detached: true,
      stdio: 'pipe'
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `Development server starting...\n- Dependencies: ${withDependencies ? 'Started' : 'Skipped'}\n- Server: Starting on port ${port}\n- PID: ${appProcess.pid}\n\nServer should be available at http://localhost:${port} in a few moments.`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to start development server:\n${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function stopDevServer(args = {}) {
  try {
    // Stop Docker dependencies
    execSync('docker-compose -f webauthn-server/docker-compose.yml down', {
      encoding: 'utf8',
      cwd: process.cwd()
    });
    
    // Kill any running Gradle processes
    try {
      execSync('pkill -f "gradle.*run"', { encoding: 'utf8' });
    } catch (e) {
      // Ignore if no processes found
    }
    
    return {
      content: [
        {
          type: 'text',
          text: 'Development server and dependencies stopped successfully.',
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error stopping services: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function analyzeCodeStructure(args = {}) {
  const { path = 'src/main/kotlin', depth = 3 } = args;
  
  function analyzeDirectory(dirPath, currentDepth = 0, maxDepth = 3) {
    const items = [];
    
    if (currentDepth >= maxDepth || !existsSync(dirPath)) {
      return items;
    }
    
    try {
      const entries = readdirSync(dirPath);
      
      for (const entry of entries) {
        const fullPath = join(dirPath, entry);
        const stat = statSync(fullPath);
        const relativePath = relative(process.cwd(), fullPath);
        
        if (stat.isDirectory()) {
          items.push({
            type: 'directory',
            name: entry,
            path: relativePath,
            children: analyzeDirectory(fullPath, currentDepth + 1, maxDepth)
          });
        } else if (entry.endsWith('.kt')) {
          // Analyze Kotlin file
          const content = readFileSync(fullPath, 'utf8');
          const lines = content.split('\n');
          const classes = lines.filter(line => line.trim().startsWith('class ') || line.trim().startsWith('interface ') || line.trim().startsWith('object '));
          const functions = lines.filter(line => line.trim().startsWith('fun '));
          
          items.push({
            type: 'kotlin-file',
            name: entry,
            path: relativePath,
            stats: {
              lines: lines.length,
              classes: classes.length,
              functions: functions.length
            }
          });
        }
      }
    } catch (error) {
      console.error(`Error analyzing ${dirPath}:`, error.message);
    }
    
    return items;
  }
  
  const structure = analyzeDirectory(path, 0, depth);
  
  function formatStructure(items, indent = 0) {
    let output = '';
    const indentStr = '  '.repeat(indent);
    
    for (const item of items) {
      if (item.type === 'directory') {
        output += `${indentStr}📁 ${item.name}/\n`;
        if (item.children) {
          output += formatStructure(item.children, indent + 1);
        }
      } else if (item.type === 'kotlin-file') {
        output += `${indentStr}📄 ${item.name} (${item.stats.lines} lines, ${item.stats.classes} classes, ${item.stats.functions} functions)\n`;
      }
    }
    
    return output;
  }
  
  return {
    content: [
      {
        type: 'text',
        text: `Code Structure Analysis for ${path}:\n\n${formatStructure(structure)}`,
      },
    ],
  };
}

async function checkDependencies(args = {}) {
  const { outdated = false } = args;
  
  try {
    let command = './gradlew :webauthn-server:dependencies';
    if (outdated) {
      command = './gradlew :webauthn-server:dependencyUpdates';
    }
    
    const output = execSync(command, { 
      encoding: 'utf8',
      cwd: process.cwd(),
      timeout: 60000
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `Dependency Information:\n\n${output}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error checking dependencies: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function generateApiClients(args = {}) {
  const { language = 'all' } = args;
  
  try {
    let command = './gradlew';
    
    if (language === 'all') {
      command += ' :webauthn-server:generateAllClients';
    } else {
      const taskMap = {
        'typescript': ':webauthn-server:generateTsClient',
        'java': ':webauthn-server:generateJavaClient', 
        'python': ':webauthn-server:generatePythonClient',
        'csharp': ':webauthn-server:generateCsharpClient'
      };
      command += ` ${taskMap[language]}`;
    }
    
    const output = execSync(command, { 
      encoding: 'utf8',
      cwd: process.cwd(),
      timeout: 300000
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `API client generation completed for ${language}!\n\nOutput:\n${output}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Client generation failed: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function databaseStatus(args = {}) {
  try {
    // Check Docker services
    const dockerStatus = execSync('docker-compose -f webauthn-server/docker-compose.yml ps', { 
      encoding: 'utf8',
      cwd: process.cwd()
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `Database Status:\n\n${dockerStatus}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error checking database status: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function viewLogs(args = {}) {
  const { lines = 50, level = 'ALL' } = args;
  
  try {
    // Check for application logs
    const logPaths = [
      'build/logs/application.log',
      'logs/application.log',
      '/tmp/webauthn-server.log'
    ];
    
    let logContent = 'No log files found.\n\nTrying Docker logs...\n\n';
    
    try {
      // Try to get Docker logs
      const dockerLogs = execSync('docker-compose -f webauthn-server/docker-compose.yml logs --tail=50 webauthn-server', { 
        encoding: 'utf8',
        cwd: process.cwd(),
        timeout: 10000
      });
      logContent += dockerLogs;
    } catch (dockerError) {
      logContent += 'No Docker logs available.\n';
    }
    
    return {
      content: [
        {
          type: 'text',
          text: `Application Logs (last ${lines} lines):\n\n${logContent}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error viewing logs: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function testApiEndpoint(args = {}) {
  const { endpoint, method = 'GET', body, baseUrl = 'http://localhost:8080' } = args;
  
  try {
    const url = `${baseUrl}${endpoint}`;
    let curlCommand = `curl -X ${method} "${url}" -H "Content-Type: application/json"`;
    
    if (body && (method === 'POST' || method === 'PUT')) {
      curlCommand += ` -d '${body}'`;
    }
    
    curlCommand += ' -w "\\nStatus: %{http_code}\\nTime: %{time_total}s"';
    
    const output = execSync(curlCommand, { 
      encoding: 'utf8',
      timeout: 30000
    });
    
    return {
      content: [
        {
          type: 'text',
          text: `API Test: ${method} ${url}\n\nResponse:\n${output}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `API test failed: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('WebAuthn Dev Tools MCP server running on stdio');
}

run().catch(console.error);