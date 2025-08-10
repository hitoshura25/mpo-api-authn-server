package com.vmenon.mpo.api.authn.yubico

import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.vmenon.mpo.api.authn.storage.postgresql.DatabaseConfig
import com.vmenon.mpo.api.authn.storage.postgresql.createQuantumSafeCredentialStorage
import com.vmenon.mpo.api.authn.testutils.BaseIntegrationTest
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.security.SecureRandom
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class CredentialsRepositoryImplTest : BaseIntegrationTest() {
    private lateinit var credentialStorage: CredentialStorage
    private lateinit var credentialRepositoryImpl: CredentialRepositoryImpl

    @BeforeEach
    fun setupTest() {
        credentialStorage =
            createQuantumSafeCredentialStorage(
                DatabaseConfig(
                    host = postgres.host,
                    port = postgres.getMappedPort(5432),
                    database = postgres.databaseName,
                    username = postgres.username,
                    password = postgres.password,
                    maxPoolSize = 5,
                ),
            )

        credentialRepositoryImpl = CredentialRepositoryImpl(credentialStorage)
    }

    @Test
    fun testGetUsernameForUserHandleReturnsValidUserIfInStorage() {
        val username = "integration_test_user"
        val displayName = "Integration Test User"
        val userHandle = ByteArray(64)

        SecureRandom().nextBytes(userHandle)
        val userHandleByteArray = ByteArray(userHandle)
        addRegistration(username, displayName, userHandleByteArray)

        val storedUser = credentialRepositoryImpl.getUsernameForUserHandle(userHandleByteArray)
        assertEquals(username, storedUser.get())
    }

    @Test
    fun testGetUsernameForUserHandleReturnsNoUserIfNotInStorage() {
        val userHandle = ByteArray(64)

        SecureRandom().nextBytes(userHandle)
        val userHandleByteArray = ByteArray(userHandle)

        val storedUser = credentialRepositoryImpl.getUsernameForUserHandle(userHandleByteArray)
        assertTrue(storedUser.isEmpty)
    }

    @Test
    fun testGetUserHandleForUsernameReturnsNoUserIfNotInStorage() {
        val username = "integration_test_user"
        val storedUserHandle = credentialRepositoryImpl.getUserHandleForUsername(username)
        assertTrue(storedUserHandle.isEmpty)
    }

    @Test
    fun testLookupAllReturnsValidCredentialsIfInStorage() {
        val username = "integration_test_user"
        val displayName = "Integration Test User"
        val userHandle = ByteArray(64)

        SecureRandom().nextBytes(userHandle)
        val userHandleByteArray = ByteArray(userHandle)
        val registration = addRegistration(username, displayName, userHandleByteArray)

        val storedCredentials =
            credentialRepositoryImpl.lookupAll(
                registration.credential.credentialId,
            )
        assertEquals(registration.credential.credentialId, storedCredentials.first().credentialId)
    }

    @Test
    fun testLookupAllReturnsNoCredentialsIfNotInStorage() {
        val credentialId = ByteArray(64)
        SecureRandom().nextBytes(credentialId)
        val storedCredentials = credentialRepositoryImpl.lookupAll(ByteArray(credentialId))
        assertTrue(storedCredentials.isEmpty())
    }

    @Test
    fun testLookupReturnsNoCredentialsIfNotInStorage() {
        val credentialId = ByteArray(64)
        SecureRandom().nextBytes(credentialId)

        val userHandle = ByteArray(64)
        SecureRandom().nextBytes(userHandle)

        val storedCredential =
            credentialRepositoryImpl.lookup(
                ByteArray(credentialId),
                ByteArray(userHandle),
            )
        assertTrue(storedCredential.isEmpty)
    }

    private fun addRegistration(
        username: String,
        userDisplayName: String,
        userHandle: ByteArray,
    ): CredentialRegistration {
        val credentialId = ByteArray(64)
        val publicKeyCose = ByteArray(256)

        SecureRandom().nextBytes(credentialId)
        SecureRandom().nextBytes(publicKeyCose)

        val userAccount =
            UserAccount(
                username = username,
                displayName = userDisplayName,
                userHandle = userHandle,
            )

        val registration =
            CredentialRegistration(
                userAccount = userAccount,
                credential =
                    RegisteredCredential.builder()
                        .credentialId(ByteArray(credentialId))
                        .userHandle(userAccount.userHandle)
                        .publicKeyCose(ByteArray(publicKeyCose))
                        .signatureCount(1337)
                        .build(),
            )

        credentialStorage.addRegistration(registration)
        return registration
    }
}
