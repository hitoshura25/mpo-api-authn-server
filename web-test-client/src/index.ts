// Main library exports
export { WebAuthnClient } from './webauthn-client';
export { initializeWebAuthnClient } from './webauthn-client';

// Type exports
export type {
    WebAuthnClientOptions,
    WebAuthnResult,
    ConnectionTestResult,
    SimpleWebAuthnBrowser,
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
} from './types';

// Re-export generated client types and classes for advanced usage
export {
    Configuration,
    RegistrationApi,
    AuthenticationApi,
    HealthApi
} from '../generated-client/src';

// Default export for UMD compatibility
import { WebAuthnClient, initializeWebAuthnClient } from './webauthn-client';
export default {
    WebAuthnClient,
    initializeWebAuthnClient
};