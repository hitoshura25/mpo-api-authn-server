package com.vmenon.webauthn.testservice.testutils

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.yubico.webauthn.data.*
import java.security.*
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.util.*

/**
 * Simplified TestAuthenticator for HTTP service
 * Based on Yubico's WebAuthn TestAuthenticator but streamlined for our use case
 */
object SimpleTestAuthenticator {
    
    private val objectMapper = ObjectMapper().registerKotlinModule()
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
    
    private fun generateCredentialId(): com.yubico.webauthn.data.ByteArray {
        val id = kotlin.ByteArray(32)
        secureRandom.nextBytes(id)
        return com.yubico.webauthn.data.ByteArray(id)
    }
    
    private fun createAuthenticatorData(rpId: String, credentialId: com.yubico.webauthn.data.ByteArray, publicKey: ECPublicKey): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = sha256(rpId.toByteArray())
        val flags = 0x45.toByte() // UP=1, UV=1, AT=1
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x01)
        
        // AAGUID (16 bytes of zeros for test)
        val aaguid = kotlin.ByteArray(16)
        
        // Credential ID length (2 bytes)
        val credIdLength = byteArrayOf(
            (credentialId.size() shr 8).toByte(),
            (credentialId.size() and 0xFF).toByte()
        )
        
        // Public key in COSE format (simplified)
        val publicKeyCose = encodePublicKeyToCose(publicKey)
        
        return (rpIdHash + flags + counter + aaguid + credIdLength + credentialId.bytes + publicKeyCose).let {
            com.yubico.webauthn.data.ByteArray(it)
        }
    }
    
    private fun createSimpleAuthenticatorData(rpId: String): com.yubico.webauthn.data.ByteArray {
        val rpIdHash = sha256(rpId.toByteArray())
        val flags = 0x05.toByte() // UP=1, UV=1
        val counter = byteArrayOf(0x00, 0x00, 0x00, 0x02)
        
        return com.yubico.webauthn.data.ByteArray(rpIdHash + flags + counter)
    }
    
    private fun encodePublicKeyToCose(publicKey: ECPublicKey): kotlin.ByteArray {
        // Simplified COSE encoding for P-256 key
        val point = publicKey.w
        val x = point.affineX.toByteArray().let { if (it.size > 32) it.sliceArray(it.size - 32 until it.size) else it.padStart(32) }
        val y = point.affineY.toByteArray().let { if (it.size > 32) it.sliceArray(it.size - 32 until it.size) else it.padStart(32) }
        
        // COSE key map (simplified - this is a mock implementation)
        val coseKey = mapOf(
            1 to 2,    // kty: EC2
            3 to -7,   // alg: ES256
            -1 to 1,   // crv: P-256
            -2 to x,   // x coordinate
            -3 to y    // y coordinate
        )
        
        return cborEncode(coseKey)
    }
    
    private fun kotlin.ByteArray.padStart(length: Int): kotlin.ByteArray {
        return if (this.size >= length) this
        else kotlin.ByteArray(length - this.size) + this
    }
    
    private fun sha256(data: kotlin.ByteArray): kotlin.ByteArray {
        return MessageDigest.getInstance("SHA-256").digest(data)
    }
    
    private fun sign(data: kotlin.ByteArray, privateKey: PrivateKey): kotlin.ByteArray {
        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(privateKey)
        signature.update(data)
        return signature.sign()
    }
    
    /**
     * Simplified CBOR encoding (just for basic structures we need)
     * In a real implementation, you'd use a proper CBOR library
     */
    private fun cborEncode(obj: Any): kotlin.ByteArray {
        return when (obj) {
            is Map<*, *> -> {
                val bytes = mutableListOf<Byte>()
                bytes.add((0xa0 + obj.size).toByte()) // CBOR map
                obj.forEach { (key, value) ->
                    bytes.addAll(cborEncode(key!!).toList())
                    bytes.addAll(cborEncode(value!!).toList())
                }
                bytes.toByteArray()
            }
            is String -> {
                val strBytes = obj.toByteArray()
                val bytes = mutableListOf<Byte>()
                bytes.add((0x60 + strBytes.size).toByte()) // CBOR text string
                bytes.addAll(strBytes.toList())
                bytes.toByteArray()
            }
            is Int -> {
                when {
                    obj >= 0 && obj <= 23 -> byteArrayOf(obj.toByte())
                    obj > 23 -> byteArrayOf(0x18.toByte(), obj.toByte())
                    else -> byteArrayOf((0x20 - obj - 1).toByte())
                }
            }
            is kotlin.ByteArray -> {
                val bytes = mutableListOf<Byte>()
                bytes.add((0x40 + obj.size).toByte()) // CBOR byte string
                bytes.addAll(obj.toList())
                bytes.toByteArray()
            }
            else -> byteArrayOf() // Fallback
        }
    }
}