// Re-export types from generated client for convenience
export type {
    RegistrationRequest,
    RegistrationCompleteRequest,
    RegistrationResponse,
    RegistrationCompleteResponse,
    AuthenticationRequest,
    AuthenticationCompleteRequest,
    AuthenticationResponse,
    AuthenticationCompleteResponse,
    ErrorResponse,
    HealthResponse
} from '../generated-client/src';

// WebAuthn Client specific types
export interface WebAuthnClientOptions {
    serverUrl?: string;
}

export interface WebAuthnResult {
    success: boolean;
    message: string;
    username?: string;
}

export interface ConnectionTestResult {
    success: boolean;
    message: string;
}

// SimpleWebAuthn Browser types (for compatibility)
export interface SimpleWebAuthnBrowser {
    startRegistration: (options: any) => Promise<any>;
    startAuthentication: (options: any) => Promise<any>;
}

// Global SimpleWebAuthn interface
declare global {
    interface Window {
        SimpleWebAuthnBrowser: SimpleWebAuthnBrowser;
    }
}