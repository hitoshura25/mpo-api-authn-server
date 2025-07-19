// Global teardown for Playwright tests
async function globalTeardown() {
  console.log('🧹 Cleaning up WebAuthn test environment...');
  // Add any cleanup logic here if needed
  return null;
}

module.exports = globalTeardown;
