package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.databind.JsonNode

data class AuthenticationResponse(
    val requestId: String,
    val publicKeyCredentialRequestOptions: JsonNode,
)
