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

      // Wait for graceful shutdown with polling instead of fixed timeout
      let attempts = 0;
      const maxAttempts = 20; // Max 2 seconds (20 * 100ms)

      while (attempts < maxAttempts && !global.testClientProcess.killed) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }

      // Force kill if still running after graceful period
      if (!global.testClientProcess.killed) {
        console.log('⚡ Process still running, force killing...');
        global.testClientProcess.kill('SIGKILL');
        // Give it a moment to process the SIGKILL
        await new Promise(resolve => setTimeout(resolve, 100));
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
