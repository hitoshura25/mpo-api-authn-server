package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.testStorageModule
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.qualifier.named
import org.koin.test.KoinTest
import org.koin.test.get
import kotlin.test.assertEquals

@TestInstance(TestInstance.Lifecycle.PER_METHOD)
class AppModuleTest : KoinTest {

    @AfterEach
    fun cleanup() {
        clearAllTestProperties()
        stopKoin()
    }

    @Test
    fun `Relying Party ID should work through system property`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_ID, "test.example.com")

        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyId = get<String>(named("relyingPartyId"))
        assertEquals("test.example.com", relyingPartyId)
    }

    @Test
    fun `Relying Party ID should use default value when not configured`() {
        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyId = get<String>(named("relyingPartyId"))
        assertEquals("localhost", relyingPartyId)
    }

    @Test
    fun `Should throw InstanceCreationException when Relying Party Id is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_ID, "")

        startKoin {
            modules(testStorageModule, appModule)
        }
        assertThrows<Exception> {
            get<String>(named("relyingPartyId"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when Relying Party Id is white-space only`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_ID, "   ")

        startKoin {
            modules(testStorageModule, appModule)
        }
        assertThrows<Exception> {
            get<String>(named("relyingPartyId"))
        }
    }

    @Test
    fun `Relying Party Name should work through system property`() {
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_NAME,
            "Test WebAuthn Service",
        )

        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyName = get<String>(named("relyingPartyName"))
        assertEquals("Test WebAuthn Service", relyingPartyName)
    }

    @Test
    fun `Relying Party Name should fallback to env var when sysprop not set`() {
        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyName = get<String>(named("relyingPartyName"))
        assertEquals(
            "MPO Api Authn",
            relyingPartyName,
        ) // Default value when neither system property nor env var is set
    }

    @Test
    fun `Relying Party Name should use default value when not configured`() {
        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyName = get<String>(named("relyingPartyName"))
        assertEquals("MPO Api Authn", relyingPartyName)
    }

    @Test
    fun `Should throw InstanceCreationException when Relying Party Name is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_NAME, "")

        startKoin {
            modules(testStorageModule, appModule)
        }
        assertThrows<Exception> {
            get<String>(named("relyingPartyName"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when RP Name is whitespace only`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_NAME, "   ")

        startKoin {
            modules(testStorageModule, appModule)
        }
        assertThrows<Exception> {
            get<String>(named("relyingPartyName"))
        }
    }

    @Test
    fun `Relying Party Name should support special characters and spaces`() {
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_NAME,
            "My WebAuthn Service™ - Test Environment",
        )

        startKoin {
            modules(testStorageModule, appModule)
        }

        val relyingPartyName = get<String>(named("relyingPartyName"))
        assertEquals("My WebAuthn Service™ - Test Environment", relyingPartyName)
    }

    private fun clearAllTestProperties() {
        val properties =
            listOf(
                EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_ID,
                EnvironmentVariables.MPO_AUTHN_APP_RELYING_PARTY_NAME,
            )
        properties.forEach { System.clearProperty(it) }
    }
}
