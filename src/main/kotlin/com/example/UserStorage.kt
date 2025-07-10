package com.example

import com.yubico.webauthn.CredentialRepository
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredentialDescriptor
import java.util.*
import java.util.concurrent.ConcurrentHashMap

data class UserAccount(
    val username: String,
    val displayName: String,
    val userHandle: ByteArray
)

data class CredentialRegistration(
    val userAccount: UserAccount,
    val credential: RegisteredCredential,
    val registrationTime: Long = System.currentTimeMillis()
)

class InMemoryCredentialRepository : CredentialRepository {
    private val storage = ConcurrentHashMap<String, MutableSet<CredentialRegistration>>()
    private val usersByHandle = ConcurrentHashMap<ByteArray, UserAccount>()

    fun addRegistration(registration: CredentialRegistration) {
        val username = registration.userAccount.username
        storage.computeIfAbsent(username) { mutableSetOf() }.add(registration)
        usersByHandle[registration.userAccount.userHandle] = registration.userAccount
    }

    fun getRegistrationsByUsername(username: String): Set<CredentialRegistration> {
        return storage[username] ?: emptySet()
    }

    fun getUserByHandle(userHandle: ByteArray): UserAccount? {
        return usersByHandle[userHandle]
    }

    fun getUserByUsername(username: String): UserAccount? {
        return storage[username]?.firstOrNull()?.userAccount
    }

    override fun getCredentialIdsForUsername(username: String): Set<PublicKeyCredentialDescriptor> {
        return getRegistrationsByUsername(username)
            .map { registration ->
                PublicKeyCredentialDescriptor.builder()
                    .id(registration.credential.credentialId)
                    .build()
            }
            .toSet()
    }

    override fun getUserHandleForUsername(username: String): Optional<ByteArray> {
        return Optional.ofNullable(getUserByUsername(username)?.userHandle)
    }

    override fun getUsernameForUserHandle(userHandle: ByteArray): Optional<String> {
        return Optional.ofNullable(getUserByHandle(userHandle)?.username)
    }

    override fun lookup(credentialId: ByteArray, userHandle: ByteArray): Optional<RegisteredCredential> {
        val user = getUserByHandle(userHandle) ?: return Optional.empty()

        return storage[user.username]
            ?.find { it.credential.credentialId == credentialId }
            ?.let { Optional.of(it.credential) }
            ?: Optional.empty()
    }

    override fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential> {
        return storage.values
            .flatten()
            .filter { it.credential.credentialId == credentialId }
            .map { it.credential }
            .toSet()
    }
}
