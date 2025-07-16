package com.vmenon.mpo.api.authn.yubico

import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.vmenon.mpo.api.authn.storage.postgresql.SecurePostgreSQLCredentialStorage
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.KeyGenerator
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.testcontainers.containers.BindMode
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.utility.DockerImageName

@Testcontainers
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class CredentialsRepositoryImplTest {
    companion object {
        @Container
        val postgres = PostgreSQLContainer(DockerImageName.parse("postgres:15-alpine"))
            .withDatabaseName("webauthn_test")
            .withUsername("test_user")
            .withPassword("test_password")
            .withFileSystemBind(
                "src/main/resources/db/migration",
                "/docker-entrypoint-initdb.d",
                BindMode.READ_ONLY
            )
    }

    private lateinit var credentialStorage: CredentialStorage
    private lateinit var credentialRepositoryImpl: CredentialRepositoryImpl
    private lateinit var encryptionKey: String

    @BeforeAll
    fun setupContainers() {
        // Start containers
        postgres.start()
        println("PostgreSQL URL: ${postgres.jdbcUrl}")

        val keyGen = KeyGenerator.getInstance("AES")
        keyGen.init(256)
        val secretKey = keyGen.generateKey()
        encryptionKey = Base64.getEncoder().encodeToString(secretKey.encoded)
    }

    @AfterAll
    fun tearDownContainers() {
        postgres.stop()
    }

    @BeforeEach
    fun setupTest() {
        credentialStorage = SecurePostgreSQLCredentialStorage.create(
            host = postgres.host,
            port = postgres.getMappedPort(5432),
            database = postgres.databaseName,
            username = postgres.username,
            password = postgres.password,
            maxPoolSize = 10,
            encryptionKeyBase64 = encryptionKey
        )

        // Clear all data from tables before each test
        clearDatabase()

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

        val storedCredentials = credentialRepositoryImpl.lookupAll(registration.credential.credentialId)
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

        val storedCredential = credentialRepositoryImpl.lookup(
            ByteArray(credentialId),
            ByteArray(userHandle)
        )
        assertTrue(storedCredential.isEmpty())
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

        val userAccount = UserAccount(
            username = username,
            displayName = userDisplayName,
            userHandle = userHandle
        )

        val registration = CredentialRegistration(
            userAccount = userAccount,
            credential = RegisteredCredential.builder()
                .credentialId(ByteArray(credentialId))
                .userHandle(userAccount.userHandle)
                .publicKeyCose(ByteArray(publicKeyCose))
                .signatureCount(1337)
                .build()
        )

        credentialStorage.addRegistration(registration)
        return registration
    }

    private fun clearDatabase() {
        postgres.createConnection("").use { connection ->
            connection.createStatement().use { statement ->
                statement.execute("TRUNCATE TABLE webauthn_credentials_secure CASCADE")
                statement.execute("TRUNCATE TABLE webauthn_users_secure CASCADE")
            }
        }
    }
}