package com.vmenon.mpo.api.authn.testutils

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.TestInstance
import org.koin.core.context.stopKoin
import org.koin.test.KoinTest
import org.testcontainers.containers.BindMode
import org.testcontainers.containers.GenericContainer
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.utility.DockerImageName
import java.security.SecureRandom
import java.util.Base64

/**
 * Base class for integration tests that need PostgreSQL, Redis, and Jaeger containers.
 * Manages the lifecycle of shared test containers and provides common setup functionality.
 */
@Testcontainers
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
abstract class BaseIntegrationTest : KoinTest {
    companion object {
        /**
         * Generate secure test master encryption key.
         *
         * Supports optional environment variable override for reproducible tests:
         * - Set MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY for deterministic CI builds
         * - Omit for random key generation (better test isolation)
         *
         * Key requirements: 32 bytes (256 bits) for AES-256
         */
        private val testMasterKey: String by lazy {
            System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY) ?: run {
                val secureRandom = SecureRandom()
                val keyBytes = ByteArray(32) // 256 bits for AES-256
                secureRandom.nextBytes(keyBytes)
                Base64.getEncoder().encodeToString(keyBytes)
            }
        }
    }
    val postgres: PostgreSQLContainer<*> =
        PostgreSQLContainer(DockerImageName.parse("postgres:15-alpine"))
            .withDatabaseName("webauthn_test")
            .withUsername("test_user")
            .withPassword("test_password")
            .withFileSystemBind(
                "src/main/resources/db/migration",
                "/docker-entrypoint-initdb.d",
                BindMode.READ_ONLY,
            )

    val redis: GenericContainer<*> =
        GenericContainer(DockerImageName.parse("redis:7-alpine"))
            .withExposedPorts(6379)
            .withCommand("redis-server --requirepass test_password")

    val jaeger: GenericContainer<*> =
        GenericContainer(DockerImageName.parse("jaegertracing/all-in-one:1.53"))
            .withExposedPorts(14250, 16686)
            .withEnv("COLLECTOR_OTLP_ENABLED", "true")

    @BeforeAll
    fun startContainers() {
        postgres.start()
        redis.start()
        jaeger.start()
        println("PostgreSQL URL: ${postgres.jdbcUrl}")
        println("Redis Host: ${redis.host}:${redis.getMappedPort(6379)}")
        println("Jaeger UI: http://${jaeger.host}:${jaeger.getMappedPort(16686)}")
        println("Jaeger OTLP Endpoint: http://${jaeger.host}:${jaeger.getMappedPort(14250)}")
    }

    @AfterAll
    fun stopContainers() {
        postgres.stop()
        redis.stop()
        jaeger.stop()
    }

    @BeforeEach
    fun setupBaseTest() {
        setupTestEnvironmentVariables()
    }

    @AfterEach
    fun cleanupBaseTest() {
        clearDatabase()
        clearTestEnvironmentVariables()
    }

    /**
     * Sets up environment variables for the test containers.
     * Should be called in test setup methods.
     */
    protected fun setupTestEnvironmentVariables() {
        stopKoin() // Ensure clean state

        // Redis configuration
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_HOST, redis.host)
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_REDIS_PORT,
            redis.getMappedPort(6379).toString(),
        )
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD, "test_password")
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "0")

        // PostgreSQL configuration
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_HOST, postgres.host)
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_DB_PORT,
            postgres.getMappedPort(5432).toString(),
        )
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_NAME, postgres.databaseName)
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_USERNAME, postgres.username)
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PASSWORD, postgres.password)

        // OpenTelemetry/Jaeger configuration
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT,
            "http://${jaeger.host}:${jaeger.getMappedPort(14250)}",
        )
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME,
            "mpo-authn-server-test",
        )

        // JWT Key Rotation configuration
        // Use securely generated test key (supports env var override for reproducible tests)
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY,
            testMasterKey,
        )
    }

    /**
     * Clears test environment variables.
     * Should be called in test cleanup methods.
     */
    private fun clearTestEnvironmentVariables() {
        stopKoin()

        val properties =
            listOf(
                EnvironmentVariables.MPO_AUTHN_REDIS_HOST,
                EnvironmentVariables.MPO_AUTHN_REDIS_PORT,
                EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD,
                EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE,
                EnvironmentVariables.MPO_AUTHN_DB_HOST,
                EnvironmentVariables.MPO_AUTHN_DB_PORT,
                EnvironmentVariables.MPO_AUTHN_DB_NAME,
                EnvironmentVariables.MPO_AUTHN_DB_USERNAME,
                EnvironmentVariables.MPO_AUTHN_DB_PASSWORD,
                EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT,
                EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME,
                EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY,
            )
        properties.forEach { System.clearProperty(it) }
    }

    private fun clearDatabase() {
        postgres.createConnection("").use { connection ->
            connection.createStatement().use { statement ->
                // Clear JWT rotation tables (must be before jwt_signing_keys due to FK constraint)
                statement.execute("TRUNCATE TABLE jwt_key_audit_log CASCADE")
                statement.execute("TRUNCATE TABLE jwt_signing_keys CASCADE")
                // Clear WebAuthn tables
                statement.execute("TRUNCATE TABLE webauthn_credentials_secure CASCADE")
                statement.execute("TRUNCATE TABLE webauthn_users_secure CASCADE")
            }
        }
    }
}
