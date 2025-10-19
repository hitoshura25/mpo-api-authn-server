package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.error.InstanceCreationException
import org.koin.core.qualifier.named
import org.koin.test.KoinTest
import org.koin.test.get
import kotlin.test.assertEquals

@TestInstance(TestInstance.Lifecycle.PER_METHOD)
class StorageModuleTest : KoinTest {
    @AfterEach
    fun cleanup() {
        clearAllTestProperties()
        stopKoin()
    }

    // Redis Configuration Tests using Koin DI with direct get() calls
    @Test
    fun `Redis host configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_HOST, "redis-test.example.com")

        startKoin {
            modules(storageModule)
        }

        val redisHost = get<String>(named("redisHost"))
        assertEquals("redis-test.example.com", redisHost)
    }

    @Test
    fun `Should throw InstanceCreationException when Redis host is not configured in DI`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("redisHost"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Redis host is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_HOST, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("redisHost"))
        }
    }

    @Test
    fun `Redis port configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT, "6380")

        startKoin {
            modules(storageModule)
        }

        val redisPort = get<Int>(named("redisPort"))
        assertEquals(6380, redisPort)
    }

    @Test
    fun `Should use default value when Redis port not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        val redisPort = get<Int>(named("redisPort"))
        assertEquals(6379, redisPort)
    }

    @Test
    fun `Should throw Exception when Redis port is not a integer`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT, "not-a-number")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("redisPort"))
        }
    }

    @Test
    fun `Should throw Exception when Redis port is below port number range`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT, "0")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("redisPort"))
        }
    }

    @Test
    fun `Should throw Exception when Redis port is above port number range`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT, "65536")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("redisPort"))
        }
    }

    @Test
    fun `Should throw Exception when Redis port is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("redisPort"))
        }
    }

    @Test
    fun `Redis password should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD, "test-password")

        startKoin {
            modules(storageModule)
        }

        val redisPassword = get<String>(named("redisPassword"))
        assertEquals("test-password", redisPassword)
    }

    @Test
    fun `Should throw InstanceCreationException when Redis password not configured`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("redisPassword"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Redis password is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("redisPassword"))
        }
    }

    @Test
    fun `Redis database configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "3")

        startKoin {
            modules(storageModule)
        }

        val redisDatabase = get<Int>(named("redisDatabase"))
        assertEquals(3, redisDatabase)
    }

    @Test
    fun `Should use default value for Redis database when not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        val redisDatabase = get<Int>(named("redisDatabase"))
        assertEquals(0, redisDatabase)
    }

    @Test
    fun `Should throw InstanceCreationException when redis database is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisDatabase"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when redis database is not an integer`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "invalid-value")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisDatabase"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when redis database is below range value`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "-1")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisDatabase"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when redis database is above range value`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE, "16")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisDatabase"))
        }
    }

    @Test
    fun `Redis max connections should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS, "25")

        startKoin {
            modules(storageModule)
        }

        val redisMaxConnections = get<Int>(named("redisMaxConnections"))
        assertEquals(25, redisMaxConnections)
    }

    @Test
    fun `Should throw InstanceCreationException when redis max connections is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisMaxConnections"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when redis max connections is invalid value`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS, "not-a-number")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<Int>(named("redisMaxConnections"))
        }
    }

    @Test
    fun `Database host configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_HOST, "postgres-test.example.com")

        startKoin {
            modules(storageModule)
        }

        val dbHost = get<String>(named("dbHost"))
        assertEquals("postgres-test.example.com", dbHost)
    }

    @Test
    fun `Should throw InstanceCreationException when Database host not configured in DI`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbHost"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Database host is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_HOST, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbHost"))
        }
    }

    @Test
    fun `Database port configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT, "5433")

        startKoin {
            modules(storageModule)
        }

        val dbPort = get<Int>(named("dbPort"))
        assertEquals(5433, dbPort)
    }

    @Test
    fun `Should use default value when Database port not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        val dbPort = get<Int>(named("dbPort"))
        assertEquals(5432, dbPort)
    }

    @Test
    fun `Should throw Exception when Database port is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbPort"))
        }
    }

    @Test
    fun `Should throw Exception when Database port is not an integer`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT, "not-a-number")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbPort"))
        }
    }

    @Test
    fun `Should throw Exception when Database port is below port number range`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT, "-1")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbPort"))
        }
    }

    @Test
    fun `Should throw Exception when Datbase port is above port number range`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT, "65536")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbPort"))
        }
    }

    @Test
    fun `Database name configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_NAME, "test_webauthn_db")

        startKoin {
            modules(storageModule)
        }

        val dbName = get<String>(named("dbName"))
        assertEquals("test_webauthn_db", dbName)
    }

    @Test
    fun `Database name configuration should be default when not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        val dbName = get<String>(named("dbName"))
        assertEquals("webauthn", dbName)
    }

    @Test
    fun `Should throw InstanceCreationException when Database name is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_NAME, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbName"))
        }
    }

    @Test
    fun `Database username configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_USERNAME, "test_user")

        startKoin {
            modules(storageModule)
        }

        val dbUsername = get<String>(named("dbUsername"))
        assertEquals("test_user", dbUsername)
    }

    @Test
    fun `Should throw InstanceCreationException when DB username not configured`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbUsername"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Database username is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_USERNAME, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbUsername"))
        }
    }

    @Test
    fun `Database password configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PASSWORD, "test_password")

        startKoin {
            modules(storageModule)
        }

        val dbPassword = get<String>(named("dbPassword"))
        assertEquals("test_password", dbPassword)
    }

    @Test
    fun `Should throw InstanceCreationException when DB password not configured`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbPassword"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Database password is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_PASSWORD, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("dbPassword"))
        }
    }

    @Test
    fun `Database max pool size configuration should work through Koin DI`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE, "20")

        startKoin {
            modules(storageModule)
        }

        val dbMaxPoolSize = get<Int>(named("dbMaxPoolSize"))
        assertEquals(20, dbMaxPoolSize)
    }

    @Test
    fun `Should throw Exception when Database max pool size is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE, "")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbMaxPoolSize"))
        }
    }

    @Test
    fun `Should throw Exception when Database max pool size is invalid value`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE, "not-a-number")

        startKoin {
            modules(storageModule)
        }

        assertThrows<Exception> {
            get<Int>(named("dbMaxPoolSize"))
        }
    }

    private fun clearAllTestProperties() {
        val properties =
            listOf(
                EnvironmentVariables.MPO_AUTHN_REDIS_HOST,
                EnvironmentVariables.MPO_AUTHN_REDIS_PORT,
                EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD,
                EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE,
                EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS,
                EnvironmentVariables.MPO_AUTHN_DB_HOST,
                EnvironmentVariables.MPO_AUTHN_DB_PORT,
                EnvironmentVariables.MPO_AUTHN_DB_NAME,
                EnvironmentVariables.MPO_AUTHN_DB_USERNAME,
                EnvironmentVariables.MPO_AUTHN_DB_PASSWORD,
                EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE,
            )
        properties.forEach { System.clearProperty(it) }
    }
}
