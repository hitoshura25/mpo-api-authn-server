// Global setup for Playwright tests
const { chromium } = require('@playwright/test');
const { spawn } = require('child_process');

let testClientProcess = null;

async function globalSetup() {
  const setupStartTime = Date.now();
  console.log('🚀 Setting up WebAuthn test environment...');

  // Start the test client web application
  console.log('🌐 Starting test client web application...');
  const clientStartTime = Date.now();
  testClientProcess = spawn('npm', ['start'], {
    cwd: __dirname,
    stdio: 'inherit',
    detached: false
  });

  // Wait a moment for the test client to start
  await new Promise(resolve => setTimeout(resolve, 3000));

  // Wait for test client to be ready
  console.log('⏳ Waiting for test client to be ready...');
  const clientWaitStartTime = Date.now();
  const maxClientRetries = 15;
  const retryDelay = 1000;

  for (let i = 0; i < maxClientRetries; i++) {
    try {
      const response = await fetch('http://localhost:8081/health');
      if (response.ok) {
        const clientReadyTime = Date.now();
        const clientWaitDuration = clientReadyTime - clientWaitStartTime;
        console.log(`✅ Test client is running and ready (${clientWaitDuration}ms)`);
        break;
      }
    } catch (error) {
      console.log(`⏳ Test client not ready, retrying... (${i + 1}/${maxClientRetries})`);
    }

    if (i === maxClientRetries - 1) {
      const failedTime = Date.now();
      const totalWaitTime = failedTime - clientWaitStartTime;
      console.error(`❌ Test client failed to start after ${totalWaitTime}ms`);
      throw new Error('Test client is not ready');
    }

    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }

  // Verify that the test client has SimpleWebAuthn loaded
  console.log('🔍 Verifying SimpleWebAuthn library is available...');
  const libraryCheckStartTime = Date.now();
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:8081');
    await page.waitForLoadState('networkidle');

    // Wait for SimpleWebAuthn library to load
    const isLibraryLoaded = await page.waitForFunction(() => {
      return typeof window.SimpleWebAuthnBrowser !== 'undefined';
    }, { timeout: 10000 });

    if (isLibraryLoaded) {
      const libraryLoadedTime = Date.now();
      const libraryCheckDuration = libraryLoadedTime - libraryCheckStartTime;
      console.log(`✅ SimpleWebAuthn library loaded successfully (${libraryCheckDuration}ms)`);
    } else {
      throw new Error('SimpleWebAuthn library failed to load');
    }

    // Verify the web application loads correctly
    console.log('🔍 Verifying web application loads correctly...');
    const appVerifyStartTime = Date.now();

    // Check page title
    const title = await page.title();
    if (title !== 'WebAuthn Test Client') {
      throw new Error(`Expected page title 'WebAuthn Test Client', got '${title}'`);
    }

    // Check main heading
    const heading = await page.locator('h1').textContent();
    if (!heading.includes('WebAuthn Passkey Test Client')) {
      throw new Error(`Expected heading to contain 'WebAuthn Passkey Test Client', got '${heading}'`);
    }

    // Wait for application to fully initialize
    await page.waitForFunction(() => {
      return document.getElementById('connectionStatus') &&
             document.querySelector('h1').textContent.includes('WebAuthn');
    }, { timeout: 10000 });

    const appVerifiedTime = Date.now();
    const appVerifyDuration = appVerifiedTime - appVerifyStartTime;
    console.log(`✅ Web application loaded and initialized successfully (${appVerifyDuration}ms)`);

  } finally {
    await page.close();
    await browser.close();
  }

  // Wait for WebAuthn server to be ready
  console.log('⏳ Waiting for WebAuthn server to be ready...');
  const serverWaitStartTime = Date.now();
  const maxRetries = 30; // Wait up to 30 seconds

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:8080/health');
      if (response.ok) {
        const serverReadyTime = Date.now();
        const serverWaitDuration = serverReadyTime - serverWaitStartTime;
        const totalSetupTime = serverReadyTime - setupStartTime;
        console.log(`✅ WebAuthn server is running and ready for tests (waited ${serverWaitDuration}ms)`);
        console.log(`🎯 Total setup time: ${totalSetupTime}ms (${(totalSetupTime/1000).toFixed(1)}s)`);

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
  const failedTime = Date.now();
  const totalWaitTime = failedTime - serverWaitStartTime;
  const totalSetupTime = failedTime - setupStartTime;
  console.error(`❌ WebAuthn server is not ready after ${totalWaitTime}ms (total setup time: ${totalSetupTime}ms)`);
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
