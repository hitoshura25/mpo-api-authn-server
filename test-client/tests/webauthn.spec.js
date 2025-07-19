const { test, expect } = require('@playwright/test');

test.describe('WebAuthn Passkey End-to-End Tests', () => {

  test.beforeEach(async ({ page, context }) => {
    // For Chromium-based browsers, use CDP (Chrome DevTools Protocol)
    if (context._browser.browserType().name() === 'chromium') {
      const client = await context.newCDPSession(page);
      await client.send('WebAuthn.enable');
      const { authenticatorId } = await client.send('WebAuthn.addVirtualAuthenticator', {
        options: {
          protocol: 'ctap2',
          ctap2Version: 'ctap2_1',
          transport: 'internal',
          hasResidentKey: true,
          hasUserVerification: true,
          hasLargeBlob: false,
          hasCredBlob: false,
          hasMinPinLength: false,
          hasPrf: false,
          automaticPresenceSimulation: true,
          isUserVerified: true
        }
      });
      page.authenticatorId = authenticatorId;
    }

    // Navigate to the test client web application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Wait for the application to fully initialize
    await page.waitForFunction(() => {
      return window.SimpleWebAuthnBrowser &&
             document.getElementById('connectionStatus') &&
             document.querySelector('h1').textContent.includes('WebAuthn');
    }, { timeout: 10000 });
  });

  test('should load test client web application', async ({ page }) => {
    await expect(page).toHaveTitle('WebAuthn Test Client');
    await expect(page.locator('h1')).toContainText('WebAuthn Passkey Test Client');

    // Check if SimpleWebAuthn library is loaded
    const isLibraryLoaded = await page.evaluate(() => {
      return typeof window.SimpleWebAuthnBrowser !== 'undefined';
    });
    expect(isLibraryLoaded).toBe(true);
  });

  test('should successfully connect to server', async ({ page }) => {
    // Wait for the automatic connection test to complete
    await page.waitForTimeout(3000);

    const connectionStatus = await page.locator('#connectionStatus').textContent();

    // Server must be running for tests to pass
    expect(connectionStatus).toContain('successful');
  });

  test('should complete full registration flow with virtual authenticator', async ({ page }) => {
    // No need to mock - use virtual authenticator for real WebAuthn calls

    // Fill registration form
    await page.fill('#regUsername', 'playwright-test-user');
    await page.fill('#regDisplayName', 'Playwright Test User');

    // Start registration - this will use the virtual authenticator
    await page.click('button:has-text("Register Passkey")');

    // Wait for registration to complete
    await page.waitForTimeout(5000);

    const registrationStatus = await page.locator('#registrationStatus').textContent();
    expect(registrationStatus).toContain('successful');
  });

  test('should complete full authentication flow with virtual authenticator', async ({ page }) => {
    // First register a credential
    await page.fill('#regUsername', 'playwright-auth-user');
    await page.fill('#regDisplayName', 'Playwright Auth User');
    await page.click('button:has-text("Register Passkey")');
    await page.waitForTimeout(3000);

    // Then authenticate with it
    await page.fill('#authUsername', 'playwright-auth-user');
    await page.click('button:has-text("Authenticate with Passkey")');
    await page.waitForTimeout(3000);

    const authStatus = await page.locator('#authenticationStatus').textContent();
    expect(authStatus).toContain('successful');
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
          hasChallenge: !!data.publicKeyCredentialCreationOptions?.publicKey.challenge,
          hasUser: !!data.publicKeyCredentialCreationOptions?.publicKey.user
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
          hasChallenge: !!data.publicKeyCredentialRequestOptions?.publicKey.challenge
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
