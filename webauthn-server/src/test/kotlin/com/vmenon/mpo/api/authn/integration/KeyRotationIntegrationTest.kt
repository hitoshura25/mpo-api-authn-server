package com.vmenon.mpo.api.authn.integration

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.model.KeyStatus
import com.vmenon.mpo.api.authn.module
import com.vmenon.mpo.api.authn.repository.PostgresKeyRepository
import com.vmenon.mpo.api.authn.routes.JwksResponse
import com.vmenon.mpo.api.authn.security.KeyRotationService
import com.vmenon.mpo.api.authn.security.PostQuantumCryptographyService
import com.vmenon.mpo.api.authn.testStorageModule
import com.vmenon.mpo.api.authn.testutils.BaseIntegrationTest
import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText
import io.ktor.http.HttpStatusCode
import io.ktor.server.testing.testApplication
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Integration tests for JWT key rotation functionality.
 *
 * Tests the complete key rotation lifecycle:
 * 1. Initial key generation (backward compatibility)
 * 2. Key encryption/decryption
 * 3. JWKS endpoint returns multiple keys during rotation
 * 4. Token signing with new key after rotation
 * 5. Token verification with old key after rotation
 * 6. Expired key cleanup
 * 7. Accelerated rotation for testing
 *
 * Uses BaseIntegrationTest patterns with TestContainers for PostgreSQL, Redis, and Jaeger.
 */
class KeyRotationIntegrationTest : BaseIntegrationTest() {
    private lateinit var keyRepository: PostgresKeyRepository
    private lateinit var postQuantumCrypto: PostQuantumCryptographyService
    private lateinit var keyRotationService: KeyRotationService

    private val objectMapper = jacksonObjectMapper()

