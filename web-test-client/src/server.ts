import express from 'express';
import path from 'path';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 8082; // Use 8082 to avoid conflict with webauthn-test-credentials-service on 8081

// Enable CORS for all routes
app.use(cors());

// Serve static files from the public directory (adjust path for compiled location)
app.use(express.static(path.join(__dirname, '../../public')));

// Serve bundled files from the dist directory root
app.use(express.static(path.join(__dirname, '../')));

// Serve compiled TypeScript files from dist directory
app.use('/dist', express.static(path.join(__dirname, '../')));

// Serve the main application
app.get('/', (req: express.Request, res: express.Response) => {
    res.sendFile(path.join(__dirname, '../../public', 'index.html'));
});

// Health check endpoint
app.get('/health', (req: express.Request, res: express.Response) => {
    res.json({
        status: 'ok',
        service: 'webauthn-web-test-client',
        timestamp: new Date().toISOString()
    });
});

app.listen(PORT, () => {
    console.log(`🚀 WebAuthn Test Client running at http://localhost:${PORT}`);
    console.log(`📋 Health check available at http://localhost:${PORT}/health`);
    console.log(`🔧 API Server should be running at http://localhost:8080`);
});