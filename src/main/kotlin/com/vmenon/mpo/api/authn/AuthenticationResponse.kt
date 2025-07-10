package com.vmenon.mpo.api.authn

data class AuthenticationResponse(
    val requestId: String,
    val publicKeyCredentialRequestOptions: String
)
