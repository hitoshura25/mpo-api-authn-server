package com.vmenon.webauthn.testlib

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.upokecenter.cbor.CBORObject
import com.yubico.webauthn.data.AuthenticatorAssertionResponse
import com.yubico.webauthn.data.AuthenticatorAttestationResponse
import com.yubico.webauthn.data.ClientAssertionExtensionOutputs
import com.yubico.webauthn.data.ClientRegistrationExtensionOutputs
import com.yubico.webauthn.data.PublicKeyCredential
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.SecureRandom
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.util.Base64

/**
 * Comprehensive WebAuthn Test Authenticator
 * Consolidates functionality from both server and test-service implementations
 */
object WebAuthnTestAuthenticator {
    private val objectMapper =
        ObjectMapper()
            .registerKotlinModule()
            .registerModule(Jdk8Module())
    private val secureRandom = SecureRandom()

    const val DEFAULT_RP_ID = "localhost"
    const val DEFAULT_ORIGIN = "https://localhost"

    // Constants for magic numbers
    const val CREDENTIAL_ID_SIZE = 32
    const val USER_PRESENT_USER_VERIFIED_ATTESTED = 0x45
    const val USER_PRESENT_USER_VERIFIED = 0x05
    const val AAGUID_SIZE = 16
    const val COORDINATE_SIZE = 32
    const val COSE_KEY_TYPE_EC2 = 2
    const val COSE_ALG_ES256 = -7
    const val COSE_EC2_CURVE_P256 = 1
    const val COSE_EC2_X = -2
    const val COSE_EC2_Y = -3
    const val COSE_KEY_TYPE = 1
    const val COSE_ALG = 3
    const val COSE_EC2_CURVE = -1
    const val BITS_PER_BYTE = 8
    const val BYTE_MASK = 0xFF

    /**
     * Generate a test EC key pair using P-256 curve
     */
    fun generateKeyPair(): KeyPair {
        val keyPairGenerator = KeyPairGenerator.getInstance("EC")
        val ecSpec = ECGenParameterSpec("secp256r1") // P-256
        keyPairGenerator.initialize(ecSpec, secureRandom)
        return keyPairGenerator.generateKeyPair()
    }

    /**
     * Create a test registration credential
     */
    fun createRegistrationCredential(
        challenge: ByteArray,
        keyPair: KeyPair,
        rpId: String = DEFAULT_RP_ID,
        origin: String = DEFAULT_ORIGIN,
    ): PublicKeyCredential<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs> {
        val credentialId = generateCredentialId()

        // Create client data JSON
        val clientData =
            mapOf(
                "type" to "webauthn.create",
                "challenge" to Base64.getUrlEncoder().withoutPadding().encodeToString(challenge),
                "origin" to origin,
            )
        val clientDataJson = objectMapper.writeValueAsString(clientData)
        val clientDataJsonBytes = com.yubico.webauthn.data.ByteArray(clientDataJson.toByteArray())

        // Create authenticator data
        val authenticatorData =
            createAuthenticatorData(rpId, credentialId, keyPair.public as ECPublicKey)

        // Create attestation object (using "none" format)
        val attestationObject =
            mapOf(
                "fmt" to "none",
                "attStmt" to emptyMap<String, Any>(),
                "authData" to authenticatorData.bytes,
            )
        val attestationObjectBytes =
            com.yubico.webauthn.data.ByteArray(
                WebAuthnCryptoHelper.cborEncode(attestationObject),
            )

        val response =
            AuthenticatorAttestationResponse.builder()
                .attestationObject(attestationObjectBytes)
                .clientDataJSON(clientDataJsonBytes)
                .build()

        return PublicKeyCredential.builder<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs>()
            .id(credentialId)
            .response(response)
            .clientExtensionResults(ClientRegistrationExtensionOutputs.builder().build())
            .build()
    }

    /**
     * Create a test authentication credential
     */
    fun createAuthenticationCredential(
        challenge: ByteArray,
        credentialId: ByteArray,
        keyPair: KeyPair,
        rpId: String = DEFAULT_RP_ID,
        origin: String = DEFAULT_ORIGIN,
    ): PublicKeyCredential<AuthenticatorAssertionResponse, ClientAssertionExtensionOutputs> {
        // Create client data JSON
        val clientData =
            mapOf(
                "type" to "webauthn.get",
                "challenge" to Base64.getUrlEncoder().withoutPadding().encodeToString(challenge),
                "origin" to origin,
            )
        val clientDataJson = objectMapper.writeValueAsString(clientData)
        val clientDataJsonBytes = com.yubico.webauthn.data.ByteArray(clientDataJson.toByteArray())

        // Create authenticator data (without attestation data for authentication)
        val authenticatorData = createSimpleAuthenticatorData(rpId)

        // Create signature
        val signatureData = authenticatorData.bytes + WebAuthnCryptoHelper.sha256(clientDataJsonBytes.bytes)
        val signature = WebAuthnCryptoHelper.sign(signatureData, keyPair.private)

        val response =
            AuthenticatorAssertionResponse.builder()
                .authenticatorData(authenticatorData)
                .clientDataJSON(clientDataJsonBytes)
                .signature(com.yubico.webauthn.data.ByteArray(signature))
                .build()

        return PublicKeyCredential.builder<AuthenticatorAssertionResponse, ClientAssertionExtensionOutputs>()
            .id(com.yubico.webauthn.data.ByteArray(credentialId))
            .response(response)
            .clientExtensionResults(ClientAssertionExtensionOutputs.builder().build())
            .build()
    }