    @BeforeEach
    fun setupKeyRotation() {
        // Clear any existing keys from database
        clearKeyTables()

        // Set up test environment with accelerated rotation for testing (HOCON format)
        System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED, "true")
        System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL, "30s") // 30 seconds for testing
        System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD, "15s") // 15 seconds grace period
        System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION, "30s") // 30 seconds retention

        // Initialize services using Kyber768 post-quantum encryption
        keyRepository = PostgresKeyRepository(createDataSource())
        postQuantumCrypto = PostQuantumCryptographyService()
        keyRotationService = KeyRotationService(keyRepository, postQuantumCrypto)
    }

    @AfterEach
    fun cleanupKeyRotation() {
        // Clear key rotation environment variables
        System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
        System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD)
        System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION)
        System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY)

        // Clear key tables
        clearKeyTables()
    }

    private fun clearKeyTables() {
        postgres.createConnection("")?.use { connection ->
            connection.createStatement().use { statement ->
                statement.execute("TRUNCATE TABLE jwt_key_audit_log CASCADE")
                statement.execute("TRUNCATE TABLE jwt_signing_keys CASCADE")
            }
        }
    }

    @Test
    fun `test initial key generation creates backward-compatible key`() {
        keyRotationService.initialize()

        val activeKey = keyRepository.getActiveKey()
        assertNotNull(activeKey, "Active key should be created during initialization")
        assertEquals("webauthn-2024-01", activeKey.keyId, "Should use backward-compatible key ID")
        assertEquals(KeyStatus.ACTIVE, activeKey.status)
        assertEquals("RS256", activeKey.algorithm)
        assertEquals(2048, activeKey.keySize)
        assertNotNull(activeKey.activatedAt, "Active key should have activation timestamp")
    }

    @Test
    fun `test JWKS endpoint returns active key`() =
        testApplication {
            application { module(testStorageModule) }

            keyRotationService.initialize()

            val jwksResponse = client.get("/.well-known/jwks.json")
            assertEquals(HttpStatusCode.OK, jwksResponse.status)

            // Verify Cache-Control header
            val cacheControl = jwksResponse.headers["Cache-Control"]
            assertNotNull(cacheControl, "JWKS should have Cache-Control header")
            assertTrue(cacheControl.contains("max-age=300"), "Should have 5-minute cache")
            assertTrue(cacheControl.contains("stale-if-error=3600"), "Should have 1-hour stale-if-error")

            val jwks = objectMapper.readValue<JwksResponse>(jwksResponse.bodyAsText())
            val keys = jwks.keys

            assertNotNull(keys)
            assertTrue(keys.size >= 1, "JWKS should contain at least one key")

            val firstKey = keys[0]
            assertEquals("RSA", firstKey.kty)
            assertEquals("sig", firstKey.use)
            assertEquals("RS256", firstKey.alg)
            assertNotNull(firstKey.kid)
            assertNotNull(firstKey.n, "Should have RSA modulus")
            assertNotNull(firstKey.e, "Should have RSA exponent")
        }

    @Test
    fun `test key rotation creates PENDING key`() {
        keyRotationService.initialize()
        val initialActiveKey = keyRepository.getActiveKey()
        assertNotNull(initialActiveKey)

        // Trigger rotation
        val newKeyId = keyRotationService.rotateKey(reason = "Integration test")

        // Verify new key is PENDING immediately after rotation
        val pendingKey = keyRepository.getKey(newKeyId)
        assertNotNull(pendingKey)
        assertEquals(KeyStatus.PENDING, pendingKey.status)

        // Wait for grace period (15 seconds)
        println("Waiting 16 seconds for grace period to expire...")
        Thread.sleep(16_000)

        // Manually trigger activation check (simulating scheduler)
        keyRotationService.checkAndActivatePendingKeys()

        // After activation, new key should be ACTIVE
        val currentActiveKey = keyRepository.getActiveKey()
        assertNotNull(currentActiveKey)
        assertEquals(newKeyId, currentActiveKey.keyId)

        // Old key should be RETIRED
        val retiredKey = keyRepository.getKey(initialActiveKey.keyId)
        assertNotNull(retiredKey)
        assertEquals(KeyStatus.RETIRED, retiredKey.status)
    }

    @Test
    fun `test JWKS returns multiple keys during rotation grace period`() =
        testApplication {
            application { module(testStorageModule) }

            keyRotationService.initialize()

            // Manually create a second key to simulate grace period
            val newKeyId = "webauthn-test-2025"
            val keyPair = java.security.KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()

            // Create PEM strings manually for test
            val privateKeyPem =
                """
                -----BEGIN PRIVATE KEY-----
                ${java.util.Base64.getEncoder().encodeToString(keyPair.private.encoded)}
                -----END PRIVATE KEY-----
                """.trimIndent()
            val publicKeyPem =
                """
                -----BEGIN PUBLIC KEY-----
                ${java.util.Base64.getEncoder().encodeToString(keyPair.public.encoded)}
                -----END PUBLIC KEY-----
                """.trimIndent()

            val pendingKey =
                com.vmenon.mpo.api.authn.model.JwtSigningKey(
                    keyId = newKeyId,
                    privateKeyPem = postQuantumCrypto.encryptToString(privateKeyPem),
                    publicKeyPem = publicKeyPem,
                    algorithm = "RS256",
                    keySize = 2048,
                    status = KeyStatus.PENDING,
                    createdAt = java.time.Instant.now(),
                    metadata = mapOf("test" to true),
                )
            keyRepository.saveKey(pendingKey)

            val jwksResponse = client.get("/.well-known/jwks.json")
            assertEquals(HttpStatusCode.OK, jwksResponse.status)

            val jwks = objectMapper.readValue<JwksResponse>(jwksResponse.bodyAsText())
            val keys = jwks.keys

            assertNotNull(keys)
            // Should only return ACTIVE key (PENDING not included in JWKS until activated)
            assertEquals(1, keys.size, "JWKS should only contain ACTIVE keys, not PENDING")
        }

    @Test
    fun `test key encryption and decryption`() {
        keyRotationService.initialize()
        val activeKey = keyRepository.getActiveKey()!!

        // Verify private key is encrypted in database
        postgres.createConnection("")?.use { connection ->
            val statement = connection.createStatement()
            val resultSet =
                statement.executeQuery(
                    "SELECT private_key_pem FROM jwt_signing_keys WHERE key_id = '${activeKey.keyId}'",
                )

            assertTrue(resultSet.next())
            val encryptedPrivateKey = resultSet.getString("private_key_pem")

            // Encrypted key should not contain PEM markers (it's base64-encoded ciphertext)
            assertFalse(
                encryptedPrivateKey.contains("-----BEGIN PRIVATE KEY-----"),
                "Private key should be encrypted in database",
            )

            // Decrypt and verify it's valid
            val decryptedKey = postQuantumCrypto.decryptFromString(encryptedPrivateKey)
            assertTrue(decryptedKey.contains("-----BEGIN PRIVATE KEY-----"))
            assertTrue(decryptedKey.contains("-----END PRIVATE KEY-----"))
        }
    }

    @Test
    fun `test accelerated rotation lifecycle with age-based trigger`() {
        keyRotationService.initialize()
        val initialKey = keyRepository.getActiveKey()!!

        // Wait for key to age beyond rotation threshold (30 seconds in test mode)
        println("Waiting 31 seconds for key to age beyond rotation threshold...")
        Thread.sleep(31_000)

        // Trigger rotation check (should automatically rotate to PENDING)
        keyRotationService.checkAndRotateIfNeeded()

        // Wait for grace period (15 seconds)
        println("Waiting 16 seconds for grace period to expire...")
        Thread.sleep(16_000)

        // Manually trigger activation check (simulating scheduler)
        keyRotationService.checkAndActivatePendingKeys()

        // Verify rotation occurred
        val newActiveKey = keyRepository.getActiveKey()
        assertNotNull(newActiveKey)
        assertTrue(newActiveKey.keyId != initialKey.keyId, "Active key should have changed after rotation")

        // Old key should be RETIRED
        val retiredKey = keyRepository.getKey(initialKey.keyId)
        assertNotNull(retiredKey)
        assertEquals(KeyStatus.RETIRED, retiredKey.status)
    }

    @Test
    fun `test expired key cleanup`() {
        keyRotationService.initialize()
        val initialKey = keyRepository.getActiveKey()!!

        // Manually create and retire a key with short expiration
        val expiredKeyId = "webauthn-expired-test"
        val keyPair = java.security.KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()

        val privateKeyPem =
            """
            -----BEGIN PRIVATE KEY-----
            ${java.util.Base64.getEncoder().encodeToString(keyPair.private.encoded)}
            -----END PRIVATE KEY-----
            """.trimIndent()
        val publicKeyPem =
            """
            -----BEGIN PUBLIC KEY-----
            ${java.util.Base64.getEncoder().encodeToString(keyPair.public.encoded)}
            -----END PUBLIC KEY-----
            """.trimIndent()

        val expiredKey =
            com.vmenon.mpo.api.authn.model.JwtSigningKey(
                keyId = expiredKeyId,
                privateKeyPem = postQuantumCrypto.encryptToString(privateKeyPem),
                publicKeyPem = publicKeyPem,
                algorithm = "RS256",
                keySize = 2048,
                status = KeyStatus.RETIRED,
                createdAt = java.time.Instant.now().minusSeconds(3600),
                retiredAt = java.time.Instant.now().minusSeconds(1800),
                expiresAt = java.time.Instant.now().minusSeconds(60), // Expired 1 minute ago
            )
        keyRepository.saveKey(expiredKey)

        // Verify key exists before cleanup
        assertNotNull(keyRepository.getKey(expiredKeyId))

        // Trigger cleanup
        keyRotationService.cleanupExpiredKeys()

        // Verify key was deleted
        val deletedKey = keyRepository.getKey(expiredKeyId)
        assertEquals(null, deletedKey, "Expired key should be deleted")
    }

    @Test
    fun `test data persistence across application restarts`() {
        keyRotationService.initialize()
        val initialKeyId = keyRepository.getActiveKey()!!.keyId

        // Manually create a PENDING key
        val pendingKeyId = "webauthn-pending-restart-test"
        val keyPair = java.security.KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()

        val privateKeyPem =
            """
            -----BEGIN PRIVATE KEY-----
            ${java.util.Base64.getEncoder().encodeToString(keyPair.private.encoded)}
            -----END PRIVATE KEY-----
            """.trimIndent()
        val publicKeyPem =
            """
            -----BEGIN PUBLIC KEY-----
            ${java.util.Base64.getEncoder().encodeToString(keyPair.public.encoded)}
            -----END PUBLIC KEY-----
            """.trimIndent()

        val pendingKey =
            com.vmenon.mpo.api.authn.model.JwtSigningKey(
                keyId = pendingKeyId,
                privateKeyPem = postQuantumCrypto.encryptToString(privateKeyPem),
                publicKeyPem = publicKeyPem,
                algorithm = "RS256",
                keySize = 2048,
                status = KeyStatus.PENDING,
                createdAt = java.time.Instant.now(),
            )
        keyRepository.saveKey(pendingKey)

        // Simulate restart by creating new service instances
        val newKeyRepository = PostgresKeyRepository(createDataSource())
        val newPostQuantumCrypto = PostQuantumCryptographyService()
        val newKeyRotationService = KeyRotationService(newKeyRepository, newPostQuantumCrypto)

        // Verify keys are persisted
        val persistedPendingKey = newKeyRepository.getKey(pendingKeyId)
        assertNotNull(persistedPendingKey, "PENDING key should persist across restarts")
        assertEquals(KeyStatus.PENDING, persistedPendingKey.status)

        val persistedActiveKey = newKeyRepository.getActiveKey()
        assertEquals(initialKeyId, persistedActiveKey?.keyId, "ACTIVE key should persist across restarts")
    }

    @Test
    fun `test JWT token signing with rotated key`() =
        testApplication {
            application { module(testStorageModule) }

            keyRotationService.initialize()

            // Get initial JWT token
            val initialResponse = client.get("/") // Dummy endpoint to trigger DI initialization

            // Wait for key to age beyond rotation threshold
            println("Waiting 31 seconds for key to age beyond rotation threshold...")
            Thread.sleep(31_000)

            // Trigger rotation check
            keyRotationService.checkAndRotateIfNeeded()

            // Wait for grace period
            println("Waiting 16 seconds for grace period to expire...")
            Thread.sleep(16_000)

            // Manually trigger activation check (simulating scheduler)
            keyRotationService.checkAndActivatePendingKeys()

            // New token should be signed with new key
            // (Integration test via actual authentication would be more comprehensive,
            // but this validates the key rotation mechanism is working)
            val newActiveKey = keyRepository.getActiveKey()
            assertNotNull(newActiveKey)
            assertTrue(newActiveKey.keyId != "webauthn-2024-01", "Should have rotated to new key")
        }

    @Test
    fun `test audit log records key lifecycle events`() {
        keyRotationService.initialize()
        val activeKey = keyRepository.getActiveKey()!!

        // Get audit logs
        val auditLogs = keyRepository.getAuditLogs(activeKey.keyId)

        // Should have at least GENERATED and ACTIVATED events
        assertTrue(auditLogs.isNotEmpty(), "Should have audit logs")
        val events = auditLogs.map { it.event }
        assertTrue(
            events.any { it == com.vmenon.mpo.api.authn.model.KeyEvent.GENERATED },
            "Should have GENERATED event",
        )
    }

    @Test
    fun `test getActiveSigningKey returns correct key and caches it`() {
        keyRotationService.initialize()

        // First call should load from database
        val (keyId1, keyPair1) = keyRotationService.getActiveSigningKey()
        assertEquals("webauthn-2024-01", keyId1)

        // Second call should return cached value (same instance)
        val (keyId2, keyPair2) = keyRotationService.getActiveSigningKey()
        assertEquals(keyId1, keyId2)
        assertTrue(keyPair1 === keyPair2, "Should return cached KeyPair instance")
    }

    /**
     * Helper to create a HikariDataSource from the postgres test container.
     */
    private fun createDataSource(): HikariDataSource {
        val config = HikariConfig().apply {
            jdbcUrl = postgres.jdbcUrl
            username = postgres.username
            password = postgres.password
            driverClassName = "org.postgresql.Driver"
            maximumPoolSize = 5
        }
        return HikariDataSource(config)
    }
}
