package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.RegisteredCredential
import java.util.Optional
import com.yubico.webauthn.data.ByteArray

interface CredentialStorage {
    fun addRegistration(registration: CredentialRegistration)

    fun getRegistrationsByUsername(username: String): Set<CredentialRegistration>

    fun getUserByUsername(username: String): UserAccount?

    fun getUserByHandle(userHandle: ByteArray): UserAccount?

    fun userExists(username: String): Boolean

    fun lookup(
        credentialId: ByteArray,
        userHandle: ByteArray,
    ): Optional<RegisteredCredential>

    fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential>

    fun close()
}
