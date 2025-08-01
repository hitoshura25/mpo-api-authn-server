const express = require('express');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 8082; // Use 8082 to avoid conflict with webauthn-test-credentials-service on 8081

// Enable CORS for all routes
app.use(cors());

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve the main application
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'webauthn-test-client',
        timestamp: new Date().toISOString()
    });
});

app.listen(PORT, () => {
    console.log(`🚀 WebAuthn Test Client running at http://localhost:${PORT}`);
    console.log(`📋 Health check available at http://localhost:${PORT}/health`);
    console.log(`🔧 API Server should be running at http://localhost:8080`);
});
