# WebAuthn Web Test Client

A TypeScript-based WebAuthn E2E test client that consumes published npm packages, with webpack bundling and comprehensive E2E testing using Playwright.

## 🏗️ Architecture Overview

This client demonstrates modern TypeScript development practices with:

- **TypeScript 5.3+** with strict type checking
- **Published npm package consumption** for client library integration
- **Webpack bundling** with UMD/CommonJS support for browser compatibility
- **Playwright E2E testing** with real WebAuthn credential testing
- **Express development server** for local testing
- **Production-ready builds** with TypeScript declarations

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- TypeScript 5.3+
- Running WebAuthn server (port 8080)
- WebAuthn test credentials service (port 8081)

### Installation

```bash
# Install dependencies
npm install

# Build the TypeScript client
npm run build

# Start development server
npm run dev

# Run E2E tests
npm test
```

### Published TypeScript Client

The project consumes the published TypeScript client library from npm:

```bash
# Production package (stable releases):
@vmenon25/mpo-webauthn-client

# Staging package (development/testing):
@hitoshura25/mpo-webauthn-client-staging

# No manual generation needed - uses published packages
```

## 📁 Project Structure

```
web-test-client/
├── src/                          # TypeScript source files
│   ├── index.ts                  # Main entry point and UMD exports
│   ├── server.ts                 # Express development server
│   ├── types.ts                  # Shared TypeScript types
│   └── webauthn-client.ts        # WebAuthn client implementation
├── public/                       # Static assets
│   └── index.html                # Test page template
├── tests/                        # Playwright E2E tests
│   └── webauthn.spec.js          # WebAuthn flow tests
├── dist/                         # Build output
│   ├── umd/                      # UMD bundles for browser use
│   └── src/                      # TypeScript server builds
├── scripts/                      # Utility scripts
│   └── cleanup-port.js           # Port cleanup for tests
├── webpack.config.js             # Webpack build configuration
├── tsconfig.json                 # TypeScript base configuration
├── tsconfig.build.json           # Build-specific TypeScript config
├── playwright.config.js          # Playwright test configuration
└── package.json                  # Dependencies with published client library
```

**Published Client Library Structure**:
```
../typescript-client-library/             # Dedicated client library submodule
├── src/                          # Generated TypeScript client source
├── dist/                         # Built CommonJS + ESM outputs
├── package.json                  # Publishing configuration
└── README.md                     # Client library documentation
```

## 🔧 Build System

### Webpack Configuration

The project uses a sophisticated webpack setup:

- **Development mode**: Source maps, hot reload, HTML plugin
- **Production mode**: Minification, UMD bundling, tree shaking
- **External dependencies**: @simplewebauthn/browser as external for smaller bundles
- **TypeScript compilation**: ts-loader with Babel for broader browser support

### TypeScript Configuration

- **tsconfig.json**: Base configuration for development
- **tsconfig.build.json**: Build-specific configuration with declarations
- **Strict type checking** enabled
- **ES2020 target** with DOM types for browser compatibility

## 📚 Available Scripts

### Development

```bash
npm run dev              # Build and start development server
npm run build:dev        # Development build only
npm run dev:server       # Start server with hot reload (ts-node)
```

### Production

```bash
npm run build            # Full production build (webpack + server)
npm run build:server     # Build TypeScript server only
npm start                # Start production server
```

### Testing

```bash
npm test                 # Run Playwright E2E tests
npm run test:ui          # Interactive test UI
npm run test:debug       # Debug mode with breakpoints
npm run test:headed      # Run tests with browser UI
npm run test:report      # View test results report
npm run test:clean       # Clean ports and run tests
```

### Server Management

```bash
npm run server:start     # Start WebAuthn server dependencies
npm run server:stop      # Stop all server services
npm run server:logs      # View server logs
npm run server:restart   # Restart WebAuthn server
npm run server:status    # Check server status
```

### Utility

```bash
npm run cleanup:port     # Clean up port 8082 if stuck
npm run test:with-server # Start server, run tests, stop server
```

## 🧪 Testing Architecture

### Playwright E2E Tests

The test suite validates complete WebAuthn flows:

- **Registration flow**: User account creation with passkey
- **Authentication flow**: Login with registered passkey
- **Error handling**: Invalid credentials, timeouts, cancellations
- **Cross-browser compatibility**: Chromium, Firefox, WebKit

### Test Configuration

```javascript
// playwright.config.js
{
  testDir: './tests',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:8082',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } }
  ]
}
```

## 🔗 Published Client Integration

The published TypeScript client provides type-safe API access:

### Usage Example

