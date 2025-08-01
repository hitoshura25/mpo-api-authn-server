package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.databind.JsonNode

data class RegistrationResponse(
    val requestId: String,
    val publicKeyCredentialCreationOptions: JsonNode,
)
