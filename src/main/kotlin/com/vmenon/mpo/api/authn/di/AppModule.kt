package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.yubico.CredentialRepositoryImpl
import com.yubico.webauthn.CredentialRepository
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.data.RelyingPartyIdentity
import org.koin.core.qualifier.named
import org.koin.dsl.module

/**
 * Koin dependency injection module for WebAuthn application with separated storage interfaces
 */
val appModule = module {
    single(named("relyingPartyId")) {
        System.getProperty("RELYING_PARTY_ID") ?: System.getenv("RELYING_PARTY_ID") ?: "localhost"
    }

    single(named("relyingPartyName")) {
        System.getProperty("RELYING_PARTY_NAME") ?: System.getenv("RELYING_PARTY_NAME") ?: "WebAuthn Demo"
    }

    single<CredentialRepository> {
        val credentialStorage: CredentialStorage by inject()
        CredentialRepositoryImpl(credentialStorage)
    }

    single {
        val relyingPartyId: String by inject(named("relyingPartyId"))
        val relyingPartyName: String by inject(named("relyingPartyName"))
        val credentialRepository: CredentialRepository by inject()

        RelyingParty.builder()
            .identity(
                RelyingPartyIdentity.builder()
                    .id(relyingPartyId)
                    .name(relyingPartyName)
                    .build()
            )
            .credentialRepository(credentialRepository)
            .build()
    }
}
