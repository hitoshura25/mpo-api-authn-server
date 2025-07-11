package com.vmenon.mpo.api.authn.yubico

import com.upokecenter.cbor.CBORObject
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import java.security.interfaces.ECPublicKey
import java.security.interfaces.RSAPublicKey

/**
 * Re-exports from WebAuthnCodecs and Crypto so tests can use it
 * Converted from Scala to Kotlin
 */
object WebAuthnTestCodecs {
    val ecPublicKeyToRaw = WebAuthnCodecs::ecPublicKeyToRaw
    fun ecPublicKeyToCose(key: ECPublicKey): ByteArray =
        WebAuthnCodecs.rawEcKeyToCose(ecPublicKeyToRaw(key))

    fun rsaPublicKeyToCose(
        key: RSAPublicKey,
        alg: COSEAlgorithmIdentifier
    ): ByteArray {
        val coseKey: MutableMap<Long, Any> = HashMap()
        coseKey[1L] = 3L // Key type: RSA
        coseKey[3L] = alg.id
        coseKey[-1L] = key.modulus.toByteArray() // public modulus n
        coseKey[-2L] = key.publicExponent.toByteArray() // public exponent e

        return ByteArray(CBORObject.FromObject(coseKey).EncodeToBytes())
    }
}
