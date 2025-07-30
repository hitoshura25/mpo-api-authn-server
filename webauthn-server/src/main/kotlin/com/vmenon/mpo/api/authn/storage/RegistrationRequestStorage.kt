package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions

/**
 * Interface for storing temporary WebAuthn registration requests with TTL support
 */
interface RegistrationRequestStorage {
    /**
     * Store a registration request with TTL
     * @param requestId unique identifier for the request
     * @param options the registration options to store
     * @param ttlSeconds time to live in seconds (default 5 minutes)
     */
    suspend fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long = 300,
    )

    /**
     * Retrieve and remove a registration request
     * @param requestId the request identifier
     * @return the stored options or null if not found/expired
     */
    suspend fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions?

    /**
     * Close/cleanup resources
     */
    fun close()
}
