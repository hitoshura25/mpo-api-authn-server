package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.storage.InMemoryRequestStorage
import com.vmenon.mpo.api.authn.storage.RequestStorage
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.qualifier.named
import org.koin.test.KoinTest
import org.koin.test.inject

class DependencyInjectionTest : KoinTest {

    @BeforeEach
    fun setup() {
        stopKoin() // Ensure clean state
    }

    @AfterEach
    fun teardown() {
        stopKoin() // Clean up after each test
    }

    @Test
    fun `should inject memory storage when STORAGE_TYPE is memory`() {
        // Set environment for memory storage
        System.setProperty("STORAGE_TYPE", "memory")

        startKoin {
            modules(appModule)
        }

        val storage: RequestStorage by inject()

        assertTrue(storage is InMemoryRequestStorage)

        System.clearProperty("STORAGE_TYPE")
    }

    @Test
    fun `should configure redis storage type when STORAGE_TYPE is redis`() {
        // Set environment for redis storage
        System.setProperty("STORAGE_TYPE", "redis")
        System.setProperty("REDIS_HOST", "localhost")
        System.setProperty("REDIS_PORT", "6379")

        try {
            startKoin {
                modules(appModule)
            }

            val koin = getKoin()

            // Only verify the configuration values, not the actual storage instantiation
            val storageType = koin.get<String>(named("storageType"))
            val redisHost = koin.get<String>(named("redisHost"))
            val redisPort = koin.get<Int>(named("redisPort"))

            assertEquals("redis", storageType)
            assertEquals("localhost", redisHost)
            assertEquals(6379, redisPort)
        } finally {
            System.clearProperty("STORAGE_TYPE")
            System.clearProperty("REDIS_HOST")
            System.clearProperty("REDIS_PORT")
        }
    }

    @Test
    fun `should throw exception for unsupported storage type`() {
        System.setProperty("STORAGE_TYPE", "unsupported")

        try {
            startKoin {
                modules(appModule)
            }

            // Get the Koin instance and try to get the RequestStorage directly
            val koin = getKoin()
            val exception = assertThrows<Exception> {
                koin.get<RequestStorage>()
            }

            // Check that the root cause is our IllegalArgumentException with the expected message
            val rootCause = generateSequence(exception as Throwable) { it.cause }.last()
            assertTrue(rootCause is IllegalArgumentException)
            assertTrue(rootCause.message?.contains("Unsupported storage type: unsupported") == true)
        } finally {
            System.clearProperty("STORAGE_TYPE")
        }
    }
}
