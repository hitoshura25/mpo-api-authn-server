package com.vmenon.mpo.api.authn.storage.postgresql

import com.vmenon.mpo.api.authn.security.PostQuantumCryptographyService
import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import com.yubico.webauthn.RegisteredCredential
import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import java.io.Closeable
import java.security.MessageDigest
import java.sql.SQLException
import java.util.Optional
import javax.sql.DataSource
import com.yubico.webauthn.data.ByteArray
import com.vmenon.mpo.api.authn.security.EncryptedData
import java.security.GeneralSecurityException
import com.fasterxml.jackson.core.JsonProcessingException
import java.sql.Connection
import java.sql.ResultSet
import com.vmenon.mpo.api.authn.utils.JacksonUtils

/**
 * Configuration for database connection
 */
data class DatabaseConfig(
    val host: String,
    val port: Int,
    val database: String,
    val username: String,
    val password: String,
    val maxPoolSize: Int,
)

/**
 * Helper for user-related database operations
 */
internal class UserDataManager(
    private val dataSource: DataSource,
    private val cryptoHelper: QuantumCryptoHelper,
) {
    fun getUserByHandle(userHandle: ByteArray): UserAccount? {
        val userHandleHash = cryptoHelper.hash(userHandle.base64Url)
        val sql = "SELECT encrypted_user_data FROM webauthn_users_secure WHERE user_handle_hash = ?"
        return executeQueryForUser(sql, userHandleHash)
    }

    fun getUserByUsername(username: String): UserAccount? {
        val usernameHash = cryptoHelper.hash(username)
        val sql = "SELECT encrypted_user_data FROM webauthn_users_secure WHERE username_hash = ?"
        return executeQueryForUser(sql, usernameHash)
    }

    fun userExists(username: String): Boolean {
        val usernameHash = cryptoHelper.hash(username)
        val sql = "SELECT 1 FROM webauthn_users_secure WHERE username_hash = ? LIMIT 1"

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, usernameHash)
                statement.executeQuery().use { resultSet ->
                    resultSet.next()
                }
            }
        }
    }

    private fun executeQueryForUser(sql: String, parameter: String): UserAccount? {
        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, parameter)
                statement.executeQuery().use { resultSet ->
                    extractUserFromResultSet(resultSet, cryptoHelper)
                }
            }
        }
    }

}

/**
 * Helper for encryption/decryption operations
 */
internal class QuantumCryptoHelper(private val cryptoService: PostQuantumCryptographyService) {
    fun encrypt(data: String) = cryptoService.encrypt(data)

    fun decrypt(encryptedDataString: String): String {
        val parts = encryptedDataString.split("|")
        require(parts.size >= MINIMUM_ENCRYPTED_PARTS) { "Invalid encrypted data format" }

        val method = parts[0]
        val data = parts[1]
        val keyMaterial = parts[2]
        val metadata =
            if (parts.size > METADATA_PART_THRESHOLD) {
                parts[METADATA_PART_INDEX].split(",").associate {
                    val kv = it.split("=", limit = KEY_VALUE_SPLIT_LIMIT)
                    if (kv.size == EXPECTED_KV_PARTS) kv[0] to kv[1] else kv[0] to ""
                }
            } else {
                emptyMap()
            }

        return cryptoService.decrypt(
            EncryptedData(
                method,
                data,
                keyMaterial,
                metadata,
            ),
        )
    }

    fun encryptedDataToString(encrypted: EncryptedData): String {
        val metadataStr = encrypted.metadata.entries.joinToString(",") { "${it.key}=${it.value}" }
        return "${encrypted.method}|${encrypted.data}|${encrypted.keyMaterial}|$metadataStr"
    }

    fun hash(data: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hashBytes = digest.digest(data.toByteArray())
        return hashBytes.joinToString("") { "%02x".format(it) }
    }

    companion object {
        // Data parsing constants
        const val MINIMUM_ENCRYPTED_PARTS = 4
        const val METADATA_PART_THRESHOLD = 3
        const val METADATA_PART_INDEX = 3
        const val KEY_VALUE_SPLIT_LIMIT = 2
        const val EXPECTED_KV_PARTS = 2
    }
}

/**
 * Quantum-safe PostgreSQL credential storage - secure by default for new projects
 * Uses Kyber768 + AES-256-GCM hybrid encryption for all data
 */
