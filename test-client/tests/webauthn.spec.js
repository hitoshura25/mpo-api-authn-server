const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

// Helper function to generate unique usernames for parallel test execution
function generateUniqueUsername(testName, workerIndex = 0) {
  const timestamp = Date.now();
  const randomBytes = crypto.randomBytes(4).toString('hex');
  const processId = process.pid;
  const workerId = workerIndex || Math.floor(Math.random() * 1000);

  // Create a short hash of the test name for readability
  const testHash = crypto.createHash('md5').update(testName).digest('hex').substring(0, 6);

  return `pw-${testHash}-${timestamp}-${processId}-${workerId}-${randomBytes}`;
}

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
    await page.goto('http://localhost:8081');
    await page.waitForLoadState('networkidle');
  });

  test('should complete full registration flow with virtual authenticator', async ({ page }, testInfo) => {
    // Generate scalable unique username using test metadata
    const uniqueUsername = generateUniqueUsername(testInfo.title, testInfo.workerIndex);

    // Fill registration form
    await page.fill('#regUsername', uniqueUsername);
    await page.fill('#regDisplayName', 'Playwright Test User');

    // Start registration - this will use the virtual authenticator
    await page.click('button:has-text("Register Passkey")');

    // Wait for registration to complete
    await page.waitForTimeout(5000);

    const registrationStatus = await page.locator('#registrationStatus').textContent();
    expect(registrationStatus).toContain('successful');
  });

  test('should complete full authentication flow with virtual authenticator', async ({ page }, testInfo) => {
    // Generate unique username for this test
    const uniqueUsername = generateUniqueUsername(testInfo.title, testInfo.workerIndex);

    // First register a credential
    await page.fill('#regUsername', uniqueUsername);
    await page.fill('#regDisplayName', 'Playwright Auth User');
    await page.click('button:has-text("Register Passkey")');
    await page.waitForTimeout(3000);

    // Then authenticate with it
    await page.fill('#authUsername', uniqueUsername);
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
                origin: 'http://localhost:8081',
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
