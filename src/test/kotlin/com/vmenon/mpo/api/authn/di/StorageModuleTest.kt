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
        assertEquals(6379, redisPort) // Should fall back to default
    }

    @Test
    fun `Redis password should work as nullable through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_PASSWORD", "test-password")

        startKoin {
            modules(storageModule)
        }

        val redisPassword = get<String>(named("redisPassword"))
        assertEquals("test-password", redisPassword)
    }

    @Test
    fun `Redis password should be null when not configured through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        // When redisPassword is null (not configured), trying to access it should throw IllegalStateException
        // because Koin's single instance factory can't return a null value for a nullable dependency
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
    fun `Database username configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_USERNAME", "test_user")

        startKoin {
            modules(storageModule)
        }

        val dbUsername = get<String>(named("dbUsername"))
        assertEquals("test_user", dbUsername)
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
    fun `Database max pool size configuration should work through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_MAX_POOL_SIZE", "20")

        startKoin {
            modules(storageModule)
        }

        val dbMaxPoolSize = get<Int>(named("dbMaxPoolSize"))
        assertEquals(20, dbMaxPoolSize)
    }

    // Integration Tests - Multiple configurations working together
    @Test
    fun `All Redis configuration should work together through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_HOST", "redis-cluster.example.com")
        System.setProperty("MPO_AUTHN_REDIS_PORT", "6380")
        System.setProperty("MPO_AUTHN_REDIS_PASSWORD", "cluster-password")
        System.setProperty("MPO_AUTHN_REDIS_DATABASE", "2")
        System.setProperty("MPO_AUTHN_REDIS_MAX_CONNECTIONS", "50")

        startKoin {
            modules(storageModule)
        }

        assertEquals("redis-cluster.example.com", get<String>(named("redisHost")))
        assertEquals(6380, get<Int>(named("redisPort")))
        assertEquals("cluster-password", get<String>(named("redisPassword")))
        assertEquals(2, get<Int>(named("redisDatabase")))
        assertEquals(50, get<Int>(named("redisMaxConnections")))
    }

    @Test
    fun `All Database configuration should work together through Koin DI`() {
        System.setProperty("MPO_AUTHN_DB_HOST", "postgres-cluster.example.com")
        System.setProperty("MPO_AUTHN_DB_PORT", "5433")
        System.setProperty("MPO_AUTHN_DB_NAME", "production_webauthn")
        System.setProperty("MPO_AUTHN_DB_USERNAME", "prod_user")
        System.setProperty("MPO_AUTHN_DB_PASSWORD", "prod_password")
        System.setProperty("MPO_AUTHN_DB_MAX_POOL_SIZE", "30")

        startKoin {
            modules(storageModule)
        }

        assertEquals("postgres-cluster.example.com", get<String>(named("dbHost")))
        assertEquals(5433, get<Int>(named("dbPort")))
        assertEquals("production_webauthn", get<String>(named("dbName")))
        assertEquals("prod_user", get<String>(named("dbUsername")))
        assertEquals("prod_password", get<String>(named("dbPassword")))
        assertEquals(30, get<Int>(named("dbMaxPoolSize")))
    }

    // Test Koin-specific behavior
    @Test
    fun `Configuration should be singleton through Koin DI`() {
        System.setProperty("MPO_AUTHN_REDIS_HOST", "singleton-test-host")

        startKoin {
            modules(storageModule)
        }

        val redisHost1 = get<String>(named("redisHost"))
        val redisHost2 = get<String>(named("redisHost"))

        // Should be the same instance due to single() behavior
        assertEquals(redisHost1, redisHost2)
        assertEquals("singleton-test-host", redisHost1)
    }

    @Test
    fun `Configuration should be evaluated lazily through Koin DI`() {
        startKoin {
            modules(storageModule)
        }

        // Set property after Koin started but before first access
        System.setProperty("MPO_AUTHN_REDIS_HOST", "lazy-evaluated-host")

        val redisHost = get<String>(named("redisHost"))
        assertEquals("lazy-evaluated-host", redisHost)
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

    @Test
    fun `Multiple Koin contexts should work independently`() {
        // First context
        System.setProperty("MPO_AUTHN_REDIS_HOST", "first-host")
        startKoin {
            modules(storageModule)
        }
        assertEquals("first-host", get<String>(named("redisHost")))
        stopKoin()

        // Second context with different property
        System.setProperty("MPO_AUTHN_REDIS_HOST", "second-host")
        startKoin {
            modules(storageModule)
        }
        assertEquals("second-host", get<String>(named("redisHost")))
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
