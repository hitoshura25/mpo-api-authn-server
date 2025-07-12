package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.CredentialRepository
import com.yubico.webauthn.data.ByteArray

/**
 * Interface for credential repository to support multiple implementations
 */
interface ScalableCredentialRepository : CredentialRepository {

    /**
     * Add a new credential registration
     */
    fun addRegistration(registration: CredentialRegistration)

    /**
     * Get all registrations for a username
     */
    fun getRegistrationsByUsername(username: String): Set<CredentialRegistration>

    /**
     * Get user account by user handle
     */
    fun getUserByHandle(userHandle: ByteArray): UserAccount?

    /**
     * Get user account by username
     */
    fun getUserByUsername(username: String): UserAccount?

    /**
     * Close/cleanup resources
     */
    fun close()
}
