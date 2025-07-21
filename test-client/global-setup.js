// Global setup for Playwright tests
const { chromium } = require('@playwright/test');
const { spawn } = require('child_process');

let testClientProcess = null;

/**
 * Generic function to wait for a service to be ready with responsive polling
 */
async function waitForService(url, serviceName, maxWaitTimeMs = 15000) {
  const startTime = Date.now();
  const retryDelay = 100;
  const maxRetries = Math.floor(maxWaitTimeMs / retryDelay);

  console.log(`⏳ Waiting for ${serviceName} to be ready...`);

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        const endTime = Date.now();
        const waitDuration = endTime - startTime;
        console.log(`✅ ${serviceName} is running and ready (${waitDuration}ms)`);
        return waitDuration;
      } else {
        // Only log every 10th attempt to reduce noise (every 1 second)
        if (i % 10 === 0 || i > maxRetries * 0.7) {
          console.log(`⏳ ${serviceName} responded with status ${response.status}, retrying... (${Math.floor(i * retryDelay / 1000)}s)`);
        }
      }
    } catch (error) {
      // Only log every 10th attempt to reduce noise (every 1 second)
      if (i % 10 === 0 || i > maxRetries * 0.7) {
        console.log(`⏳ ${serviceName} not ready, retrying... (${Math.floor(i * retryDelay / 1000)}s)`);
      }
    }

    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }

  const failedTime = Date.now();
  const totalWaitTime = failedTime - startTime;
  throw new Error(`${serviceName} is not ready after ${totalWaitTime}ms`);
}

async function globalSetup() {
  const setupStartTime = Date.now();
  console.log('🚀 Setting up WebAuthn test environment...');

  // Start the test client web application
  console.log('🌐 Starting test client web application...');
  testClientProcess = spawn('npm', ['start'], {
    cwd: __dirname,
    stdio: 'inherit',
    detached: false
  });

  // Wait for test client to be ready
  try {
    await waitForService('http://localhost:8081/health', 'Test client', 15000);
  } catch (error) {
    console.error(`❌ ${error.message}`);
    throw new Error('Test client is not ready');
  }

  // Quick verification that the web application is serving correctly
  console.log('🔍 Verifying web application is serving correctly...');
  const appVerifyStartTime = Date.now();

  try {
    // Just check that the main page loads with correct content
    const response = await fetch('http://localhost:8081');
    const html = await response.text();

    if (!html.includes('WebAuthn Test Client')) {
      throw new Error('Web application does not contain expected content');
    }

    const appVerifyDuration = Date.now() - appVerifyStartTime;
    console.log(`✅ Web application verified successfully (${appVerifyDuration}ms)`);
  } catch (error) {
    throw new Error(`Web application verification failed: ${error.message}`);
  }

  // Wait for WebAuthn server to be ready
  try {
    await waitForService('http://localhost:8080/health', 'WebAuthn server', 30000);
  } catch (error) {
    console.error(`❌ ${error.message}`);
    console.error('   Please ensure the server is running with Docker Compose:');
    console.error('   npm run server:start');
    console.error('   Or check server logs with:');
    console.error('   npm run server:logs');
    console.error('   Check server status with:');
    console.error('   npm run server:status');

    // Clean up test client if WebAuthn server failed
    if (testClientProcess) {
      testClientProcess.kill('SIGTERM');
    }

    throw new Error('WebAuthn server is not ready. Please start the server with Docker Compose.');
  }

  const serverReadyTime = Date.now();
  const totalSetupTime = serverReadyTime - setupStartTime;
  console.log(`🎯 Total setup time: ${totalSetupTime}ms (${(totalSetupTime/1000).toFixed(1)}s)`);

  // Store the test client process so we can clean it up later
  global.testClientProcess = testClientProcess;
  return null;
}

module.exports = globalSetup;
