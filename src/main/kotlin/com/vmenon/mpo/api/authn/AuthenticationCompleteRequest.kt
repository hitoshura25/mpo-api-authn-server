package com.vmenon.mpo.api.authn

data class AuthenticationCompleteRequest(
    val requestId: String,
    val credential: String
)
