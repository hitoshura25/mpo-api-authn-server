# WebAuthn Web Test Client

A TypeScript-based WebAuthn test client with automated OpenAPI client generation, webpack bundling, and comprehensive E2E testing using Playwright.

## 🏗️ Architecture Overview

This client demonstrates modern TypeScript development practices with:

- **TypeScript 5.3+** with strict type checking
- **Automated OpenAPI client generation** from server specification
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

### Generated OpenAPI Client

The project automatically integrates a generated TypeScript client from the server's OpenAPI specification:

```bash
# Generated client is located in:
./generated-client/

# The client is automatically included in builds
# No manual regeneration needed - handled by CI/CD
```

## 📁 Project Structure

```
web-test-client/
├── src/                          # TypeScript source files
│   ├── index.ts                  # Main entry point and UMD exports
│   ├── server.ts                 # Express development server
│   ├── types.ts                  # Shared TypeScript types
│   └── webauthn-client.ts        # WebAuthn client implementation
├── generated-client/             # Auto-generated OpenAPI client
│   ├── src/apis/                 # Generated API endpoints
│   ├── src/models/               # Generated data models
│   └── index.ts                  # Generated client exports
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
└── playwright.config.js          # Playwright test configuration
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

## 🔗 OpenAPI Client Integration

The generated TypeScript client provides type-safe API access:

### Usage Example

```typescript
import { 
  AuthenticationApi, 
  RegistrationApi,
  Configuration 
} from './generated-client';

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

### Generated Client Features

- **Full type safety** with TypeScript interfaces
- **Automatic serialization** of request/response data
- **Error handling** with typed exception models
- **Browser and Node.js compatibility**
- **Axios-based HTTP client** with interceptor support

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

### CI/CD Integration

The client integrates with the project's CI/CD pipeline:

- **Client regeneration**: Automatic OpenAPI client updates
- **Build verification**: TypeScript compilation and webpack bundling
- **E2E testing**: Full WebAuthn flow validation
- **Artifact publishing**: UMD bundles and TypeScript declarations

## 📊 Performance Characteristics

### Bundle Sizes

- **UMD Bundle**: ~50KB minified (excluding SimpleWebAuthn)
- **Generated Client**: ~30KB with all API endpoints
- **Development Build**: ~200KB with source maps

### Build Times

- **Development build**: ~2-3 seconds
- **Production build**: ~5-8 seconds with optimization
- **Test execution**: ~30-60 seconds for full suite

## 🔧 Configuration

### Environment Variables

```bash
# Development server port (default: 8082)
PORT=8082

# API server URL (default: http://localhost:8080)
API_BASE_URL=http://localhost:8080

# Test credentials service URL (default: http://localhost:8081)
TEST_SERVICE_URL=http://localhost:8081
```

### Webpack Externals

SimpleWebAuthn is configured as external to reduce bundle size:

```javascript
externals: {
  '@simplewebauthn/browser': 'SimpleWebAuthnBrowser'
}
```

## 🤝 Contributing

1. Follow TypeScript strict mode requirements
2. Update tests for API changes
3. Regenerate OpenAPI client after server changes
4. Validate webpack builds for both development and production
5. Run full test suite before submitting changes

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.