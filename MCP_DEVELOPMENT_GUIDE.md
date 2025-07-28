# WebAuthn MCP Development Tools

This project is enhanced with Model Context Protocol (MCP) tools specifically designed for full-stack development with Claude Code.

## Quick Setup

1. **Install dependencies:**
   ```bash
   ./setup-dev-tools.sh
   ```

2. **Start using Claude Code** - The `claude_config.json` is already configured and Claude Code will automatically detect the MCP tools when you're in this directory.

## Available Development Tools

### 🧪 Testing Tools
- **`run_tests`** - Run project tests with optional filters
  - Filter by test pattern or class name
  - Choose test types (unit, integration, all)
  - Works with multi-module structure (`:webauthn-server:test`) and standalone projects (`cd android-test-client && ./gradlew test`)

### 🏗️ Build Tools  
- **`build_project`** - Build the project with Gradle
  - Option for clean builds
  - Option to skip tests
  - Supports module-specific builds (`:webauthn-server:build`)

### 🚀 Server Management
- **`start_dev_server`** - Start development server with dependencies
  - Uses `webauthn-server/start-dev.sh` for Docker setup
  - Automatically starts PostgreSQL and Redis
  - Configurable port
- **`stop_dev_server`** - Stop server and dependencies
  - Stops Docker containers in webauthn-server module

### 🔍 Code Analysis
- **`analyze_code_structure`** - Analyze project organization
  - Shows directory structure with file statistics
  - Configurable depth and path

### 📦 Dependency Management
- **`check_dependencies`** - Check project dependencies
  - View dependency tree
  - Check for outdated dependencies

### 🌐 API Tools
- **`generate_api_clients`** - Generate client libraries
  - Support for TypeScript, Java, Python, C#
- **`test_api_endpoint`** - Test specific API endpoints
  - Support for all HTTP methods
  - JSON request bodies

### 🗄️ Database Tools
- **`database_status`** - Check database connection and schema

### 📝 Monitoring Tools
- **`view_logs`** - View application logs
  - Configurable number of lines
  - Log level filtering

## Usage Examples with Claude Code

### Development Workflow
```
You: "Start the development server and run the tests"
Claude Code: Uses start_dev_server → run_tests

You: "Analyze the code structure in the routes package"  
Claude Code: Uses analyze_code_structure with specific path

You: "Test the authentication endpoint with a POST request"
Claude Code: Uses test_api_endpoint with method and body
```

### Debugging Workflow
```
You: "The server won't start, help me debug"
Claude Code: Uses database_status → view_logs → analyze issues

You: "Check if our dependencies are up to date"
Claude Code: Uses check_dependencies with outdated=true
```

### Build and Deploy
```
You: "Do a clean build and generate all API clients"
Claude Code: Uses build_project with clean=true → generate_api_clients

You: "Build the project but skip the tests"
Claude Code: Uses build_project with skipTests=true
```

## Configuration

### Environment Variables
The MCP tools work with your existing environment configuration. Make sure your `.env` or environment has:

```bash
MPO_AUTHN_DB_HOST=localhost
MPO_AUTHN_DB_PORT=5432
MPO_AUTHN_DB_NAME=webauthn_dev
MPO_AUTHN_DB_USERNAME=postgres
MPO_AUTHN_DB_PASSWORD=postgres
MPO_AUTHN_REDIS_HOST=localhost
MPO_AUTHN_REDIS_PORT=6379
MPO_AUTHN_APP_RELYING_PARTY_ID=localhost
MPO_AUTHN_APP_RELYING_PARTY_NAME=WebAuthn Dev Server
```

### MCP Configuration
The `claude_config.json` is pre-configured:

```json
{
  "mcpServers": {
    "webauthn-dev-tools": {
      "command": "node",
      "args": ["dev-tools-mcp-server.js"],
      "cwd": "/Users/vinayakmenon/mpo-api-authn-server"
    }
  }
}
```

## Benefits for Development

### 🤖 AI-Assisted Development
- **Smart Testing**: Claude Code can run relevant tests based on your changes
- **Code Analysis**: Get insights into code structure and organization
- **Debugging Help**: AI can analyze logs and suggest solutions

### ⚡ Streamlined Workflow
- **One Command**: Ask Claude Code to perform complex multi-step operations
- **Context Aware**: Tools understand your project structure and conventions
- **Integrated**: No need to remember complex Gradle commands

### 🔄 Continuous Feedback
- **Real-time Status**: Check server and database status
- **Build Feedback**: Get immediate build results and error analysis
- **Test Results**: Run and analyze test results with AI assistance

### 📈 Enhanced Productivity
- **Automated Tasks**: Let AI handle routine development tasks
- **Quick Prototyping**: Rapidly test ideas and implementations
- **Documentation**: Generate documentation and examples automatically

## Troubleshooting

### MCP Server Issues
If the MCP server fails to start:
1. Check Node.js installation: `node --version`
2. Install dependencies: `npm install`
3. Check file permissions: `chmod +x dev-tools-mcp-server.js`

### Development Server Issues
If the development server won't start:
1. Check database status: Ask Claude Code to run `database_status`
2. View logs: Ask Claude Code to run `view_logs`
3. Stop and restart: Ask Claude Code to `stop_dev_server` then `start_dev_server`

### Test Failures
If tests are failing:
1. Run specific tests: Ask Claude Code to `run_tests` with a pattern
2. Check build status: Ask Claude Code to `build_project`
3. Analyze code changes: Ask Claude Code to `analyze_code_structure`

## Extending the Tools

The MCP server is extensible. To add new tools:

1. Add the tool definition to the `ListToolsRequestSchema` handler
2. Add the implementation in the `CallToolRequestSchema` handler
3. Test with Claude Code

This enables you to create custom development workflows specific to your project needs.