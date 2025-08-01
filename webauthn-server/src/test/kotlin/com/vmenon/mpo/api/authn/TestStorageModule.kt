package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.testutils.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.testutils.InMemoryCredentialStorage
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
    }