class QuantumSafeCredentialStorage(
    private val dataSource: DataSource,
) : CredentialStorage {
    private val cryptoHelper = QuantumCryptoHelper(PostQuantumCryptographyService())
    private val userDataManager = UserDataManager(dataSource, cryptoHelper)

    companion object {
        // SQL parameter indices
        private const val PARAM_1 = 1
        private const val PARAM_2 = 2
        private const val PARAM_3 = 3
    }


    override fun addRegistration(registration: CredentialRegistration) {
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                val userHandleHash = cryptoHelper.hash(registration.userAccount.userHandle.base64Url)
                val usernameHash = cryptoHelper.hash(registration.userAccount.username)
                val credentialIdHash = cryptoHelper.hash(registration.credential.credentialId.base64Url)

                // Encrypt user data with quantum-safe encryption
                val encryptedUserData =
                    cryptoHelper.encryptedDataToString(
                        cryptoHelper.encrypt(objectMapper.writeValueAsString(registration.userAccount)),
                    )

                // Insert or update user
                val insertUserSQL =
                    """
                    INSERT INTO webauthn_users_secure (user_handle_hash, username_hash, encrypted_user_data) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT (username_hash) DO UPDATE SET 
                        encrypted_user_data = EXCLUDED.encrypted_user_data
                    """.trimIndent()

                connection.prepareStatement(insertUserSQL).use { statement ->
                    statement.setString(PARAM_1, userHandleHash)
                    statement.setString(PARAM_2, usernameHash)
                    statement.setString(PARAM_3, encryptedUserData)
                    statement.executeUpdate()
                }

                // Encrypt credential data with quantum-safe encryption
                val encryptedCredentialData =
                    cryptoHelper.encryptedDataToString(
                        cryptoHelper.encrypt(objectMapper.writeValueAsString(registration)),
                    )

                // Insert credential
                val insertCredentialSQL =
                    """
                    INSERT INTO webauthn_credentials_secure 
                    (credential_id_hash, user_handle_hash, encrypted_credential_data) 
                    VALUES (?, ?, ?)
                    ON CONFLICT (credential_id_hash) DO UPDATE SET
                        encrypted_credential_data = EXCLUDED.encrypted_credential_data
                    """.trimIndent()

                connection.prepareStatement(insertCredentialSQL).use { statement ->
                    statement.setString(PARAM_1, credentialIdHash)
                    statement.setString(PARAM_2, userHandleHash)
                    statement.setString(PARAM_3, encryptedCredentialData)
                    statement.executeUpdate()
                }

                connection.commit()
            } catch (e: SQLException) {
                handleTransactionException(connection, e)
            } catch (e: GeneralSecurityException) {
                handleTransactionException(connection, e)
            } catch (e: JsonProcessingException) {
                handleTransactionException(connection, e)
            }
        }
    }

    override fun getRegistrationsByUsername(username: String): Set<CredentialRegistration> {
        val usernameHash = cryptoHelper.hash(username)
        val sql =
            """
            SELECT c.encrypted_credential_data 
            FROM webauthn_credentials_secure c
            JOIN webauthn_users_secure u ON c.user_handle_hash = u.user_handle_hash
            WHERE u.username_hash = ?
            """.trimIndent()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(PARAM_1, usernameHash)
                statement.executeQuery().use { resultSet ->
                    buildSet {
                        while (resultSet.next()) {
                            val encryptedData = resultSet.getString("encrypted_credential_data")
                            val credentialJson = cryptoHelper.decrypt(encryptedData)
                            add(objectMapper.readValue(credentialJson, CredentialRegistration::class.java))
                        }
                    }
                }
            }
        }
    }

    override fun getUserByHandle(userHandle: ByteArray): UserAccount? =
        userDataManager.getUserByHandle(userHandle)

    override fun getUserByUsername(username: String): UserAccount? = 
        userDataManager.getUserByUsername(username)

    override fun userExists(username: String): Boolean = 
        userDataManager.userExists(username)

    override fun close() {
        (dataSource as Closeable).close()
    }

    override fun lookup(
        credentialId: ByteArray,
        userHandle: ByteArray,
    ): Optional<RegisteredCredential> {
        val credentialIdHash = cryptoHelper.hash(credentialId.base64Url)
        val userHandleHash = cryptoHelper.hash(userHandle.base64Url)

        val sql =
            """
            SELECT encrypted_credential_data 
            FROM webauthn_credentials_secure 
            WHERE credential_id_hash = ? AND user_handle_hash = ?
            """.trimIndent()

        return executeQueryForCredential(sql, credentialIdHash, userHandleHash)
    }

    private fun executeQueryForCredential(sql: String, param1: String, param2: String): Optional<RegisteredCredential> {
        return executeCredentialQuery(dataSource, sql, param1, param2) { resultSet ->
            extractCredentialFromResultSet(resultSet, cryptoHelper)
        }
    }


    override fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential> {
        val credentialIdHash = cryptoHelper.hash(credentialId.base64Url)
        val sql = "SELECT encrypted_credential_data FROM webauthn_credentials_secure WHERE credential_id_hash = ?"

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(PARAM_1, credentialIdHash)
                statement.executeQuery().use { resultSet ->
                    buildSet {
                        while (resultSet.next()) {
                            val encryptedData = resultSet.getString("encrypted_credential_data")
                            val credentialJson = cryptoHelper.decrypt(encryptedData)
                            val registration =
                                objectMapper.readValue(credentialJson, CredentialRegistration::class.java)
                            add(registration.credential)
                        }
                    }
                }
            }
        }
    }

    private fun handleTransactionException(connection: Connection, exception: Throwable): Nothing {
        connection.rollback()
        throw exception
    }
}

