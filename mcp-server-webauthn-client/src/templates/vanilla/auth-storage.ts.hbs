/**
 * Authentication Storage Service
 *
 * Manages JWT token lifecycle using industry-standard libraries:
 * - jwt-decode: Safe JWT parsing and validation
 * - sessionStorage: Browser-native session storage
 *
 * Security Features:
 * - Automatic expiration checking via jwt-decode
 * - Graceful handling of malformed tokens
 * - Session cleared on browser tab close (better security)
 */

import { jwtDecode } from 'jwt-decode';

export interface AuthSession {
    accessToken: string;
    tokenType: string;
    expiresIn: number;
    username: string;
    issuedAt: number;
}

export class AuthStorage {
    private static readonly STORAGE_KEY = 'webauthn_auth_session';

    /**
     * Store authentication session
     * Uses browser sessionStorage (cleared on tab close)
     */
    static store(session: Omit<AuthSession, 'issuedAt'>): void {
        const fullSession: AuthSession = {
            ...session,
            issuedAt: Date.now()
        };

        // Store in sessionStorage with JSON serialization
        sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify(fullSession));

        console.log('✅ Auth session stored:', {
            username: fullSession.username,
            expiresIn: fullSession.expiresIn,
            tokenType: fullSession.tokenType
        });
    }

    /**
     * Get current authentication session
     * Uses jwt-decode for safe token parsing and expiration validation
     */
    static get(): AuthSession | null {
        const sessionJson = sessionStorage.getItem(this.STORAGE_KEY);
        if (!sessionJson) return null;

        try {
            const session: AuthSession = JSON.parse(sessionJson);

            // Use jwt-decode to safely extract and validate token structure
            // This prevents crashes from malformed tokens
            const decoded = jwtDecode<{ exp: number }>(session.accessToken);

            // Check if token is expired using decoded 'exp' claim
            // exp is in seconds since epoch, Date.now() is in milliseconds
            if (decoded.exp && decoded.exp * 1000 < Date.now()) {
                console.warn('⚠️ Token expired, clearing session');
                this.clear();
                return null;
            }

            return session;
        } catch (error) {
            // jwt-decode throws on malformed tokens
            console.error('❌ Failed to parse JWT (malformed token):', error);
            this.clear();
            return null;
        }
    }

    /**
     * Get Authorization header value
     */
    static getAuthorizationHeader(): string | null {
        const session = this.get();
        if (!session) return null;
        return `${session.tokenType} ${session.accessToken}`;
    }

    /**
     * Check if user is authenticated
     */
    static isAuthenticated(): boolean {
        return this.get() !== null;
    }

    /**
     * Clear authentication session (logout)
     */
    static clear(): void {
        sessionStorage.removeItem(this.STORAGE_KEY);
        console.log('🔓 Auth session cleared');
    }

    /**
     * Get time remaining until token expires (in seconds)
     * Uses jwt-decode to extract exp claim
     */
    static getTimeRemaining(): number | null {
        const sessionJson = sessionStorage.getItem(this.STORAGE_KEY);
        if (!sessionJson) return null;

        try {
            const session: AuthSession = JSON.parse(sessionJson);
            const decoded = jwtDecode<{ exp: number }>(session.accessToken);
            if (!decoded.exp) return null;

            // exp is in seconds, Date.now() is in milliseconds
            const remaining = Math.max(0, decoded.exp - Math.floor(Date.now() / 1000));
            return remaining;
        } catch {
            // Malformed token - return null
            return null;
        }
    }

    /**
     * Get token expiration as Date object
     * Useful for displaying exact expiration time
     */
    static getExpirationDate(): Date | null {
        const sessionJson = sessionStorage.getItem(this.STORAGE_KEY);
        if (!sessionJson) return null;

        try {
            const session: AuthSession = JSON.parse(sessionJson);
            const decoded = jwtDecode<{ exp: number }>(session.accessToken);
            if (!decoded.exp) return null;

            return new Date(decoded.exp * 1000);
        } catch {
            return null;
        }
    }

    /**
     * Decode JWT payload (for debugging/inspection)
     * SECURITY: Only use for non-sensitive data - JWT is NOT encrypted!
     */
    static decodeToken(): any | null {
        const sessionJson = sessionStorage.getItem(this.STORAGE_KEY);
        if (!sessionJson) return null;

        try {
            const session: AuthSession = JSON.parse(sessionJson);
            return jwtDecode(session.accessToken);
        } catch {
            return null;
        }
    }
}
