package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.ScalableCredentialRepository
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryCredentialRepository
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryRegistrationRequestStorage
import org.koin.dsl.module

val testStorageModule = module {
    single<RegistrationRequestStorage> {
        InMemoryRegistrationRequestStorage()
    }

    single<AssertionRequestStorage> {
        InMemoryAssertionRequestStorage()
    }

    single<ScalableCredentialRepository> {
        InMemoryCredentialRepository()
    }
}