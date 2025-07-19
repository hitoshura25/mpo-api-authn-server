// Global setup for Playwright tests
const { chromium } = require('@playwright/test');

async function globalSetup() {
  console.log('🚀 Setting up WebAuthn test environment...');

  // Wait for server to be ready (it should be started via Docker Compose)
  console.log('⏳ Waiting for server to be ready...');

  const maxRetries = 30; // Wait up to 30 seconds
  const retryDelay = 1000; // 1 second between retries

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:8080/health');
      if (response.ok) {
        console.log('✅ Server is running and ready for tests');
        return null;
      } else {
        console.log(`⏳ Server responded with status ${response.status}, retrying... (${i + 1}/${maxRetries})`);
      }
    } catch (error) {
      console.log(`⏳ Server not ready, retrying... (${i + 1}/${maxRetries})`);
    }

    // Wait before next retry
    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }

  // If we get here, server is not ready
  console.error('❌ Server is not ready after 30 seconds');
  console.error('   Please ensure the server is running with Docker Compose:');
  console.error('   npm run server:start');
  console.error('   Or check server logs with:');
  console.error('   npm run server:logs');
  console.error('   Check server status with:');
  console.error('   npm run server:status');

  throw new Error('Server is not ready. Please start the server with Docker Compose.');
}

module.exports = globalSetup;
