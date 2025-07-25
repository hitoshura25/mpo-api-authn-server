#!/bin/bash

# Setup script for WebAuthn MCP development tools
set -e

echo "🛠️  Setting up WebAuthn MCP Development Tools"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm found: $(npm --version)"

# Install MCP SDK dependencies
echo "📦 Installing MCP SDK dependencies..."
npm install

# Make the MCP server executable
chmod +x dev-tools-mcp-server.js

echo ""
echo "🎉 Setup complete! You can now use Claude Code with MCP integration."
echo ""
echo "📋 Available MCP tools:"
echo "  • run_tests - Run project tests"
echo "  • build_project - Build the project with Gradle"
echo "  • start_dev_server - Start development server with dependencies"
echo "  • stop_dev_server - Stop development server and dependencies"
echo "  • analyze_code_structure - Analyze project code organization"
echo "  • check_dependencies - Check project dependencies"
echo "  • generate_api_clients - Generate API client libraries"
echo "  • database_status - Check database connection status"
echo "  • view_logs - View application logs"
echo "  • test_api_endpoint - Test specific API endpoints"
echo ""
echo "💡 Usage examples:"
echo "  Claude Code: 'Run the tests'"
echo "  Claude Code: 'Start the development server'"
echo "  Claude Code: 'Analyze the code structure'"
echo "  Claude Code: 'Test the /health endpoint'"
echo ""
echo "🔧 Configuration:"
echo "  • claude_config.json is already configured"
echo "  • MCP server will auto-start when Claude Code needs it"