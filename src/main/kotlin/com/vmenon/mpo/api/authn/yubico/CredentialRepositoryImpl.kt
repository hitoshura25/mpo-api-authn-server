package com.vmenon.mpo.api.authn.yubico

import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.yubico.webauthn.CredentialRepository
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredentialDescriptor
import java.util.Optional

class CredentialRepositoryImpl(private val credentialStorage: CredentialStorage) : CredentialRepository {
    override fun getCredentialIdsForUsername(username: String): Set<PublicKeyCredentialDescriptor?>? {
        return credentialStorage.getRegistrationsByUsername(username)
            .map { registration ->
                PublicKeyCredentialDescriptor.builder()
                    .id(registration.credential.credentialId)
                    .build()
            }
            .toSet()
    }

    override fun getUserHandleForUsername(username: String): Optional<ByteArray> {
        return Optional.ofNullable(credentialStorage.getUserByUsername(username)?.userHandle)
    }

    override fun getUsernameForUserHandle(userHandle: ByteArray): Optional<String> {
        return Optional.ofNullable(credentialStorage.getUserByHandle(userHandle)?.username)

    }

    override fun lookup(
        credentialId: ByteArray,
        userHandle: ByteArray
    ): Optional<RegisteredCredential> {
        return credentialStorage.lookup(credentialId, userHandle)
    }

    override fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential> {
        return credentialStorage.lookupAll(credentialId)
    }
}