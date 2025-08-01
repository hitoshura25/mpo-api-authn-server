package com.vmenon.mpo.api.authn

data class RegistrationCompleteRequest(
    val requestId: String,
    val credential: String,
)
