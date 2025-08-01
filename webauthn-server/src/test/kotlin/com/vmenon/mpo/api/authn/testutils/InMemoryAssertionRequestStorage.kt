package com.vmenon.mpo.api.authn.testutils

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.yubico.webauthn.AssertionRequest
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

/**
 * In-memory implementation of AssertionRequestStorage for development/testing
 * NOTE: This should NOT be used in production multi-instance deployments
 */
class InMemoryAssertionRequestStorage : AssertionRequestStorage {
    private data class StoredItem<T>(
        val value: T,
        val expirationTime: Long,
    )

    private val storage = ConcurrentHashMap<String, StoredItem<AssertionRequest>>()
    private val cleanupExecutor: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()

    init {
        // Clean up expired entries every minute
        cleanupExecutor.scheduleAtFixedRate({
            cleanupExpiredEntries()
        }, 1, 1, TimeUnit.MINUTES)
    }

    override suspend fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long,
    ) {
        val expirationTime = System.currentTimeMillis() + (ttlSeconds * 1000)
        storage[requestId] = StoredItem(request, expirationTime)
    }

    override suspend fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        val stored = storage.remove(requestId)
        return if (stored != null && stored.expirationTime > System.currentTimeMillis()) {
            stored.value
        } else {
            null
        }
    }

    private fun cleanupExpiredEntries() {
        val currentTime = System.currentTimeMillis()
        storage.entries.removeIf { (_, stored) ->
            stored.expirationTime <= currentTime
        }
    }

    override fun close() {
        cleanupExecutor.shutdown()
        storage.clear()
    }
}
