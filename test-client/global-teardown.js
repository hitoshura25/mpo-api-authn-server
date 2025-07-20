// Global teardown for Playwright tests
async function globalTeardown() {
  console.log('🧹 Cleaning up WebAuthn test environment...');

  // Clean up the test client web application process
  if (global.testClientProcess) {
    console.log('🔌 Stopping test client web application...');
    try {
      global.testClientProcess.kill('SIGTERM');

      // Give it a moment to gracefully shut down
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Force kill if still running
      if (!global.testClientProcess.killed) {
        global.testClientProcess.kill('SIGKILL');
      }

      console.log('✅ Test client stopped successfully');
    } catch (error) {
      console.warn('⚠️ Warning: Could not stop test client process:', error.message);
    }
  }

  return null;
}

module.exports = globalTeardown;
