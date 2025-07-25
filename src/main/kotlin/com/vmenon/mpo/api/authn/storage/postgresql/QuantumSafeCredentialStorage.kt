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
import java.util.Optional
import javax.sql.DataSource

/**
 * Quantum-safe PostgreSQL credential storage - secure by default for new projects
 * Uses Kyber768 + AES-256-GCM hybrid encryption for all data
 */
class QuantumSafeCredentialStorage(
    private val dataSource: DataSource
) : CredentialStorage {

    private val cryptoService = PostQuantumCryptographyService()

    companion object {
        fun create(
            host: String,
            port: Int,
            database: String,
            username: String,
            password: String,
            maxPoolSize: Int
        ): QuantumSafeCredentialStorage {
            val config = HikariConfig().apply {
                jdbcUrl = "jdbc:postgresql://$host:$port/$database?sslmode=disable"
                this.username = username
                this.password = password
                maximumPoolSize = maxPoolSize
                minimumIdle = 2
                connectionTimeout = 30000
                idleTimeout = 600000
                maxLifetime = 1800000
                leakDetectionThreshold = 60000
            }

            val dataSource = HikariDataSource(config)
            return QuantumSafeCredentialStorage(dataSource)
        }
    }

    private fun encrypt(data: String) = cryptoService.encrypt(data)

    private fun decrypt(encryptedDataString: String): String {
        val parts = encryptedDataString.split("|")
        require(parts.size >= 4) { "Invalid encrypted data format" }

        val method = parts[0]
        val data = parts[1]
        val keyMaterial = parts[2]
        val metadata = if (parts.size > 3) {
            parts[3].split(",").associate {
                val kv = it.split("=", limit = 2)
                if (kv.size == 2) kv[0] to kv[1] else kv[0] to ""
            }
        } else emptyMap()

        return cryptoService.decrypt(
            com.vmenon.mpo.api.authn.security.EncryptedData(
                method,
                data,
                keyMaterial,
                metadata
            )
        )
    }

    private fun encryptedDataToString(encrypted: com.vmenon.mpo.api.authn.security.EncryptedData): String {
        val metadataStr = encrypted.metadata.entries.joinToString(",") { "${it.key}=${it.value}" }
        return "${encrypted.method}|${encrypted.data}|${encrypted.keyMaterial}|$metadataStr"
    }

    private fun hash(data: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hashBytes = digest.digest(data.toByteArray())
        return hashBytes.joinToString("") { "%02x".format(it) }
    }

    override fun addRegistration(registration: CredentialRegistration) {
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                val userHandleHash = hash(registration.userAccount.userHandle.base64Url)
                val usernameHash = hash(registration.userAccount.username)
                val credentialIdHash = hash(registration.credential.credentialId.base64Url)

                // Encrypt user data with quantum-safe encryption
                val encryptedUserData = encryptedDataToString(
                    encrypt(objectMapper.writeValueAsString(registration.userAccount))
                )

                // Insert or update user
                val insertUserSQL = """
                    INSERT INTO webauthn_users_secure (user_handle_hash, username_hash, encrypted_user_data) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT (username_hash) DO UPDATE SET 
                        encrypted_user_data = EXCLUDED.encrypted_user_data
                """.trimIndent()

                connection.prepareStatement(insertUserSQL).use { statement ->
                    statement.setString(1, userHandleHash)
                    statement.setString(2, usernameHash)
                    statement.setString(3, encryptedUserData)
                    statement.executeUpdate()
                }

                // Encrypt credential data with quantum-safe encryption
                val encryptedCredentialData = encryptedDataToString(
                    encrypt(objectMapper.writeValueAsString(registration))
                )

                // Insert credential
                val insertCredentialSQL = """
                    INSERT INTO webauthn_credentials_secure 
                    (credential_id_hash, user_handle_hash, encrypted_credential_data) 
                    VALUES (?, ?, ?)
                    ON CONFLICT (credential_id_hash) DO UPDATE SET
                        encrypted_credential_data = EXCLUDED.encrypted_credential_data
                """.trimIndent()

                connection.prepareStatement(insertCredentialSQL).use { statement ->
                    statement.setString(1, credentialIdHash)
                    statement.setString(2, userHandleHash)
                    statement.setString(3, encryptedCredentialData)
                    statement.executeUpdate()
                }

                connection.commit()
            } catch (e: Exception) {
                connection.rollback()
                throw e
            }
        }
    }

    override fun getRegistrationsByUsername(username: String): Set<CredentialRegistration> {
        val usernameHash = hash(username)
        val sql = """
            SELECT c.encrypted_credential_data 
            FROM webauthn_credentials_secure c
            JOIN webauthn_users_secure u ON c.user_handle_hash = u.user_handle_hash
            WHERE u.username_hash = ?
        """.trimIndent()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, usernameHash)
                statement.executeQuery().use { resultSet ->
                    buildSet {
                        while (resultSet.next()) {
                            val encryptedData = resultSet.getString("encrypted_credential_data")
                            val credentialJson = decrypt(encryptedData)
                            add(objectMapper.readValue(credentialJson, CredentialRegistration::class.java))
                        }
                    }
                }
            }
        }
    }

    override fun getUserByHandle(userHandle: com.yubico.webauthn.data.ByteArray): UserAccount? {
        val userHandleHash = hash(userHandle.base64Url)
        val sql = "SELECT encrypted_user_data FROM webauthn_users_secure WHERE user_handle_hash = ?"

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, userHandleHash)
                statement.executeQuery().use { resultSet ->
                    if (resultSet.next()) {
                        val encryptedData = resultSet.getString("encrypted_user_data")
                        val userJson = decrypt(encryptedData)
                        objectMapper.readValue(userJson, UserAccount::class.java)
                    } else null
                }
            }
        }
    }

    override fun getUserByUsername(username: String): UserAccount? {
        val usernameHash = hash(username)
        val sql = "SELECT encrypted_user_data FROM webauthn_users_secure WHERE username_hash = ?"

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, usernameHash)
                statement.executeQuery().use { resultSet ->
                    if (resultSet.next()) {
                        val encryptedData = resultSet.getString("encrypted_user_data")
                        val userJson = decrypt(encryptedData)
                        objectMapper.readValue(userJson, UserAccount::class.java)
                    } else null
                }
            }
        }
    }

    override fun userExists(username: String): Boolean {
        val usernameHash = hash(username)
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

    override fun lookup(
        credentialId: com.yubico.webauthn.data.ByteArray,
        userHandle: com.yubico.webauthn.data.ByteArray
    ): Optional<RegisteredCredential> {
        val credentialIdHash = hash(credentialId.base64Url)
        val userHandleHash = hash(userHandle.base64Url)

        val sql = """
            SELECT encrypted_credential_data 
            FROM webauthn_credentials_secure 
            WHERE credential_id_hash = ? AND user_handle_hash = ?
        """.trimIndent()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, credentialIdHash)
                statement.setString(2, userHandleHash)
                statement.executeQuery().use { resultSet ->
                    if (resultSet.next()) {
                        val encryptedData = resultSet.getString("encrypted_credential_data")
                        val credentialJson = decrypt(encryptedData)
                        val registration = objectMapper.readValue(credentialJson, CredentialRegistration::class.java)
                        Optional.of(registration.credential)
                    } else {
                        Optional.empty()
                    }
                }
            }
        }
    }

    override fun lookupAll(credentialId: com.yubico.webauthn.data.ByteArray): Set<RegisteredCredential> {
        val credentialIdHash = hash(credentialId.base64Url)
        val sql = "SELECT encrypted_credential_data FROM webauthn_credentials_secure WHERE credential_id_hash = ?"

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                statement.setString(1, credentialIdHash)
                statement.executeQuery().use { resultSet ->
                    buildSet {
                        while (resultSet.next()) {
                            val encryptedData = resultSet.getString("encrypted_credential_data")
                            val credentialJson = decrypt(encryptedData)
                            val registration =
                                objectMapper.readValue(credentialJson, CredentialRegistration::class.java)
                            add(registration.credential)
                        }
                    }
                }
            }
        }
    }

    override fun close() {
        (dataSource as Closeable).close()
    }
}