    private fun generateCredentialId(): com.yubico.webauthn.data.ByteArray {
        val id = kotlin.ByteArray(CREDENTIAL_ID_SIZE)
        secureRandom.nextBytes(id)
        return com.yubico.webauthn.data.ByteArray(id)
    }

    private fun createAuthenticatorData(
        rpId: String,
        credentialId: com.yubico.webauthn.data.ByteArray,
        publicKey: ECPublicKey,
    ): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = WebAuthnCryptoHelper.sha256(rpId.toByteArray())
        val flags = USER_PRESENT_USER_VERIFIED_ATTESTED.toByte()
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x01)
        val aaguid = kotlin.ByteArray(AAGUID_SIZE)
        val credIdLength =
            byteArrayOf(
                (credentialId.size() shr BITS_PER_BYTE).toByte(),
                (credentialId.size() and BYTE_MASK).toByte(),
            )
        val publicKeyCose = WebAuthnCryptoHelper.encodePublicKeyToCose(publicKey)

        return com.yubico.webauthn.data.ByteArray(
            rpIdHash + flags + counter + aaguid + credIdLength + credentialId.bytes + publicKeyCose,
        )
    }

    private fun createSimpleAuthenticatorData(rpId: String): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = WebAuthnCryptoHelper.sha256(rpId.toByteArray())
        val flags = USER_PRESENT_USER_VERIFIED.toByte()
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x02)
        return com.yubico.webauthn.data.ByteArray(rpIdHash + flags + counter)
    }
}

/**
 * Helper functions for COSE and cryptographic operations
 */
object WebAuthnCryptoHelper {
    fun encodePublicKeyToCose(publicKey: ECPublicKey): kotlin.ByteArray {
        val point = publicKey.w
        val x =
            point.affineX.toByteArray().let {
                if (it.size > WebAuthnTestAuthenticator.COORDINATE_SIZE) {
                    it.sliceArray(it.size - WebAuthnTestAuthenticator.COORDINATE_SIZE until it.size)
                } else {
                    it.padStart(WebAuthnTestAuthenticator.COORDINATE_SIZE)
                }
            }
        val y =
            point.affineY.toByteArray().let {
                if (it.size > WebAuthnTestAuthenticator.COORDINATE_SIZE) {
                    it.sliceArray(it.size - WebAuthnTestAuthenticator.COORDINATE_SIZE until it.size)
                } else {
                    it.padStart(WebAuthnTestAuthenticator.COORDINATE_SIZE)
                }
            }

        val coseKey =
            mapOf(
                WebAuthnTestAuthenticator.COSE_KEY_TYPE to WebAuthnTestAuthenticator.COSE_KEY_TYPE_EC2,
                WebAuthnTestAuthenticator.COSE_ALG to WebAuthnTestAuthenticator.COSE_ALG_ES256,
                WebAuthnTestAuthenticator.COSE_EC2_CURVE to WebAuthnTestAuthenticator.COSE_EC2_CURVE_P256,
                WebAuthnTestAuthenticator.COSE_EC2_X to x,
                WebAuthnTestAuthenticator.COSE_EC2_Y to y,
            )
        return cborEncode(coseKey)
    }

    fun kotlin.ByteArray.padStart(length: Int): kotlin.ByteArray =
        if (this.size >= length) this else kotlin.ByteArray(length - this.size) + this

    fun sha256(data: kotlin.ByteArray): kotlin.ByteArray =
        MessageDigest.getInstance(
            "SHA-256",
        ).digest(data)

    fun sign(
        data: kotlin.ByteArray,
        privateKey: PrivateKey,
    ): kotlin.ByteArray {
        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(privateKey)
        signature.update(data)
        return signature.sign()
    }

    fun cborEncode(obj: Any): kotlin.ByteArray {
        val cborObj =
            when (obj) {
                is Map<*, *> -> {
                    val cborMap = CBORObject.NewMap()
                    obj.forEach {
                            (key, value) ->
                        cborMap[toCBORObject(key!!)] = toCBORObject(value!!)
                    }
                    cborMap
                }
                else -> toCBORObject(obj)
            }
        return cborObj.EncodeToBytes()
    }

    private fun toCBORObject(obj: Any): CBORObject {
        return when (obj) {
            is String -> CBORObject.FromObject(obj)
            is Int -> CBORObject.FromObject(obj)
            is kotlin.ByteArray -> CBORObject.FromObject(obj)
            is com.yubico.webauthn.data.ByteArray -> CBORObject.FromObject(obj.bytes)
            is Map<*, *> -> {
                val cborMap = CBORObject.NewMap()
                obj.forEach { (key, value) -> cborMap[toCBORObject(key!!)] = toCBORObject(value!!) }
                cborMap
            }
            else -> CBORObject.FromObject(obj)
        }
    }
}
