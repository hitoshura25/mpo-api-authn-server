package com.vmenon.mpo.api.authn.storage.redis

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.ScalableCredentialRepository
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredentialDescriptor
import java.util.Optional
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

/**
 * Redis-based implementation of ScalableCredentialRepository for multi-instance deployments
 */
class RedisCredentialRepository(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:creds:"
) : ScalableCredentialRepository {

    private val objectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
    }

    companion object {
        private const val CREDENTIALS_BY_USERNAME_PREFIX = "username:"
        private const val USER_BY_HANDLE_PREFIX = "handle:"

        fun create(
            host: String = "localhost",
            port: Int = 6379,
            password: String? = null,
            database: Int = 0,
            maxConnections: Int = 10
        ): RedisCredentialRepository {
            val config = JedisPoolConfig().apply {
                maxTotal = maxConnections
                maxIdle = maxConnections / 2
                minIdle = 1
                testOnBorrow = true
                testOnReturn = true
            }

            val jedisPool = if (password != null) {
                JedisPool(config, host, port, 2000, password, database)
            } else {
                JedisPool(config, host, port, 2000, null, database)
            }

            return RedisCredentialRepository(jedisPool)
        }
    }

    override fun addRegistration(registration: CredentialRegistration) {
        val username = registration.userAccount.username
        val userHandle = registration.userAccount.userHandle.base64Url

        jedisPool.resource.use { jedis ->
            // Store the registration by username (as a set member)
            val credentialsKey = "$keyPrefix$CREDENTIALS_BY_USERNAME_PREFIX$username"
            val registrationJson = objectMapper.writeValueAsString(registration)
            jedis.sadd(credentialsKey, registrationJson)

            // Store user account by handle for lookup
            val userHandleKey = "$keyPrefix$USER_BY_HANDLE_PREFIX$userHandle"
            val userAccountJson = objectMapper.writeValueAsString(registration.userAccount)
            jedis.set(userHandleKey, userAccountJson)
        }
    }

    override fun getRegistrationsByUsername(username: String): Set<CredentialRegistration> {
        val credentialsKey = "$keyPrefix$CREDENTIALS_BY_USERNAME_PREFIX$username"

        return jedisPool.resource.use { jedis ->
            val registrationJsons = jedis.smembers(credentialsKey)
            registrationJsons.map { json ->
                objectMapper.readValue(json, CredentialRegistration::class.java)
            }.toSet()
        }
    }

    override fun getUserByHandle(userHandle: ByteArray): UserAccount? {
        val userHandleKey = "$keyPrefix$USER_BY_HANDLE_PREFIX${userHandle.base64Url}"

        return jedisPool.resource.use { jedis ->
            val userAccountJson = jedis.get(userHandleKey)
            if (userAccountJson != null) {
                objectMapper.readValue(userAccountJson, UserAccount::class.java)
            } else {
                null
            }
        }
    }

    override fun getUserByUsername(username: String): UserAccount? {
        return getRegistrationsByUsername(username).firstOrNull()?.userAccount
    }

    override fun getCredentialIdsForUsername(username: String): Set<PublicKeyCredentialDescriptor> {
        return getRegistrationsByUsername(username)
            .map { registration ->
                PublicKeyCredentialDescriptor.builder()
                    .id(registration.credential.credentialId)
                    .build()
            }
            .toSet()
    }

    override fun getUserHandleForUsername(username: String): Optional<ByteArray> {
        return Optional.ofNullable(getUserByUsername(username)?.userHandle)
    }

    override fun getUsernameForUserHandle(userHandle: ByteArray): Optional<String> {
        return Optional.ofNullable(getUserByHandle(userHandle)?.username)
    }

    override fun lookup(credentialId: ByteArray, userHandle: ByteArray): Optional<RegisteredCredential> {
        val userAccount = getUserByHandle(userHandle) ?: return Optional.empty()

        return getRegistrationsByUsername(userAccount.username)
            .find { it.credential.credentialId == credentialId }
            ?.let { Optional.of(it.credential) }
            ?: Optional.empty()
    }

    override fun lookupAll(credentialId: ByteArray): Set<RegisteredCredential> {
        // This is less efficient in Redis but necessary for the interface
        // In a real implementation, you might want to maintain a separate index
        return jedisPool.resource.use { jedis ->
            val allUserKeys = jedis.keys("$keyPrefix$CREDENTIALS_BY_USERNAME_PREFIX*")
            allUserKeys.flatMap { key ->
                val registrationJsons = jedis.smembers(key)
                registrationJsons.mapNotNull { json ->
                    val registration = objectMapper.readValue(json, CredentialRegistration::class.java)
                    if (registration.credential.credentialId == credentialId) {
                        registration.credential
                    } else {
                        null
                    }
                }
            }.toSet()
        }
    }

    override fun close() {
        jedisPool.close()
    }
}
