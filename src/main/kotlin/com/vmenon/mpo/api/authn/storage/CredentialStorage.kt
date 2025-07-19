package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.RegisteredCredential
import java.util.Optional

interface CredentialStorage {
    fun addRegistration(registration: CredentialRegistration)
    fun getRegistrationsByUsername(username: String): Set<CredentialRegistration>
    fun getUserByUsername(username: String): UserAccount?
    fun getUserByHandle(userHandle: com.yubico.webauthn.data.ByteArray): UserAccount?
    fun userExists(username: String): Boolean
    fun lookup(
        credentialId: com.yubico.webauthn.data.ByteArray,
        userHandle: com.yubico.webauthn.data.ByteArray
    ): Optional<RegisteredCredential>

    fun lookupAll(credentialId: com.yubico.webauthn.data.ByteArray): Set<RegisteredCredential>
    fun close()
}