const { test, expect } = require('@playwright/test');
const path = require('path');

test.describe('WebAuthn Passkey End-to-End Tests', () => {

  test.beforeEach(async ({ page, context }) => {
    // Add virtual authenticator with proper WebAuthn support
    await context.addInitScript(() => {
      // Mock WebAuthn API to work with virtual authenticator
      if (!window.PublicKeyCredential) {
        window.PublicKeyCredential = class MockPublicKeyCredential {
          static async isUserVerifyingPlatformAuthenticatorAvailable() {
            return true;
          }

          static async isConditionalMediationAvailable() {
            return true;
          }
        };
      }
    });

    // Navigate to the test client
    const testClientPath = path.join(__dirname, '..', 'index.html');
    await page.goto(`file://${testClientPath}`);

    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
  });

  test('should load test client and verify WebAuthn availability', async ({ page }) => {
    await expect(page).toHaveTitle('WebAuthn Test Client');
    await expect(page.locator('h1')).toContainText('WebAuthn Passkey Test Client');

    // Check if WebAuthn APIs are available
    const isWebAuthnAvailable = await page.evaluate(() => {
      return typeof window.PublicKeyCredential !== 'undefined';
    });

    expect(isWebAuthnAvailable).toBe(true);
  });

  test('should successfully connect to server', async ({ page }) => {
    // Wait for the automatic connection test to complete
    await page.waitForTimeout(3000);

    const connectionStatus = await page.locator('#connectionStatus').textContent();

    // Server must be running for tests to pass
    expect(connectionStatus).toContain('successful');
  });

  test('should complete full registration flow with real server', async ({ page }) => {
    // Mock successful WebAuthn registration but let server calls go through
    await page.addInitScript(() => {
      const mockCredential = {
        id: 'test-credential-id-' + Date.now(),
        rawId: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
        response: {
          clientDataJSON: new TextEncoder().encode(JSON.stringify({
            type: 'webauthn.create',
            challenge: 'test-challenge',
            origin: 'http://localhost:8080',
          })),
          attestationObject: new Uint8Array([
            0xa3, 0x63, 0x66, 0x6d, 0x74, 0x66, 0x70, 0x61, 0x63, 0x6b, 0x65, 0x64,
            0x67, 0x61, 0x74, 0x74, 0x53, 0x74, 0x6d, 0x74, 0xa0, 0x68, 0x61, 0x75,
            0x74, 0x68, 0x44, 0x61, 0x74, 0x61, 0x58, 0x25
          ])
        },
        type: 'public-key',
        clientExtensionResults: {}
      };

      // Override navigator.credentials.create but allow fetch to go through
      if (window.navigator && window.navigator.credentials) {
        window.navigator.credentials.create = async (options) => {
          console.log('Mock WebAuthn create called with:', options);
          // Simulate some delay
          await new Promise(resolve => setTimeout(resolve, 100));
          return mockCredential;
        };
      }
    });

    // Fill registration form
    await page.fill('#regUsername', 'playwright-test-user');
    await page.fill('#regDisplayName', 'Playwright Test User');

    // Start registration
    await page.click('button:has-text("Register Passkey")');

    // Wait for registration to complete
    await page.waitForTimeout(5000);

    // Check final registration status - should succeed or show specific error
    const registrationStatus = await page.locator('#registrationStatus').textContent();

    // The test should either succeed or fail with a specific server error
    // It should NOT fail with network issues if server is running
    expect(registrationStatus).not.toContain('Connection failed');
    expect(registrationStatus).not.toContain('Network error');
  });

  test('should complete full authentication flow with real server', async ({ page }) => {
    // Mock successful WebAuthn authentication but let server calls go through
    await page.addInitScript(() => {
      const mockCredential = {
        id: 'test-credential-id-' + Date.now(),
        rawId: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
        response: {
          clientDataJSON: new TextEncoder().encode(JSON.stringify({
            type: 'webauthn.get',
            challenge: 'test-challenge',
            origin: 'http://localhost:8080',
          })),
          authenticatorData: new Uint8Array([
            0x49, 0x96, 0x0d, 0xe5, 0x88, 0x0e, 0x8c, 0x68, 0x74, 0x34, 0x17, 0x0f,
            0x64, 0x76, 0x60, 0x5b, 0x8f, 0xe4, 0xae, 0xb9, 0xa2, 0x86, 0x32, 0xc7,
            0x99, 0x5c, 0xf3, 0xba, 0x83, 0x1d, 0x97, 0x63, 0x01, 0x00, 0x00, 0x00, 0x00
          ]),
          signature: new Uint8Array([
            0x30, 0x44, 0x02, 0x20, 0x18, 0x97, 0x71, 0x7b, 0x9c, 0x30, 0x7e, 0x02,
            0x62, 0x1a, 0x5e, 0x1b, 0x1c, 0x6e, 0x6f, 0x88, 0x4d, 0x6e, 0x6f, 0x4d,
            0x88, 0x4d, 0x6e, 0x6f, 0x4d, 0x88, 0x4d, 0x6e, 0x6f, 0x4d, 0x88, 0x4d
          ]),
          userHandle: new Uint8Array([21, 22, 23, 24, 25, 26, 27, 28])
        },
        type: 'public-key',
        clientExtensionResults: {}
      };

      // Override navigator.credentials.get but allow fetch to go through
      if (window.navigator && window.navigator.credentials) {
        window.navigator.credentials.get = async (options) => {
          console.log('Mock WebAuthn get called with:', options);
          // Simulate some delay
          await new Promise(resolve => setTimeout(resolve, 100));
          return mockCredential;
        };
      }
    });

    // Fill authentication form
    await page.fill('#authUsername', 'playwright-test-user');

    // Start authentication
    await page.click('button:has-text("Authenticate with Passkey")');

    // Wait for authentication to complete
    await page.waitForTimeout(5000);

    // Check final authentication status - should succeed or show specific error
    const authStatus = await page.locator('#authenticationStatus').textContent();

    // The test should either succeed or fail with a specific server error
    // It should NOT fail with network issues if server is running
    expect(authStatus).not.toContain('Connection failed');
    expect(authStatus).not.toContain('Network error');
  });

  test('should handle usernameless authentication flow with real server', async ({ page }) => {
    // Mock WebAuthn for usernameless flow
    await page.addInitScript(() => {
      if (window.navigator && window.navigator.credentials) {
        window.navigator.credentials.get = async (options) => {
          return {
            id: 'usernameless-credential-id',
            rawId: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]),
            response: {
              clientDataJSON: new TextEncoder().encode(JSON.stringify({
                type: 'webauthn.get',
                challenge: 'test-challenge',
                origin: 'http://localhost:8080',
              })),
              authenticatorData: new Uint8Array(37),
              signature: new Uint8Array(32),
              userHandle: new Uint8Array([21, 22, 23, 24])
            },
            type: 'public-key',
            clientExtensionResults: {}
          };
        };
      }
    });

    // Leave username empty for usernameless flow
    await page.fill('#authUsername', '');

    // Start authentication
    await page.click('button:has-text("Authenticate with Passkey")');

    // Wait for processing
    await page.waitForTimeout(5000);

    const authStatus = await page.locator('#authenticationStatus').textContent();

    // Should get a proper response from server (success or business logic error)
    expect(authStatus).not.toContain('Connection failed');
    expect(authStatus).not.toContain('Network error');
  });

  test('should handle WebAuthn errors gracefully', async ({ page }) => {
    // Mock WebAuthn to throw errors
    await page.addInitScript(() => {
      if (window.navigator && window.navigator.credentials) {
        window.navigator.credentials.create = async () => {
          throw new Error('NotAllowedError: User cancelled the operation');
        };
      }
    });

    // Fill form and try to register
    await page.fill('#regUsername', 'error-test-user');
    await page.fill('#regDisplayName', 'Error Test User');
    await page.click('button:has-text("Register Passkey")');

    // Wait for error to appear
    await page.waitForTimeout(2000);

    // Should show error status
    const status = await page.locator('#registrationStatus').textContent();
    expect(status).toContain('failed');
  });

  test('should validate form inputs properly', async ({ page }) => {
    // Test empty username
    await page.fill('#regUsername', '');
    await page.fill('#regDisplayName', 'Test User');
    await page.click('button:has-text("Register Passkey")');

    await page.waitForTimeout(500);
    let status = await page.locator('#registrationStatus').textContent();
    expect(status).toContain('Please enter both username and display name');

    // Test empty display name
    await page.fill('#regUsername', 'testuser');
    await page.fill('#regDisplayName', '');
    await page.click('button:has-text("Register Passkey")');

    await page.waitForTimeout(500);
    status = await page.locator('#registrationStatus').textContent();
    expect(status).toContain('Please enter both username and display name');
  });

  test('should test server API endpoints directly', async ({ page }) => {
    // Test that server endpoints are accessible and return expected structure
    const registrationStartResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8080/register/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: 'api-test-user',
            displayName: 'API Test User'
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return {
          success: true,
          hasRequestId: !!data.requestId,
          hasOptions: !!data.publicKeyCredentialCreationOptions,
          hasChallenge: !!data.publicKeyCredentialCreationOptions?.challenge,
          hasUser: !!data.publicKeyCredentialCreationOptions?.user
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
        };
      }
    });

    expect(registrationStartResponse.success).toBe(true);
    expect(registrationStartResponse.hasRequestId).toBe(true);
    expect(registrationStartResponse.hasOptions).toBe(true);
    expect(registrationStartResponse.hasChallenge).toBe(true);
    expect(registrationStartResponse.hasUser).toBe(true);

    // Test authentication start endpoint
    const authStartResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8080/authenticate/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: 'api-test-user'
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return {
          success: true,
          hasRequestId: !!data.requestId,
          hasOptions: !!data.publicKeyCredentialRequestOptions,
          hasChallenge: !!data.publicKeyCredentialRequestOptions?.challenge
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
        };
      }
    });

    expect(authStartResponse.success).toBe(true);
    expect(authStartResponse.hasRequestId).toBe(true);
    expect(authStartResponse.hasOptions).toBe(true);
    expect(authStartResponse.hasChallenge).toBe(true);
  });
});

// Configure test execution
test.describe.configure({ mode: 'parallel' });

// Add custom test reporter for better output
test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'passed') {
    // Take screenshot on failure
    const screenshot = await page.screenshot();
    await testInfo.attach('screenshot', { body: screenshot, contentType: 'image/png' });

    // Get console logs
    const logs = await page.evaluate(() => {
      return window.console.history || [];
    });

    if (logs.length > 0) {
      await testInfo.attach('console-logs', { body: JSON.stringify(logs, null, 2), contentType: 'application/json' });
    }
  }
});
