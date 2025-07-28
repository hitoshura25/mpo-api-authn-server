package com.vmenon.mpo.api.authn.test_utils

import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import java.util.Optional
import java.util.concurrent.ConcurrentHashMap

class InMemoryCredentialStorage : CredentialStorage {
    private val storage = ConcurrentHashMap<String, MutableSet<CredentialRegistration>>()
    private val usersByHandle = ConcurrentHashMap<ByteArray, UserAccount>()

    override fun addRegistration(registration: CredentialRegistration) {
        val username = registration.userAccount.username
        storage.computeIfAbsent(username) { mutableSetOf() }.add(registration)
        usersByHandle[registration.userAccount.userHandle] = registration.userAccount
    }

    override fun getRegistrationsByUsername(username: String): Set<CredentialRegistration> {
        return storage[username] ?: emptySet()
    }

    override fun getUserByHandle(userHandle: ByteArray): UserAccount? {
        return usersByHandle[userHandle]
    }

    override fun getUserByUsername(username: String): UserAccount? {
        return storage[username]?.firstOrNull()?.userAccount
    }

    override fun userExists(username: String): Boolean {
        return storage.containsKey(username)
    }

    override fun lookup(credentialId: ByteArray, userHandle: ByteArray): Optional<RegisteredCredential> {
        val userAccount = getUserByHandle(userHandle) ?: return Optional.empty()

        return getRegistrationsByUsername(userAccount.username)
            .find { it.credential.credentialId == credentialId }
            ?.let { Optional.of(it.credential) }
            ?: Optional.empty()
    }

    override fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential> {
        return storage.values.flatten()
            .filter { it.credential.credentialId == credentialId }
            .map { it.credential }
            .toSet()
    }

    override fun close() {
        usersByHandle.clear()
        storage.clear()
    }
}