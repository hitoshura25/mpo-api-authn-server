package com.vmenon.mpo.api.authn.repository

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.vmenon.mpo.api.authn.model.JwtKeyAuditLog
import com.vmenon.mpo.api.authn.model.JwtSigningKey
import com.vmenon.mpo.api.authn.model.KeyEvent
import com.vmenon.mpo.api.authn.model.KeyStatus
import org.postgresql.util.PGobject
import java.sql.ResultSet
import java.sql.Timestamp
import java.time.Instant
import javax.sql.DataSource

/**
 * Repository interface for managing JWT signing keys in the database.
 *
 * Provides CRUD operations for keys and audit logging functionality.
 */
interface KeyRepository {
    /**
     * Save a new key to the database.
     * Automatically logs a GENERATED audit event.
     *
     * @param key The key to save
     * @throws Exception if key_id already exists or constraints are violated
     */
    fun saveKey(key: JwtSigningKey)

    /**
     * Retrieve a key by its ID.
     *
     * @param keyId The unique key identifier
     * @return The key if found, null otherwise
     */
    fun getKey(keyId: String): JwtSigningKey?

    /**
     * Get the current ACTIVE key.
     * Due to the single_active_key constraint, there can only be one.
     *
     * @return The active key if it exists, null otherwise
     */
    fun getActiveKey(): JwtSigningKey?

    /**
     * Get all keys with a specific status.
     *
     * @param status The status to filter by
     * @return List of keys ordered by created_at DESC
     */
    fun getKeysByStatus(status: KeyStatus): List<JwtSigningKey>

    /**
     * Get all publishable keys (ACTIVE + RETIRED) for the JWKS endpoint.
     * Ordered by status (ACTIVE first) then by created_at DESC.
     *
     * @return List of keys to include in JWKS response
     */
    fun getAllActiveAndRetiredKeys(): List<JwtSigningKey>

    /**
     * Update a key's status and set the appropriate timestamp.
     * Automatically logs an audit event (ACTIVATED, RETIRED, or DELETED).
     *
     * @param keyId The key to update
     * @param newStatus The new status
     * @param statusTimestamp When the status change occurred
     */
    fun updateKeyStatus(
        keyId: String,
        newStatus: KeyStatus,
        statusTimestamp: Instant,
    )

    /**
     * Update the expires_at timestamp for a key.
     * Used when retiring a key to set when it should be deleted.
     *
     * @param keyId The key to update
     * @param expiresAt When the key should expire
     */
    fun updateKeyExpiration(
        keyId: String,
        expiresAt: Instant,
    )

    /**
     * Permanently delete a key from the database.
     * This is the final phase of the lifecycle (after RETIRED).
     *
     * @param keyId The key to delete
     */
    fun deleteKey(keyId: String)

    /**
     * Log an audit event for key lifecycle tracking.
     *
     * @param event The audit event to log
     */
    fun logAuditEvent(event: JwtKeyAuditLog)

    /**
     * Retrieve audit logs for a specific key.
     *
     * @param keyId The key to get logs for
     * @return List of audit events ordered by timestamp DESC
     */
    fun getAuditLogs(keyId: String): List<JwtKeyAuditLog>
}

/**
 * PostgreSQL implementation of KeyRepository.
 *
 * Uses raw JDBC for database operations with proper transaction handling.
 */
class PostgresKeyRepository(private val dataSource: DataSource) : KeyRepository {
    private val objectMapper = jacksonObjectMapper()

