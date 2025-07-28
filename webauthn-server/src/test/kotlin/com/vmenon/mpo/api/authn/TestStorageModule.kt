package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.test_utils.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.test_utils.InMemoryCredentialStorage
import com.vmenon.mpo.api.authn.test_utils.InMemoryRegistrationRequestStorage
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