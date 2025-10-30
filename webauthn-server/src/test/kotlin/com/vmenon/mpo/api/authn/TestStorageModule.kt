package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.repository.KeyRepository
import com.vmenon.mpo.api.authn.scheduler.KeyRotationScheduler
import com.vmenon.mpo.api.authn.security.JwtService
import com.vmenon.mpo.api.authn.security.KeyRotationService
import com.vmenon.mpo.api.authn.security.PostQuantumCryptographyService
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.testutils.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.testutils.InMemoryCredentialStorage
import com.vmenon.mpo.api.authn.testutils.InMemoryKeyRepository
import com.vmenon.mpo.api.authn.testutils.InMemoryRegistrationRequestStorage
import org.koin.dsl.module

val testStorageModule =
    module {
        single<RegistrationRequestStorage> {
            InMemoryRegistrationRequestStorage()
        }

        single<AssertionRequestStorage> {
            InMemoryAssertionRequestStorage()
        }

        single<CredentialStorage> {
            InMemoryCredentialStorage()
        }

        // JWT Key Rotation Infrastructure (in-memory for unit tests)
        single<KeyRepository> {
            InMemoryKeyRepository()
        }

        single<PostQuantumCryptographyService> {
            // Use Kyber768 post-quantum encryption for all sensitive data
            PostQuantumCryptographyService()
        }

        single {
            val keyRepository: KeyRepository by inject()
            val postQuantumCrypto: PostQuantumCryptographyService by inject()
            KeyRotationService(keyRepository, postQuantumCrypto).also { service ->
                // Initialize key rotation system (creates initial key if needed)
                service.initialize()
            }
        }

        // KeyRotationScheduler (exists for Application.kt injection, but doesn't run in tests)
        single {
            val keyRotationService: KeyRotationService by inject()
            KeyRotationScheduler(keyRotationService)
            // Note: We don't call .start() in tests - scheduler exists but doesn't run
        }

        // JWT Service for zero-trust architecture with key rotation
        single {
            val keyRotationService: KeyRotationService by inject()
            JwtService(keyRotationService)
        }
    }
