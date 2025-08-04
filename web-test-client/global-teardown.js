// Global teardown for Playwright tests
async function globalTeardown() {
  const teardownStartTime = Date.now();
  console.log('🧹 Cleaning up WebAuthn test environment...');

  // Clean up the test client web application process
  if (global.testClientProcess && !global.testClientProcess.exitCode) {
    console.log('🔌 Stopping test client web application...');
    const stopStartTime = Date.now();
    
    try {
      // Send SIGTERM for graceful shutdown
      global.testClientProcess.kill('SIGTERM');

      // Wait for process to exit naturally using a Promise-based approach
      const processExited = await new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(false), 3000); // 3 second timeout
        
        global.testClientProcess.on('exit', () => {
          clearTimeout(timeout);
          resolve(true);
        });
        
        // Handle case where process is already exited
        if (global.testClientProcess.exitCode !== null) {
          clearTimeout(timeout);
          resolve(true);
        }
      });

      if (!processExited) {
        console.log('⚡ Process still running, force killing...');
        global.testClientProcess.kill('SIGKILL');
        
        // Wait for SIGKILL to take effect
        await new Promise((resolve) => {
          const forceTimeout = setTimeout(resolve, 1000);
          global.testClientProcess.on('exit', () => {
            clearTimeout(forceTimeout);
            resolve();
          });
        });
      }

      console.log('✅ Test client stopped successfully');
    } catch (error) {
      console.warn('⚠️ Warning: Could not stop test client process:', error.message);
      
      // Try to kill any remaining processes on port 8082
      try {
        const { spawn } = require('child_process');
        const killProcess = spawn('pkill', ['-f', 'port.*8082'], { stdio: 'ignore' });
        await new Promise(resolve => {
          killProcess.on('close', resolve);
          setTimeout(resolve, 1000); // Timeout after 1 second
        });
      } catch (killError) {
        // Ignore errors from pkill - it's a cleanup attempt
      }
    } finally {
      const stopEndTime = Date.now();
      const stopDuration = stopEndTime - stopStartTime;
      console.log(`🔌 Process cleanup completed (${stopDuration}ms)`);
    }
  }

  const teardownEndTime = Date.now();
  const totalTeardownTime = teardownEndTime - teardownStartTime;
  console.log(`🎯 Total teardown time: ${totalTeardownTime}ms (${(totalTeardownTime/1000).toFixed(1)}s)`);

  return null;
}

module.exports = globalTeardown;
