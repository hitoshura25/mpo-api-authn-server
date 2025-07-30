package com.vmenon.webauthn.testlib

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.upokecenter.cbor.CBORObject
import com.yubico.webauthn.data.*
import java.security.*
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.util.Base64

/**
 * Comprehensive WebAuthn Test Authenticator
 * Consolidates functionality from both server and test-service implementations
 */
object WebAuthnTestAuthenticator {
    
    private val objectMapper = ObjectMapper()
        .registerKotlinModule()
        .registerModule(Jdk8Module())
    private val secureRandom = SecureRandom()
    
    const val DEFAULT_RP_ID = "localhost"
    const val DEFAULT_ORIGIN = "https://localhost"
    
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
        origin: String = DEFAULT_ORIGIN
    ): PublicKeyCredential<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs> {
        
        val credentialId = generateCredentialId()
        
        // Create client data JSON
        val clientData = mapOf(
            "type" to "webauthn.create",
            "challenge" to Base64.getUrlEncoder().withoutPadding().encodeToString(challenge),
            "origin" to origin
        )
        val clientDataJson = objectMapper.writeValueAsString(clientData)
        val clientDataJsonBytes = com.yubico.webauthn.data.ByteArray(clientDataJson.toByteArray())
        
        // Create authenticator data
        val authenticatorData = createAuthenticatorData(rpId, credentialId, keyPair.public as ECPublicKey)
        
        // Create attestation object (using "none" format)
        val attestationObject = mapOf(
            "fmt" to "none",
            "attStmt" to emptyMap<String, Any>(),
            "authData" to authenticatorData.bytes
        )
        val attestationObjectBytes = com.yubico.webauthn.data.ByteArray(cborEncode(attestationObject))
        
        val response = AuthenticatorAttestationResponse.builder()
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
        origin: String = DEFAULT_ORIGIN
    ): PublicKeyCredential<AuthenticatorAssertionResponse, ClientAssertionExtensionOutputs> {
        
        // Create client data JSON
        val clientData = mapOf(
            "type" to "webauthn.get",
            "challenge" to Base64.getUrlEncoder().withoutPadding().encodeToString(challenge),
            "origin" to origin
        )
        val clientDataJson = objectMapper.writeValueAsString(clientData)
        val clientDataJsonBytes = com.yubico.webauthn.data.ByteArray(clientDataJson.toByteArray())
        
        // Create authenticator data (without attestation data for authentication)
        val authenticatorData = createSimpleAuthenticatorData(rpId)
        
        // Create signature
        val signatureData = authenticatorData.bytes + sha256(clientDataJsonBytes.bytes)
        val signature = sign(signatureData, keyPair.private)
        
        val response = AuthenticatorAssertionResponse.builder()
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
    
    // Helper methods...
    private fun generateCredentialId(): com.yubico.webauthn.data.ByteArray {
        val id = kotlin.ByteArray(32)
        secureRandom.nextBytes(id)
        return com.yubico.webauthn.data.ByteArray(id)
    }
    
    private fun createAuthenticatorData(rpId: String, credentialId: com.yubico.webauthn.data.ByteArray, publicKey: ECPublicKey): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = sha256(rpId.toByteArray())
        val flags = 0x45.toByte() // UP=1, UV=1, AT=1
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x01)
        val aaguid = kotlin.ByteArray(16)
        val credIdLength = byteArrayOf((credentialId.size() shr 8).toByte(), (credentialId.size() and 0xFF).toByte())
        val publicKeyCose = encodePublicKeyToCose(publicKey)
        
        return com.yubico.webauthn.data.ByteArray(rpIdHash + flags + counter + aaguid + credIdLength + credentialId.bytes + publicKeyCose)
    }
    
    private fun createSimpleAuthenticatorData(rpId: String): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = sha256(rpId.toByteArray())
        val flags = 0x05.toByte() // UP=1, UV=1
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x02)
        return com.yubico.webauthn.data.ByteArray(rpIdHash + flags + counter)
    }
    
    private fun encodePublicKeyToCose(publicKey: ECPublicKey): kotlin.ByteArray {
        val point = publicKey.w
        val x = point.affineX.toByteArray().let { if (it.size > 32) it.sliceArray(it.size - 32 until it.size) else it.padStart(32) }
        val y = point.affineY.toByteArray().let { if (it.size > 32) it.sliceArray(it.size - 32 until it.size) else it.padStart(32) }
        
        val coseKey = mapOf(1 to 2, 3 to -7, -1 to 1, -2 to x, -3 to y)
        return cborEncode(coseKey)
    }
    
    private fun kotlin.ByteArray.padStart(length: Int): kotlin.ByteArray =
        if (this.size >= length) this else kotlin.ByteArray(length - this.size) + this
    
    private fun sha256(data: kotlin.ByteArray): kotlin.ByteArray =
        MessageDigest.getInstance("SHA-256").digest(data)
    
    private fun sign(data: kotlin.ByteArray, privateKey: PrivateKey): kotlin.ByteArray {
        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(privateKey)
        signature.update(data)
        return signature.sign()
    }
    
    private fun cborEncode(obj: Any): kotlin.ByteArray {
        val cborObj = when (obj) {
            is Map<*, *> -> {
                val cborMap = CBORObject.NewMap()
                obj.forEach { (key, value) -> cborMap[toCBORObject(key!!)] = toCBORObject(value!!) }
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