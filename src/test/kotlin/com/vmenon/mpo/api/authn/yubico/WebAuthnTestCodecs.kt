package com.vmenon.mpo.api.authn.yubico

import Crypto
import com.upokecenter.cbor.CBORObject
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import java.security.KeyFactory
import java.security.PrivateKey
import java.security.PublicKey
import java.security.interfaces.ECPublicKey
import java.security.interfaces.RSAPublicKey
import java.security.spec.PKCS8EncodedKeySpec
import org.bouncycastle.jcajce.provider.asymmetric.edec.BCEdDSAPublicKey

/**
 * Re-exports from WebAuthnCodecs and Crypto so tests can use it
 * Converted from Scala to Kotlin
 */
object WebAuthnTestCodecs {

    fun sha256(bytes: ByteArray): ByteArray = Crypto.sha256(bytes)

    val ecPublicKeyToRaw = WebAuthnCodecs::ecPublicKeyToRaw
    val importCosePublicKey = WebAuthnCodecs::importCosePublicKey

    fun ecPublicKeyToCose(key: ECPublicKey): ByteArray =
        WebAuthnCodecs.rawEcKeyToCose(ecPublicKeyToRaw(key))

    fun publicKeyToCose(key: PublicKey): ByteArray {
        return when (key) {
            is ECPublicKey -> ecPublicKeyToCose(key)
            else -> throw UnsupportedOperationException(
                "Unknown key type: ${key.javaClass.canonicalName}"
            )
        }
    }

    fun importPrivateKey(
        encodedKey: ByteArray,
        alg: COSEAlgorithmIdentifier
    ): PrivateKey {
        return when (alg) {
            COSEAlgorithmIdentifier.ES256,
            COSEAlgorithmIdentifier.ES384,
            COSEAlgorithmIdentifier.ES512 -> {
                val keyFactory = KeyFactory.getInstance("EC")
                val spec = PKCS8EncodedKeySpec(encodedKey.bytes)
                keyFactory.generatePrivate(spec)
            }

            COSEAlgorithmIdentifier.EdDSA -> {
                val keyFactory = KeyFactory.getInstance("EdDSA")
                val spec = PKCS8EncodedKeySpec(encodedKey.bytes)
                keyFactory.generatePrivate(spec)
            }

            COSEAlgorithmIdentifier.RS256,
            COSEAlgorithmIdentifier.RS384,
            COSEAlgorithmIdentifier.RS512,
            COSEAlgorithmIdentifier.RS1 -> {
                val keyFactory = KeyFactory.getInstance("RSA")
                val spec = PKCS8EncodedKeySpec(encodedKey.bytes)
                keyFactory.generatePrivate(spec)
            }

            else -> throw UnsupportedOperationException("Unsupported algorithm: $alg")
        }
    }

    fun importEcdsaPrivateKey(encodedKey: ByteArray): PrivateKey {
        val keyFactory = KeyFactory.getInstance("EC")
        val spec = PKCS8EncodedKeySpec(encodedKey.bytes)
        return keyFactory.generatePrivate(spec)
    }

    fun eddsaPublicKeyToCose(key: BCEdDSAPublicKey): ByteArray {
        val coseKey: MutableMap<Long, Any> = HashMap()
        coseKey[1L] = 1L // Key type: octet key pair
        coseKey[3L] = COSEAlgorithmIdentifier.EdDSA.id
        coseKey[-1L] = 6L // crv: Ed25519
        coseKey[-2L] = key.encoded.takeLast(32).toByteArray() // Strip ASN.1 prefix

        return ByteArray(CBORObject.FromObject(coseKey).EncodeToBytes())
    }

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

    fun getCoseKty(encodedPublicKey: ByteArray): Int {
        val cose = CBORObject.DecodeFromBytes(encodedPublicKey.bytes)
        val kty = cose.get(CBORObject.FromObject(1)).AsInt32()
        return kty
    }
}
