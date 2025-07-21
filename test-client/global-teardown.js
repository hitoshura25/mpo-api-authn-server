// Global teardown for Playwright tests
async function globalTeardown() {
  const teardownStartTime = Date.now();
  console.log('🧹 Cleaning up WebAuthn test environment...');

  // Clean up the test client web application process
  if (global.testClientProcess) {
    console.log('🔌 Stopping test client web application...');
    const stopStartTime = Date.now();
    try {
      global.testClientProcess.kill('SIGTERM');

      // Give it a moment to gracefully shut down
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Force kill if still running
      if (!global.testClientProcess.killed) {
        global.testClientProcess.kill('SIGKILL');
      }

      const stopEndTime = Date.now();
      const stopDuration = stopEndTime - stopStartTime;
      console.log(`✅ Test client stopped successfully (${stopDuration}ms)`);
    } catch (error) {
      const stopEndTime = Date.now();
      const stopDuration = stopEndTime - stopStartTime;
      console.warn(`⚠️ Warning: Could not stop test client process after ${stopDuration}ms:`, error.message);
    }
  }

  const teardownEndTime = Date.now();
  const totalTeardownTime = teardownEndTime - teardownStartTime;
  console.log(`🎯 Total teardown time: ${totalTeardownTime}ms (${(totalTeardownTime/1000).toFixed(1)}s)`);

  return null;
}

module.exports = globalTeardown;
