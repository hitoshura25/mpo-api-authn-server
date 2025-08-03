#!/usr/bin/env node
// Script to cleanup any processes running on port 8082

const { spawn } = require('child_process');

async function killProcessOnPort(port) {
  console.log(`🧹 Cleaning up processes on port ${port}...`);
  
  try {
    // Use lsof to find processes using the port
    const lsof = spawn('lsof', ['-ti', `:${port}`], { stdio: 'pipe' });
    
    let pids = '';
    lsof.stdout.on('data', (data) => {
      pids += data.toString();
    });
    
    await new Promise((resolve) => {
      lsof.on('close', (code) => {
        resolve(code);
      });
    });
    
    if (pids.trim()) {
      const pidList = pids.trim().split('\n').filter(pid => pid);
      console.log(`🔍 Found ${pidList.length} process(es) on port ${port}: ${pidList.join(', ')}`);
      
      for (const pid of pidList) {
        try {
          process.kill(parseInt(pid), 'SIGTERM');
          console.log(`📡 Sent SIGTERM to process ${pid}`);
        } catch (error) {
          console.warn(`⚠️ Could not kill process ${pid}:`, error.message);
        }
      }
      
      // Wait a moment for graceful shutdown
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Force kill any remaining processes
      for (const pid of pidList) {
        try {
          process.kill(parseInt(pid), 'SIGKILL');
          console.log(`⚡ Force killed process ${pid}`);
        } catch (error) {
          // Process probably already exited
        }
      }
      
      console.log(`✅ Port ${port} cleanup completed`);
    } else {
      console.log(`✅ No processes found on port ${port}`);
    }
  } catch (error) {
    console.warn(`⚠️ Error during cleanup:`, error.message);
  }
}

// If called directly, clean up port 8082
if (require.main === module) {
  killProcessOnPort(8082).then(() => {
    process.exit(0);
  }).catch(() => {
    process.exit(1);
  });
}

module.exports = { killProcessOnPort };