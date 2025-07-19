// Global setup for Playwright tests
const { chromium } = require('@playwright/test');
const { spawn } = require('child_process');

let testClientProcess = null;

async function globalSetup() {
  console.log('🚀 Setting up WebAuthn test environment...');

  // Start the test client web application
  console.log('🌐 Starting test client web application...');
  testClientProcess = spawn('npm', ['start'], {
    cwd: __dirname,
    stdio: 'inherit',
    detached: false
  });

  // Wait a moment for the test client to start
  await new Promise(resolve => setTimeout(resolve, 3000));

  // Wait for test client to be ready
  console.log('⏳ Waiting for test client to be ready...');
  const maxClientRetries = 15;
  const retryDelay = 1000;

  for (let i = 0; i < maxClientRetries; i++) {
    try {
      const response = await fetch('http://localhost:3000/health');
      if (response.ok) {
        console.log('✅ Test client is running and ready');
        break;
      }
    } catch (error) {
      console.log(`⏳ Test client not ready, retrying... (${i + 1}/${maxClientRetries})`);
    }

    if (i === maxClientRetries - 1) {
      console.error('❌ Test client failed to start');
      throw new Error('Test client is not ready');
    }

    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }

  // Wait for WebAuthn server to be ready
  console.log('⏳ Waiting for WebAuthn server to be ready...');

  const maxRetries = 30; // Wait up to 30 seconds

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:8080/health');
      if (response.ok) {
        console.log('✅ WebAuthn server is running and ready for tests');
        // Store the test client process so we can clean it up later
        global.testClientProcess = testClientProcess;
        return null;
      } else {
        console.log(`⏳ WebAuthn server responded with status ${response.status}, retrying... (${i + 1}/${maxRetries})`);
      }
    } catch (error) {
      console.log(`⏳ WebAuthn server not ready, retrying... (${i + 1}/${maxRetries})`);
    }

    // Wait before next retry
    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }

  // If we get here, server is not ready
  console.error('❌ WebAuthn server is not ready after 30 seconds');
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

module.exports = globalSetup;
