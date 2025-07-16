package com.vmenon.mpo.api.authn.storage.postgresql

import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import com.yubico.webauthn.RegisteredCredential
import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import java.util.Optional
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import javax.sql.DataSource

/**
 * Secure PostgreSQL-based credential repository with application-level encryption
 * This encrypts sensitive data before storing it in the database
 */
class SecurePostgreSQLCredentialStorage(
    private val dataSource: DataSource,
    private val encryptionKey: SecretKey
) : CredentialStorage {

    companion object {
        private const val ENCRYPTION_ALGORITHM = "AES/GCM/NoPadding"
        private const val GCM_IV_LENGTH = 12
        private const val GCM_TAG_LENGTH = 16

        fun create(
            host: String = "localhost",
            port: Int = 5432,
            database: String = "webauthn",
            username: String = "webauthn_user",
            password: String = "webauthn_password",
            maxPoolSize: Int = 10,
            encryptionKeyBase64: String? = null
        ): SecurePostgreSQLCredentialStorage {
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

                // Enhanced security settings
                addDataSourceProperty("ssl", "true")
                addDataSourceProperty("sslmode", "require")
                addDataSourceProperty("loginTimeout", "30")
            }

            val dataSource = HikariDataSource(config)

            // Generate or load encryption key
            val encryptionKey = if (encryptionKeyBase64 != null) {
                val keyBytes = Base64.getDecoder().decode(encryptionKeyBase64)
                SecretKeySpec(keyBytes, "AES")
            } else {
                generateEncryptionKey()
            }

            val storage = SecurePostgreSQLCredentialStorage(dataSource, encryptionKey)
            storage.initializeTables()
            return storage
        }

        private fun generateEncryptionKey(): SecretKey {
            val keyGen = KeyGenerator.getInstance("AES")
            keyGen.init(256) // AES-256
            return keyGen.generateKey()
        }
    }

    private fun encrypt(data: String): String {
        val cipher = Cipher.getInstance(ENCRYPTION_ALGORITHM)
        val iv = ByteArray(GCM_IV_LENGTH)
        SecureRandom().nextBytes(iv)

        val parameterSpec = GCMParameterSpec(GCM_TAG_LENGTH * 8, iv)
        cipher.init(Cipher.ENCRYPT_MODE, encryptionKey, parameterSpec)

        val encryptedData = cipher.doFinal(data.toByteArray())
        val encryptedWithIv = iv + encryptedData

        return Base64.getEncoder().encodeToString(encryptedWithIv)
    }

    private fun decrypt(encryptedData: String): String {
        val encryptedWithIv = Base64.getDecoder().decode(encryptedData)
        val iv = encryptedWithIv.sliceArray(0 until GCM_IV_LENGTH)
        val encrypted = encryptedWithIv.sliceArray(GCM_IV_LENGTH until encryptedWithIv.size)

        val cipher = Cipher.getInstance(ENCRYPTION_ALGORITHM)
        val parameterSpec = GCMParameterSpec(GCM_TAG_LENGTH * 8, iv)
        cipher.init(Cipher.DECRYPT_MODE, encryptionKey, parameterSpec)

        val decryptedData = cipher.doFinal(encrypted)
        return String(decryptedData)
    }

    private fun initializeTables() {
        dataSource.connection.use { connection ->
            // Create users table with encrypted data
            val createUsersTable = """
                CREATE TABLE IF NOT EXISTS webauthn_users_secure (
                    user_handle_hash CHAR(64) PRIMARY KEY,
                    username_hash CHAR(64) UNIQUE NOT NULL,
                    encrypted_user_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """.trimIndent()

            // Create credentials table with encrypted data
            val createCredentialsTable = """
                CREATE TABLE IF NOT EXISTS webauthn_credentials_secure (
                    credential_id_hash CHAR(64) PRIMARY KEY,
                    user_handle_hash CHAR(64) NOT NULL REFERENCES webauthn_users_secure(user_handle_hash) ON DELETE CASCADE,
                    encrypted_credential_data TEXT NOT NULL,
                    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """.trimIndent()

            // Create indexes for performance (on hashes only)
            val createIndexes = arrayOf(
                "CREATE INDEX IF NOT EXISTS idx_webauthn_users_secure_username ON webauthn_users_secure(username_hash)",
                "CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_secure_user ON webauthn_credentials_secure(user_handle_hash)"
            )

            connection.createStatement().use { statement ->
                statement.execute(createUsersTable)
                statement.execute(createCredentialsTable)
                createIndexes.forEach { statement.execute(it) }
            }
        }
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

                // Encrypt user data
                val encryptedUserData = encrypt(objectMapper.writeValueAsString(registration.userAccount))

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

                // Encrypt credential data
                val encryptedCredentialData = encrypt(objectMapper.writeValueAsString(registration))

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
}