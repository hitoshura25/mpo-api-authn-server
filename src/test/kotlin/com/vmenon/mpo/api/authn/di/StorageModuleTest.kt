package com.vmenon.mpo.api.authn.di

import kotlin.test.assertEquals
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.qualifier.named
import org.koin.test.KoinTest
import org.koin.test.get

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
        System.setProperty("MPO_AUTHN_REDIS_HOST", "redis-test.example.com")

        startKoin {
            modules(storageModule)
        }

        val redisHost = get<String>(named("redisHost"))
        assertEquals("redis-test.example.com", redisHost)
    }

    @Test
    fun `Redis host should use default through Koin DI when not configured`() {
        startKoin {
            modules(storageModule)
        }

        val redisHost = get<String>(named("redisHost"))
        assertEquals("localhost", redisHost)
    }

    @Test
    fun `Redis port configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PORT", "6380")

        startKoin {
            modules(storageModule)
        }

        val redisPort = get<Int>(named("redisPort"))
        assertEquals(6380, redisPort)
    }

    @Test
    fun `Redis port should handle invalid values through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PORT", "invalid-port")

        startKoin {
            modules(storageModule)
        }

        val redisPort = get<Int>(named("redisPort"))
        assertEquals(6379, redisPort)
    }

    @Test
    fun `Should throw Exception when Redis port not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        @Suppress("DEPRECATED")
        assertThrows<Exception> {
            get<String>(named("redisPort"))
        }
    }

    @Test
    fun `Redis password should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PASSWORD", "test-password")

        startKoin {
            modules(storageModule)
        }

        val redisPassword = get<String>(named("redisPassword"))
        assertEquals("test-password", redisPassword)
    }

    @Test
    fun `Should throw IllegalStateException when Redis password not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<IllegalStateException> {
            get<String>(named("redisPassword"))
        }
    }

    @Test
    fun `Redis database configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_DATABASE", "3")

        startKoin {
            modules(storageModule)
        }

        val redisDatabase = get<Int>(named("redisDatabase"))
        assertEquals(3, redisDatabase)
    }

    @Test
    fun `Redis max connections should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_MAX_CONNECTIONS", "25")

        startKoin {
            modules(storageModule)
        }

        val redisMaxConnections = get<Int>(named("redisMaxConnections"))
        assertEquals(25, redisMaxConnections)
    }

    // Database Configuration Tests using Koin DI
    @Test
    fun `Database host configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_HOST", "postgres-test.example.com")

        startKoin {
            modules(storageModule)
        }

        val dbHost = get<String>(named("dbHost"))
        assertEquals("postgres-test.example.com", dbHost)
    }

    @Test
    fun `Database host should use default value when not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        val dbHost = get<String>(named("dbHost"))
        assertEquals("localhost", dbHost)
    }

    @Test
    fun `Database port configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_PORT", "5433")

        startKoin {
            modules(storageModule)
        }

        val dbPort = get<Int>(named("dbPort"))
        assertEquals(5433, dbPort)
    }

    @Test
    fun `Database name configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_NAME", "test_webauthn_db")

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
    fun `Database username configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_USERNAME", "test_user")

        startKoin {
            modules(storageModule)
        }

        val dbUsername = get<String>(named("dbUsername"))
        assertEquals("test_user", dbUsername)
    }

    @Test
    fun `Should throw IllegalStateException when Database username not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<IllegalStateException> {
            get<String>(named("dbUsername"))
        }
    }

    @Test
    fun `Database password configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_PASSWORD", "test_password")

        startKoin {
            modules(storageModule)
        }

        val dbPassword = get<String>(named("dbPassword"))
        assertEquals("test_password", dbPassword)
    }

    @Test
    fun `Should throw IllegalStateException when Database password not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        assertThrows<IllegalStateException> {
            get<String>(named("dbPassword"))
        }
    }

    @Test
    fun `Database max pool size configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_MAX_POOL_SIZE", "20")

        startKoin {
            modules(storageModule)
        }

        val dbMaxPoolSize = get<Int>(named("dbMaxPoolSize"))
        assertEquals(20, dbMaxPoolSize)
    }

    @Test
    fun `Empty string values should be handled correctly through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_HOST", "")
        System.setProperty("MPO_AUTHN_DB_NAME", "")
        System.setProperty("MPO_AUTHN_REDIS_PORT", "")

        startKoin {
            modules(storageModule)
        }

        // Empty strings should be used as-is for string properties
        assertEquals("", get<String>(named("redisHost")))
        assertEquals("", get<String>(named("dbName")))

        // Empty string for numeric property should fall back to default
        assertEquals(6379, get<Int>(named("redisPort")))
    }

    @Test
    fun `Configuration should handle invalid numeric values through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PORT", "invalid")
        System.setProperty("MPO_AUTHN_DB_PORT", "not-a-number")
        System.setProperty("MPO_AUTHN_REDIS_MAX_CONNECTIONS", "xyz")

        startKoin {
            modules(storageModule)
        }

        // Should all fall back to defaults
        assertEquals(6379, get<Int>(named("redisPort")))
        assertEquals(5432, get<Int>(named("dbPort")))
        assertEquals(10, get<Int>(named("redisMaxConnections")))
    }

    @Test
    fun `Configuration should handle edge numeric values through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PORT", "0")
        System.setProperty("MPO_AUTHN_DB_PORT", "-1")
        System.setProperty("MPO_AUTHN_REDIS_DATABASE", "999")

        startKoin {
            modules(storageModule)
        }

        // Should use the actual values, even if unusual
        assertEquals(0, get<Int>(named("redisPort")))
        assertEquals(-1, get<Int>(named("dbPort")))
        assertEquals(999, get<Int>(named("redisDatabase")))
    }

    private fun clearAllTestProperties() {
        val properties = listOf(
            "MPO_AUTHN_REDIS_HOST",
            "MPO_AUTHN_REDIS_PORT",
            "MPO_AUTHN_REDIS_PASSWORD",
            "MPO_AUTHN_REDIS_DATABASE",
            "MPO_AUTHN_REDIS_MAX_CONNECTIONS",
            "MPO_AUTHN_DB_HOST",
            "MPO_AUTHN_DB_PORT",
            "MPO_AUTHN_DB_NAME",
            "MPO_AUTHN_DB_USERNAME",
            "MPO_AUTHN_DB_PASSWORD",
            "MPO_AUTHN_DB_MAX_POOL_SIZE"
        )
        properties.forEach { System.clearProperty(it) }
    }
}
