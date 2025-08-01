package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.RegisteredCredential

data class CredentialRegistration(
    val userAccount: UserAccount,
    val credential: RegisteredCredential,
    val registrationTime: Long = System.currentTimeMillis(),
)
