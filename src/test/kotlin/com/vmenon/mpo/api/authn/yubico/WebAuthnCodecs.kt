/*
Taken from https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/webauthn-server-core/src/main/java/com/yubico/webauthn/WebAuthnCodecs.java#L45
 */

package com.vmenon.mpo.api.authn.yubico

import BinaryUtil
import com.google.common.primitives.Bytes
import com.upokecenter.cbor.CBORObject
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import java.math.BigInteger
import java.security.KeyFactory
import java.security.NoSuchAlgorithmException
import java.security.PublicKey
import java.security.interfaces.ECPublicKey
import java.security.spec.InvalidKeySpecException
import java.security.spec.RSAPublicKeySpec
import java.security.spec.X509EncodedKeySpec
import java.util.Arrays
import kotlin.math.ceil

object WebAuthnCodecs {

    private val EC_PUBLIC_KEY_OID = ByteArray(
        byteArrayOf(
            0x2A, 0x86.toByte(), 0x48, 0xCE.toByte(), 0x3D, 2, 1
        )
    ) // OID 1.2.840.10045.2.1 ecPublicKey (ANSI X9.62 public key type)

    private val P256_CURVE_OID = ByteArray(
        byteArrayOf(
            0x2A, 0x86.toByte(), 0x48, 0xCE.toByte(), 0x3D, 3, 1, 7 // OID 1.2.840.10045.3.1.7
        )
    )

    private val P384_CURVE_OID = ByteArray(
        byteArrayOf(0x2B, 0x81.toByte(), 0x04, 0, 34)
    ) // OID 1.3.132.0.34

    private val P512_CURVE_OID = ByteArray(
        byteArrayOf(0x2B, 0x81.toByte(), 0x04, 0, 35)
    ) // OID 1.3.132.0.35

    private val ED25519_ALG_ID = ByteArray(
        byteArrayOf(
            // SEQUENCE (5 bytes)
            0x30,
            5,
            // OID (3 bytes)
            0x06,
            3,
            // OID 1.3.101.112
            0x2B,
            101,
            112
        )
    )

    fun ecPublicKeyToRaw(key: ECPublicKey): ByteArray {
        val fieldSizeBytes = ceil(key.params.curve.field.fieldSize / 8.0).toInt()
        val x = key.w.affineX.toByteArray()
        val y = key.w.affineY.toByteArray()
        val xPadding = ByteArray(maxOf(0, fieldSizeBytes - x.size))
        val yPadding = ByteArray(maxOf(0, fieldSizeBytes - y.size))

        Arrays.fill(xPadding, 0.toByte())
        Arrays.fill(yPadding, 0.toByte())

        return ByteArray(
            Bytes.concat(
                byteArrayOf(0x04),
                xPadding,
                x.copyOfRange(maxOf(0, x.size - fieldSizeBytes), x.size),
                yPadding,
                y.copyOfRange(maxOf(0, y.size - fieldSizeBytes), y.size)
            )
        )
    }

    fun rawEcKeyToCose(key: ByteArray): ByteArray {
        val keyBytes = key.bytes
        val len = keyBytes.size
        val lenSub1 = keyBytes.size - 1

        if (!(len == 64 || len == 96 || len == 132 ||
                    (keyBytes[0] == 0x04.toByte() && (lenSub1 == 64 || lenSub1 == 96 || lenSub1 == 132)))
        ) {
            throw IllegalArgumentException(
                "Raw key must be 64, 96 or 132 bytes long, or start with 0x04 and be 65, 97 or 133 bytes long; " +
                        "was ${keyBytes.size} bytes starting with ${String.format("%02x", keyBytes[0])}"
            )
        }

        val start = if (len == 64 || len == 96 || len == 132) 0 else 1
        val coordinateLength = (len - start) / 2

        val coseKey = mutableMapOf<Long, Any>()
        coseKey[1L] = 2L // Key type: EC

        val (coseAlg, coseCrv) = when (len - start) {
            64 -> COSEAlgorithmIdentifier.ES256 to 1
            96 -> COSEAlgorithmIdentifier.ES384 to 2
            132 -> COSEAlgorithmIdentifier.ES512 to 3
            else -> throw RuntimeException(
                "Failed to determine COSE EC algorithm. This should not be possible, please file a bug report."
            )
        }

        coseKey[3L] = coseAlg.id
        coseKey[-1L] = coseCrv
        coseKey[-2L] = keyBytes.copyOfRange(start, start + coordinateLength) // x
        coseKey[-3L] = keyBytes.copyOfRange(start + coordinateLength, start + 2 * coordinateLength) // y

        return ByteArray(CBORObject.FromObject(coseKey).EncodeToBytes())
    }