    override fun saveKey(key: JwtSigningKey) {
        dataSource.connection.use { conn ->
            val sql =
                """
                INSERT INTO jwt_signing_keys
                (key_id, private_key_pem, public_key_pem, algorithm, key_size, status,
                 created_at, activated_at, retired_at, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
                """.trimIndent()

            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, key.keyId)
                stmt.setString(2, key.privateKeyPem)
                stmt.setString(3, key.publicKeyPem)
                stmt.setString(4, key.algorithm)
                stmt.setInt(5, key.keySize)
                stmt.setString(6, key.status.name)
                stmt.setTimestamp(7, Timestamp.from(key.createdAt))
                stmt.setTimestamp(8, key.activatedAt?.let { Timestamp.from(it) })
                stmt.setTimestamp(9, key.retiredAt?.let { Timestamp.from(it) })
                stmt.setTimestamp(10, key.expiresAt?.let { Timestamp.from(it) })
                stmt.setObject(11, key.metadata?.let { toPGobject(it) })
                stmt.executeUpdate()
            }

            // Log audit event
            logAuditEvent(
                JwtKeyAuditLog(
                    keyId = key.keyId,
                    event = KeyEvent.GENERATED,
                    metadata =
                        mapOf(
                            "algorithm" to key.algorithm,
                            "key_size" to key.keySize,
                        ),
                ),
            )
        }
    }

    override fun getKey(keyId: String): JwtSigningKey? {
        dataSource.connection.use { conn ->
            val sql = "SELECT * FROM jwt_signing_keys WHERE key_id = ?"
            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, keyId)
                val rs = stmt.executeQuery()
                return if (rs.next()) mapResultSetToKey(rs) else null
            }
        }
    }

    override fun getActiveKey(): JwtSigningKey? {
        dataSource.connection.use { conn ->
            val sql = "SELECT * FROM jwt_signing_keys WHERE status = 'ACTIVE'"
            conn.prepareStatement(sql).use { stmt ->
                val rs = stmt.executeQuery()
                return if (rs.next()) mapResultSetToKey(rs) else null
            }
        }
    }

    override fun getKeysByStatus(status: KeyStatus): List<JwtSigningKey> {
        dataSource.connection.use { conn ->
            val sql = "SELECT * FROM jwt_signing_keys WHERE status = ? ORDER BY created_at DESC"
            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, status.name)
                val rs = stmt.executeQuery()
                return buildList {
                    while (rs.next()) {
                        add(mapResultSetToKey(rs))
                    }
                }
            }
        }
    }

    override fun getAllActiveAndRetiredKeys(): List<JwtSigningKey> {
        dataSource.connection.use { conn ->
            val sql =
                """
                SELECT * FROM jwt_signing_keys
                WHERE status IN ('ACTIVE', 'RETIRED')
                ORDER BY
                    CASE status
                        WHEN 'ACTIVE' THEN 1
                        WHEN 'RETIRED' THEN 2
                    END,
                    created_at DESC
                """.trimIndent()
            conn.prepareStatement(sql).use { stmt ->
                val rs = stmt.executeQuery()
                return buildList {
                    while (rs.next()) {
                        add(mapResultSetToKey(rs))
                    }
                }
            }
        }
    }

    override fun updateKeyStatus(
        keyId: String,
        newStatus: KeyStatus,
        statusTimestamp: Instant,
    ) {
        dataSource.connection.use { conn ->
            val columnName =
                when (newStatus) {
                    KeyStatus.ACTIVE -> "activated_at"
                    KeyStatus.RETIRED -> "retired_at"
                    KeyStatus.DELETED -> null // Don't update timestamp for DELETED
                    KeyStatus.PENDING -> null
                }

            val sql =
                if (columnName != null) {
                    "UPDATE jwt_signing_keys SET status = ?, $columnName = ? WHERE key_id = ?"
                } else {
                    "UPDATE jwt_signing_keys SET status = ? WHERE key_id = ?"
                }

            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, newStatus.name)
                if (columnName != null) {
                    stmt.setTimestamp(2, Timestamp.from(statusTimestamp))
                    stmt.setString(3, keyId)
                } else {
                    stmt.setString(2, keyId)
                }
                stmt.executeUpdate()
            }

            // Log audit event
            val event =
                when (newStatus) {
                    KeyStatus.ACTIVE -> KeyEvent.ACTIVATED
                    KeyStatus.RETIRED -> KeyEvent.RETIRED
                    KeyStatus.DELETED -> KeyEvent.DELETED
                    KeyStatus.PENDING -> KeyEvent.GENERATED
                }

            logAuditEvent(
                JwtKeyAuditLog(
                    keyId = keyId,
                    event = event,
                ),
            )
        }
    }

    override fun updateKeyExpiration(
        keyId: String,
        expiresAt: Instant,
    ) {
        dataSource.connection.use { conn ->
            val sql = "UPDATE jwt_signing_keys SET expires_at = ? WHERE key_id = ?"
            conn.prepareStatement(sql).use { stmt ->
                stmt.setTimestamp(1, Timestamp.from(expiresAt))
                stmt.setString(2, keyId)
                stmt.executeUpdate()
            }
        }
    }

    override fun deleteKey(keyId: String) {
        dataSource.connection.use { conn ->
            conn.prepareStatement("DELETE FROM jwt_signing_keys WHERE key_id = ?").use { stmt ->
                stmt.setString(1, keyId)
                stmt.executeUpdate()
            }
        }
    }

    override fun logAuditEvent(event: JwtKeyAuditLog) {
        dataSource.connection.use { conn ->
            val sql =
                """
                INSERT INTO jwt_key_audit_log (key_id, event, timestamp, metadata)
                VALUES (?, ?, ?, ?::jsonb)
                """.trimIndent()

            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, event.keyId)
                stmt.setString(2, event.event.name)
                stmt.setTimestamp(3, Timestamp.from(event.timestamp))
                stmt.setObject(4, event.metadata?.let { toPGobject(it) })
                stmt.executeUpdate()
            }
        }
    }

    override fun getAuditLogs(keyId: String): List<JwtKeyAuditLog> {
        dataSource.connection.use { conn ->
            val sql = "SELECT * FROM jwt_key_audit_log WHERE key_id = ? ORDER BY timestamp DESC"
            conn.prepareStatement(sql).use { stmt ->
                stmt.setString(1, keyId)
                val rs = stmt.executeQuery()
                return buildList {
                    while (rs.next()) {
                        add(
                            JwtKeyAuditLog(
                                id = rs.getLong("id"),
                                keyId = rs.getString("key_id"),
                                event = KeyEvent.valueOf(rs.getString("event")),
                                timestamp = rs.getTimestamp("timestamp").toInstant(),
                                metadata = rs.getString("metadata")?.let {
                                    @Suppress("UNCHECKED_CAST")
                                    objectMapper.readValue(it, Map::class.java) as Map<String, Any>
                                },
                            ),
                        )
                    }
                }
            }
        }
    }

    /**
     * Map a ResultSet row to a JwtSigningKey object.
     */
    private fun mapResultSetToKey(rs: ResultSet): JwtSigningKey {
        return JwtSigningKey(
            keyId = rs.getString("key_id"),
            privateKeyPem = rs.getString("private_key_pem"),
            publicKeyPem = rs.getString("public_key_pem"),
            algorithm = rs.getString("algorithm"),
            keySize = rs.getInt("key_size"),
            status = KeyStatus.valueOf(rs.getString("status")),
            createdAt = rs.getTimestamp("created_at").toInstant(),
            activatedAt = rs.getTimestamp("activated_at")?.toInstant(),
            retiredAt = rs.getTimestamp("retired_at")?.toInstant(),
            expiresAt = rs.getTimestamp("expires_at")?.toInstant(),
            metadata = rs.getString("metadata")?.let {
                @Suppress("UNCHECKED_CAST")
                objectMapper.readValue(it, Map::class.java) as Map<String, Any>
            },
        )
    }

    /**
     * Convert a Map to a PostgreSQL JSONB object.
     */
    private fun toPGobject(map: Map<String, Any>): PGobject {
        return PGobject().apply {
            type = "jsonb"
            value = objectMapper.writeValueAsString(map)
        }
    }
}
