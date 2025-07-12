package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.AssertionRequest
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

/**
 * In-memory implementation of RequestStorage for development/testing
 * NOTE: This should NOT be used in production multi-instance deployments
 */
class InMemoryRequestStorage : RequestStorage {

    private data class StoredItem<T>(
        val value: T,
        val expirationTime: Long
    )

    private val registrationStorage = ConcurrentHashMap<String, StoredItem<PublicKeyCredentialCreationOptions>>()
    private val assertionStorage = ConcurrentHashMap<String, StoredItem<AssertionRequest>>()
    private val cleanupExecutor: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()

    init {
        // Clean up expired entries every minute
        cleanupExecutor.scheduleAtFixedRate({
            cleanupExpiredEntries()
        }, 1, 1, TimeUnit.MINUTES)
    }

    override fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long
    ) {
        val expirationTime = System.currentTimeMillis() + (ttlSeconds * 1000)
        registrationStorage[requestId] = StoredItem(options, expirationTime)
    }

    override fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions? {
        val stored = registrationStorage.remove(requestId)
        return if (stored != null && stored.expirationTime > System.currentTimeMillis()) {
            stored.value
        } else {
            null
        }
    }

    override fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long
    ) {
        val expirationTime = System.currentTimeMillis() + (ttlSeconds * 1000)
        assertionStorage[requestId] = StoredItem(request, expirationTime)
    }

    override fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        val stored = assertionStorage.remove(requestId)
        return if (stored != null && stored.expirationTime > System.currentTimeMillis()) {
            stored.value
        } else {
            null
        }
    }

    private fun cleanupExpiredEntries() {
        val currentTime = System.currentTimeMillis()

        registrationStorage.entries.removeIf { (_, stored) ->
            stored.expirationTime <= currentTime
        }

        assertionStorage.entries.removeIf { (_, stored) ->
            stored.expirationTime <= currentTime
        }
    }

    override fun close() {
        cleanupExecutor.shutdown()
        registrationStorage.clear()
        assertionStorage.clear()
    }
}
