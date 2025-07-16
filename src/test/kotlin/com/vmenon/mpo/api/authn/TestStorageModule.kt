package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryCredentialStorage
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryRegistrationRequestStorage
import org.koin.dsl.module

val testStorageModule = module {
    single<RegistrationRequestStorage> {
        InMemoryRegistrationRequestStorage()
    }

    single<AssertionRequestStorage> {
        InMemoryAssertionRequestStorage()
    }

    single<CredentialStorage> {
        InMemoryCredentialStorage()
    }
}