```typescript
import { 
  AuthenticationApi, 
  RegistrationApi,
  Configuration 
} from '@vmenon25/mpo-webauthn-client';

// Configure API client
const configuration = new Configuration({
  basePath: 'http://localhost:8080'
});

const registrationApi = new RegistrationApi(configuration);
const authenticationApi = new AuthenticationApi(configuration);

// Type-safe API calls
const startResponse = await registrationApi.startRegistration({
  registrationRequest: { username: 'testuser' }
});

// Parsed server response for WebAuthn
const publicKeyOptions = JSON.parse(
  startResponse.publicKeyCredentialCreationOptions
).publicKey;
```

### Published Client Features

- **Full type safety** with TypeScript interfaces
- **Automatic serialization** of request/response data
- **Error handling** with typed exception models
- **Browser and Node.js compatibility**
- **Staging→Production workflow** for E2E validation
- **Automated publishing** via GitHub Actions workflows

## 🌐 UMD Bundle Usage

The client builds to a UMD bundle for direct browser use:

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/@simplewebauthn/browser@9.0.1/dist/bundle/index.umd.min.js"></script>
  <script src="./dist/umd/webauthn-client.umd.js"></script>
</head>
<body>
  <script>
    // Global WebAuthnClient available
    const client = new WebAuthnClient.WebAuthnTestClient('http://localhost:8080');
    
    // Perform WebAuthn registration
    client.performRegistration('testuser')
      .then(result => console.log('Registration successful:', result))
      .catch(error => console.error('Registration failed:', error));
  </script>
</body>
</html>
```

## 🔒 WebAuthn Integration

### SimpleWebAuthn Browser Integration

The client uses the SimpleWebAuthn browser library:

```typescript
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';

// Registration flow
const credential = await startRegistration(publicKeyOptions);
const response = await registrationApi.completeRegistration({
  requestId: startData.requestId,
  credential: JSON.stringify(credential)
});

// Authentication flow  
const assertion = await startAuthentication(publicKeyOptions);
const authResult = await authenticationApi.completeAuthentication({
  requestId: startData.requestId,
  credential: JSON.stringify(assertion)
});
```

### Data Flow Requirements

Critical integration patterns:

1. **Server Response Parsing**: Parse `.publicKey` field for SimpleWebAuthn
2. **Credential Serialization**: Stringify credentials before sending to server
3. **Error Handling**: Handle WebAuthn exceptions and server errors
4. **Type Safety**: Use generated models for request/response data

## 🚢 Deployment

### NPM Package Structure

The client is ready for npm publishing:

```json
{
  "name": "webauthn-web-test-client",
  "main": "./dist/umd/webauthn-client.umd.js",
  "types": "./dist/src/index.d.ts",
  "files": ["dist/"]
}
```

### Distribution Files

- `dist/umd/webauthn-client.umd.js` - UMD bundle for browsers
- `dist/src/` - TypeScript compiled output with declarations
- `dist/src/index.d.ts` - TypeScript type definitions

## 🛠️ Development Workflow

### Local Development

1. Start the WebAuthn server stack:
   ```bash
   cd ../webauthn-server && ./start-dev.sh
   ```

2. Start the test credentials service:
   ```bash
   cd .. && ./gradlew :webauthn-test-credentials-service:run
   ```

3. Build and start the web client:
   ```bash
   npm run build && npm start
   ```

4. Run tests:
   ```bash
   npm test
   ```

### 🚀 CI/CD Integration

The client integrates seamlessly with the project's **3-tier AI-powered CI/CD pipeline**:

**Smart Workflow Integration**:
- **Staging package consumption**: E2E tests use staging packages for validation
- **Build verification**: TypeScript compilation and webpack bundling with published packages
- **Conditional execution**: Only builds when TypeScript/web client files change
- **Cross-platform testing**: Parallel execution with Android E2E tests using published packages

**E2E Testing Pipeline** (`e2e-tests.yml`):
- **Docker image validation**: Uses exact PR-specific Docker images
- **Service orchestration**: Automatic dependency startup (PostgreSQL, Redis, Jaeger)
- **Health checking**: Comprehensive service readiness validation
- **Test execution**: Full WebAuthn flow validation with Playwright
- **Artifact management**: Test reports and screenshots uploaded automatically
- **Parallel testing**: Web and Android tests run simultaneously for faster feedback

**Security Integration**:
- **3-tier security analysis**: Web client changes trigger security review
- **Vulnerability scanning**: TypeScript dependencies scanned for security issues
- **AI-powered analysis**: WebAuthn client patterns analyzed for security vulnerabilities
- **Automated security gates**: High-risk changes block merge until review

**Performance Optimizations**:
- **Smart change detection**: Only rebuild when necessary (docs/workflow changes skip builds)
- **Branch-specific caching**: Gradle and npm caches optimized per branch
- **Parallel builds**: Dependencies installed in parallel for faster execution
- **Build artifact reuse**: Generated clients shared between build and test stages

## 📊 Performance Characteristics

### Bundle Sizes

- **UMD Bundle**: ~50KB minified (excluding SimpleWebAuthn)
- **Generated Client**: ~30KB with all API endpoints
- **Development Build**: ~200KB with source maps

### Build Times

**Local Development**:
- **Development build**: ~2-3 seconds
- **Production build**: ~5-8 seconds with optimization
- **Test execution**: ~30-60 seconds for full suite

**CI/CD Pipeline Performance**:
- **Fast path** (docs/workflow only): ~30 seconds total
- **Build with change detection**: ~3-5 minutes
- **Full E2E pipeline**: ~8-12 minutes including Docker builds
- **Parallel test execution**: Web + Android tests run simultaneously
- **Smart caching**: 50-70% faster builds with branch-specific Gradle/npm caches

## 🔧 Configuration

### Environment Variables

**Development Configuration**:
```bash
# Development server port (default: 8082)
PORT=8082

