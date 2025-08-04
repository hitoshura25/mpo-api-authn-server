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

const server = app.listen(PORT, () => {
    console.log(`🚀 WebAuthn Test Client running at http://localhost:${PORT}`);
    console.log(`📋 Health check available at http://localhost:${PORT}/health`);
    console.log(`🔧 API Server should be running at http://localhost:8080`);
});

// Graceful shutdown handling
const gracefulShutdown = (signal: string) => {
    console.log(`📡 Received ${signal}. Starting graceful shutdown...`);
    
    server.close((err) => {
        if (err) {
            console.error('❌ Error during server shutdown:', err);
            process.exit(1);
        }
        
        console.log('✅ Server closed gracefully');
        process.exit(0);
    });
    
    // Force exit after 5 seconds if graceful shutdown fails
    setTimeout(() => {
        console.error('⚠️ Forced shutdown due to timeout');
        process.exit(1);
    }, 5000);
};

// Handle various termination signals
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT')); 
process.on('SIGUSR2', () => gracefulShutdown('SIGUSR2')); // For nodemon

// Handle uncaught exceptions and unhandled rejections
process.on('uncaughtException', (err) => {
    console.error('💥 Uncaught Exception:', err);
    gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
    gracefulShutdown('unhandledRejection');
});