package com.vmenon.mpo.api.authn

data class RegistrationResponse(
    val requestId: String,
    val publicKeyCredentialCreationOptions: String
)