    @Throws(NoSuchAlgorithmException::class, InvalidKeySpecException::class)
    private fun importCoseRsaPublicKey(cose: CBORObject): PublicKey {
        val spec = RSAPublicKeySpec(
            BigInteger(1, cose.get(CBORObject.FromObject(-1)).GetByteString()),
            BigInteger(1, cose.get(CBORObject.FromObject(-2)).GetByteString())
        )
        return KeyFactory.getInstance("RSA").generatePublic(spec)
    }

    @Throws(NoSuchAlgorithmException::class, InvalidKeySpecException::class)
    private fun importCoseEcdsaPublicKey(cose: CBORObject): PublicKey {
        val crv = cose.get(CBORObject.FromObject(-1)).AsInt32Value()
        val x = cose.get(CBORObject.FromObject(-2)).GetByteString()
        val y = cose.get(CBORObject.FromObject(-3)).GetByteString()

        val curveOid = when (crv) {
            1 -> P256_CURVE_OID.bytes
            2 -> P384_CURVE_OID.bytes
            3 -> P512_CURVE_OID.bytes
            else -> throw IllegalArgumentException("Unknown COSE EC2 curve: $crv")
        }

        val algId = BinaryUtil.encodeDerSequence(
            BinaryUtil.encodeDerObjectId(EC_PUBLIC_KEY_OID.bytes),
            BinaryUtil.encodeDerObjectId(curveOid)
        )

        val rawKey = BinaryUtil.encodeDerBitStringWithZeroUnused(
            BinaryUtil.concat(
                byteArrayOf(0x04), // Raw EC public key with x and y
                x,
                y
            )
        )

        val x509Key = BinaryUtil.encodeDerSequence(algId, rawKey)
        val kFact = KeyFactory.getInstance("EC")
        return kFact.generatePublic(X509EncodedKeySpec(x509Key))
    }

    @Throws(InvalidKeySpecException::class, NoSuchAlgorithmException::class)
    private fun importCoseEdDsaPublicKey(cose: CBORObject): PublicKey {
        val curveId = cose.get(CBORObject.FromObject(-1)).AsInt32()
        return when (curveId) {
            6 -> importCoseEd25519PublicKey(cose)
            else -> throw IllegalArgumentException("Unsupported EdDSA curve: $curveId")
        }
    }

    @Throws(InvalidKeySpecException::class, NoSuchAlgorithmException::class)
    private fun importCoseEd25519PublicKey(cose: CBORObject): PublicKey {
        val rawKey = cose.get(CBORObject.FromObject(-2)).GetByteString()
        val x509Key = BinaryUtil.encodeDerSequence(
            ED25519_ALG_ID.bytes,
            BinaryUtil.encodeDerBitStringWithZeroUnused(rawKey)
        )

        val kFact = KeyFactory.getInstance("EdDSA")
        return kFact.generatePublic(X509EncodedKeySpec(x509Key))
    }

    fun getJavaAlgorithmName(alg: COSEAlgorithmIdentifier): String {
        return when (alg) {
            COSEAlgorithmIdentifier.EdDSA -> "EDDSA"
            COSEAlgorithmIdentifier.ES256 -> "SHA256withECDSA"
            COSEAlgorithmIdentifier.ES384 -> "SHA384withECDSA"
            COSEAlgorithmIdentifier.ES512 -> "SHA512withECDSA"
            COSEAlgorithmIdentifier.RS256 -> "SHA256withRSA"
            COSEAlgorithmIdentifier.RS384 -> "SHA384withRSA"
            COSEAlgorithmIdentifier.RS512 -> "SHA512withRSA"
            COSEAlgorithmIdentifier.RS1 -> "SHA1withRSA"
        }
    }
}
