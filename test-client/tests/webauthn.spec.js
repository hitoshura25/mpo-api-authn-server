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
    // Set up CDP (Chrome DevTools Protocol) virtual authenticator
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

    // Navigate to the test client web application
    await page.goto('http://localhost:8082');
    await page.waitForLoadState('networkidle');
  });

  test('should complete full registration and authentication flow with virtual authenticator', async ({ page }, testInfo) => {
    // Generate scalable unique username using test metadata
    const uniqueUsername = generateUniqueUsername(testInfo.title, testInfo.workerIndex);

    // Step 1: Register a new passkey
    await page.fill('#regUsername', uniqueUsername);
    await page.fill('#regDisplayName', 'Playwright Test User');

    // Start registration - this will use the virtual authenticator
    await page.click('button:has-text("Register Passkey")');

    // Wait for registration to complete
    await page.waitForTimeout(5000);

    const registrationStatus = await page.locator('#registrationStatus').textContent();
    expect(registrationStatus).toContain('successful');

    // Step 2: Authenticate with the newly registered passkey
    await page.fill('#authUsername', uniqueUsername);
    await page.click('button:has-text("Authenticate with Passkey")');
    await page.waitForTimeout(3000);

    const authStatus = await page.locator('#authenticationStatus').textContent();
    expect(authStatus).toContain('successful');

    console.log(`Full flow completed successfully for user: ${uniqueUsername}`);
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