// Connection pool constants for factory function
private const val MINIMUM_IDLE_CONNECTIONS = 2
private const val CONNECTION_TIMEOUT_MS = 30000L // 30 seconds
private const val IDLE_TIMEOUT_MS = 600000L // 10 minutes  
private const val MAX_LIFETIME_MS = 1800000L // 30 minutes
private const val LEAK_DETECTION_THRESHOLD_MS = 60000L // 1 minute

/**
 * Factory function to create QuantumSafeCredentialStorage with proper connection pooling
 */
fun createQuantumSafeCredentialStorage(config: DatabaseConfig): QuantumSafeCredentialStorage {
    val hikariConfig = HikariConfig().apply {
        jdbcUrl = "jdbc:postgresql://${config.host}:${config.port}/${config.database}?sslmode=disable"
        this.username = config.username
        this.password = config.password
        maximumPoolSize = config.maxPoolSize
        minimumIdle = MINIMUM_IDLE_CONNECTIONS
        connectionTimeout = CONNECTION_TIMEOUT_MS
        idleTimeout = IDLE_TIMEOUT_MS
        maxLifetime = MAX_LIFETIME_MS
        leakDetectionThreshold = LEAK_DETECTION_THRESHOLD_MS
    }

    val dataSource = HikariDataSource(hikariConfig)
    return QuantumSafeCredentialStorage(dataSource)
}

/**
 * Helper functions for JSON processing - moved outside class to reduce function count
 */
private fun extractUserFromJson(userJson: String): UserAccount {
    return JacksonUtils.objectMapper.readValue(
        userJson, UserAccount::class.java
    )
}

private fun extractCredentialFromJson(
    credentialJson: String
): Optional<RegisteredCredential> {
    val registration = JacksonUtils.objectMapper.readValue(
        credentialJson, CredentialRegistration::class.java
    )
    return Optional.of(registration.credential)
}

private fun <T> executeCredentialQuery(
    dataSource: DataSource,
    sql: String,
    param1: String,
    param2: String,
    resultExtractor: (ResultSet) -> T
): T {
    return dataSource.connection.use { connection ->
        connection.prepareStatement(sql).use { statement ->
            statement.setString(1, param1)
            statement.setString(2, param2)
            statement.executeQuery().use { resultSet ->
                resultExtractor(resultSet)
            }
        }
    }
}

private fun extractUserFromResultSet(resultSet: ResultSet, cryptoHelper: QuantumCryptoHelper): UserAccount? {
    return if (resultSet.next()) {
        val encryptedData = resultSet.getString("encrypted_user_data")
        val userJson = cryptoHelper.decrypt(encryptedData)
        extractUserFromJson(userJson)
    } else {
        null
    }
}

private fun extractCredentialFromResultSet(
    resultSet: ResultSet, 
    cryptoHelper: QuantumCryptoHelper
): Optional<RegisteredCredential> {
    return if (resultSet.next()) {
        val encryptedData = resultSet.getString("encrypted_credential_data")
        val credentialJson = cryptoHelper.decrypt(encryptedData)
        extractCredentialFromJson(credentialJson)
    } else {
        Optional.empty()
    }
}
