package com.vmenon.mpo.api.authn.testutils

import com.vmenon.mpo.api.authn.model.JwtKeyAuditLog
import com.vmenon.mpo.api.authn.model.JwtSigningKey
import com.vmenon.mpo.api.authn.model.KeyEvent
import com.vmenon.mpo.api.authn.model.KeyStatus
import com.vmenon.mpo.api.authn.repository.KeyRepository
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

/**
 * In-memory implementation of KeyRepository for unit tests.
 * Thread-safe and provides basic key storage without database persistence.
 */
class InMemoryKeyRepository : KeyRepository {
    private val keys = ConcurrentHashMap<String, JwtSigningKey>()
    private val auditLogs = ConcurrentHashMap<String, MutableList<JwtKeyAuditLog>>()
    private val auditIdCounter = AtomicLong(1)

    override fun saveKey(key: JwtSigningKey) {
        keys[key.keyId] = key
        logAuditEvent(
            JwtKeyAuditLog(
                keyId = key.keyId,
                event = KeyEvent.GENERATED,
                metadata = mapOf("algorithm" to key.algorithm, "key_size" to key.keySize),
            ),
        )
    }

    override fun getKey(keyId: String): JwtSigningKey? = keys[keyId]

    override fun getActiveKey(): JwtSigningKey? =
        keys.values.firstOrNull { it.status == KeyStatus.ACTIVE }

    override fun getKeysByStatus(status: KeyStatus): List<JwtSigningKey> =
        keys.values.filter { it.status == status }.sortedByDescending { it.createdAt }

    override fun getAllActiveAndRetiredKeys(): List<JwtSigningKey> =
        keys.values
            .filter { it.status == KeyStatus.ACTIVE || it.status == KeyStatus.RETIRED }
            .sortedWith(
                compareBy<JwtSigningKey> { if (it.status == KeyStatus.ACTIVE) 0 else 1 }
                    .thenByDescending { it.createdAt },
            )

    override fun updateKeyStatus(
        keyId: String,
        status: KeyStatus,
        timestamp: Instant,
    ) {
        keys[keyId]?.let { key ->
            val updatedKey =
                when (status) {
                    KeyStatus.ACTIVE -> key.copy(status = status, activatedAt = timestamp)
                    KeyStatus.RETIRED -> key.copy(status = status, retiredAt = timestamp)
                    else -> key.copy(status = status)
                }
            keys[keyId] = updatedKey

            // Log appropriate audit event based on new status
            val event =
                when (status) {
                    KeyStatus.ACTIVE -> KeyEvent.ACTIVATED
                    KeyStatus.RETIRED -> KeyEvent.RETIRED
                    KeyStatus.DELETED -> KeyEvent.DELETED
                    KeyStatus.PENDING -> KeyEvent.GENERATED
                }

            logAuditEvent(JwtKeyAuditLog(keyId = keyId, event = event))
        }
    }

    override fun updateKeyExpiration(
        keyId: String,
        expiresAt: Instant,
    ) {
        keys[keyId]?.let { key ->
            keys[keyId] = key.copy(expiresAt = expiresAt)
        }
    }

    override fun deleteKey(keyId: String) {
        keys.remove(keyId)
        logAuditEvent(JwtKeyAuditLog(keyId = keyId, event = KeyEvent.DELETED))
    }

    override fun logAuditEvent(event: JwtKeyAuditLog) {
        val enrichedEvent =
            if (event.id == null) {
                event.copy(
                    id = auditIdCounter.getAndIncrement(),
                    timestamp = event.timestamp ?: Instant.now(),
                )
            } else {
                event
            }

        auditLogs.getOrPut(event.keyId) { mutableListOf() }.add(enrichedEvent)
    }

    override fun getAuditLogs(keyId: String): List<JwtKeyAuditLog> =
        auditLogs[keyId]?.sortedByDescending { it.timestamp } ?: emptyList()

    /**
     * Clear all keys and audit logs. Useful for test cleanup.
     */
    fun clear() {
        keys.clear()
        auditLogs.clear()
    }
}
