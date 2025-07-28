package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.data.ByteArray

data class UserAccount(
    val username: String,
    val displayName: String,
    val userHandle: ByteArray
)