# API server URL (default: http://localhost:8080)
API_BASE_URL=http://localhost:8080

# Test credentials service URL (default: http://localhost:8081)
TEST_SERVICE_URL=http://localhost:8081
```

**CI/CD Pipeline Configuration**:
```yaml
# Centralized in .github/workflows/
env:
  WEBAUTHN_SERVER_PORT: 8080
  TEST_CREDENTIALS_PORT: 8081
  WEB_CLIENT_PORT: 8082
  
  # Docker image management
  WEBAUTHN_SERVER_IMAGE: ${{ inputs.webauthn_server_image }}
  TEST_CREDENTIALS_IMAGE: ${{ inputs.test_credentials_image }}
  
  # Security analysis configuration
  HIGH_RISK_SCORE_THRESHOLD: 7.0
  BLOCK_MERGE_ON_CRITICAL: true
```

**Workflow Integration Variables**:
- **PR_NUMBER**: Used for artifact naming and image tagging
- **CLIENT_VERSION**: Automated version generation for client libraries
- **PLAYWRIGHT_* variables**: Automated browser configuration
- **DOCKER_* variables**: Container registry and image management

### Webpack Externals

SimpleWebAuthn is configured as external to reduce bundle size:

```javascript
externals: {
  '@simplewebauthn/browser': 'SimpleWebAuthnBrowser'
}
```

## 🤝 Contributing

### Development Guidelines

1. **TypeScript Standards**: Follow strict mode requirements and type safety
2. **Test Coverage**: Update tests for API changes and new functionality
3. **Package Publishing**: Client library publishing handled automatically by CI/CD
4. **Build Validation**: Webpack builds tested for both development and production
5. **Security Review**: Changes undergo 3-tier AI security analysis

### 🔒 Security Contribution Guidelines

**Before Making Changes**:
- Review security impact of WebAuthn client modifications
- Consider cross-origin implications and browser security model
- Validate credential handling and serialization patterns

**Pull Request Process**:
1. **Automated Security Analysis**: Your PR will trigger 3-tier AI security review
2. **Security Labels**: PRs automatically tagged with security analysis results
3. **Critical Issues**: High-risk changes are blocked until manual review
4. **Test Generation**: AI may generate additional security tests for your changes

**Manual Review Required For**:
- Changes to WebAuthn credential handling logic
- Modifications to authentication/registration flows
- New dependencies or third-party integrations
- Browser security model interactions

### 🚀 Workflow Integration

**Change Detection**:
- TypeScript/web client changes trigger full build and test cycle
- Documentation-only changes use fast path (no builds needed)
- Dockerfile changes trigger Docker rebuild and E2E tests

**Testing Strategy**:
- Local development: `npm test` for Playwright E2E tests
- CI/CD: Parallel web + Android testing with real Docker services
- Cross-browser validation: Chromium, Firefox, WebKit support
- Performance monitoring: Build times and bundle size tracking

## 📝 Additional Documentation

- **[Main Project README](../README.md)** - Full project overview with 3-tier AI security system
- **[CI/CD Pipeline Documentation](../docs/development/workflows/)** - Detailed workflow architecture
- **[Security Analysis Guide](../docs/security/webauthn-analysis.md)** - WebAuthn security testing details
- **[Scripts Usage](../docs/development/scripts-usage.md)** - Development and workflow scripts
- **[Client Library Publishing](../docs/development/client-library-publishing.md)** - Published client library workflows

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.