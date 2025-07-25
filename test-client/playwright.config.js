// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail fast - stop on first failure */
  maxFailures: process.env.CI ? 1 : undefined,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 2 : '50%',
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
    // Only generate HTML report, don't serve it automatically
    ['html', { open: 'never' }]
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
    /* Record video on failure - ensure it's properly configured */
    video: {
      mode: 'retain-on-failure',
      size: { width: 1280, height: 720 }
    },
    /* Base URL for your WebAuthn server */
    baseURL: 'http://localhost:8080',
    /* Enable HAR recording for network analysis */
    recordHar: {
      mode: 'minimal',
      path: 'test-results/network-logs.har'
    }
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Enable WebAuthn testing features
        launchOptions: {
          args: ['--enable-features=WebAuthentication']
        }
      },
    },
    /* Test against mobile viewports for mobile passkey testing */
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        launchOptions: {
          args: ['--enable-features=WebAuthentication']
        }
      },
    },
  ],

  /* Global setup and teardown */
  globalSetup: require.resolve('./global-setup.js'),
  globalTeardown: require.resolve('./global-teardown.js'),

  /* Folders to ignore */
  testIgnore: ['**/node_modules/**', '**/build/**'],

  /* Maximum time one test can run for. */
  timeout: 30 * 1000,

  /* Maximum time expect() should wait for the condition to be met. */
  expect: {
    timeout: 5000,
  },
});
