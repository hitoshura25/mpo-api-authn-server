package com.vmenon.mpo.api.authn.yubico

import BinaryUtil
import Crypto
import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.node.JsonNodeFactory
import com.fasterxml.jackson.databind.node.ObjectNode
import com.yubico.webauthn.data.AuthenticatorAssertionResponse
import com.yubico.webauthn.data.AuthenticatorAttestationResponse
import com.yubico.webauthn.data.AuthenticatorDataFlags
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import com.yubico.webauthn.data.ClientAssertionExtensionOutputs
import com.yubico.webauthn.data.ClientRegistrationExtensionOutputs
import com.yubico.webauthn.data.PublicKeyCredential
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.security.interfaces.ECPublicKey
import java.security.interfaces.RSAPublicKey
import java.security.spec.ECGenParameterSpec
import org.bouncycastle.jce.provider.BouncyCastleProvider

/**
 * Taken from https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/webauthn-server-core/src/test/scala/com/yubico/webauthn/TestAuthenticator.scala
 */
object TestAuthenticator {

    object Defaults {
        val aaguid = ByteArray(
            byteArrayOf(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
        )
        val challenge: ByteArray = ByteArray(
            byteArrayOf(0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 16, 105, 121, 98, 91)
        )
        val keyAlgorithm = COSEAlgorithmIdentifier.ES256
        const val rpId = "localhost"
        const val origin = "https://$rpId"

        object TokenBinding {
            const val status = "supported"
            const val id = "None"
        }
    }

    sealed class AttestationMaker {
        abstract val format: String

        abstract fun makeAttestationStatement(
            authDataBytes: ByteArray,
            clientDataJson: ByteArray
        ): JsonNode

        open val certChain: List<Pair<X509Certificate, PrivateKey>> = emptyList()

        fun makeAttestationObjectBytes(
            authDataBytes: ByteArray,
            clientDataJson: ByteArray
        ): ByteArray {
            val attObj = jsonMap { f ->
                mapOf(
                    "authData" to f.binaryNode(authDataBytes.bytes),
                    "fmt" to f.textNode(format),
                    "attStmt" to makeAttestationStatement(authDataBytes, clientDataJson)
                )
            }
            return ByteArray(JacksonCodecs.cbor().writeValueAsBytes(attObj))
        }

        companion object {
            fun none(): AttestationMaker = NoneAttestationMaker()
        }
    }

    private class NoneAttestationMaker : AttestationMaker() {
        override val format: String = "none"

        override fun makeAttestationStatement(
            authDataBytes: ByteArray,
            clientDataJson: ByteArray
        ): JsonNode {
            return JacksonCodecs.json().createObjectNode()
        }
    }

    fun makeAttestedCredentialDataBytes(
        publicKeyCose: ByteArray,
        aaguid: ByteArray = Defaults.aaguid
    ): ByteArray {
        val credentialId = sha256(publicKeyCose)

        val bytes = mutableListOf<Byte>()
        bytes.addAll(aaguid.bytes.toList())
        bytes.addAll(BinaryUtil.fromHex("0020").toList())
        bytes.addAll(credentialId.bytes.toList())
        bytes.addAll(publicKeyCose.bytes.toList())
        return ByteArray(bytes.toByteArray())
    }

    /**
     * Create an unattested credential for testing registration
     */
    fun createUnattestedCredentialForRegistration(
        challenge: ByteArray,
        keyPair: KeyPair
    ): Triple<
            PublicKeyCredential<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs>,
            KeyPair,
            List<Pair<X509Certificate, PrivateKey>>
            > {
        val authData = createAuthenticatorData(
            keyPair = keyPair
        )
        return createAuthenticatorAttestationCredential(
            authDataBytes = authData,
            credentialKeypair = keyPair,
            clientDataJson = createClientData(challenge = challenge, "webauthn.create"),
            attestationMaker = AttestationMaker.none()
        )
    }

    /**
     * Create an unattested credential for testing authentication
     */
    fun createUnattestedCredentialForAuthentication(
        challenge: ByteArray,
        allowedCredentialId: ByteArray,
        keyPair: KeyPair,
    ): PublicKeyCredential<AuthenticatorAssertionResponse, ClientAssertionExtensionOutputs> {
        val authDataBytes: ByteArray =
            makeAuthDataBytes(
                rpId = Defaults.rpId,
                signatureCount = 1338
            )
        val clientDataJson = createClientData(challenge = challenge, "webauthn.get")
        val clientDataJsonBytes = toBytes(
            clientDataJson
        )
        val response = AuthenticatorAssertionResponse.builder()
            .authenticatorData(authDataBytes)
            .clientDataJSON(clientDataJsonBytes)
            .signature(
                makeAssertionSignature(
                    authDataBytes,
                    Crypto.sha256(clientDataJsonBytes),
                    keyPair.private,
                )
            )
            .build()

        val credential =
            PublicKeyCredential.builder<AuthenticatorAssertionResponse, ClientAssertionExtensionOutputs>()
                .id(allowedCredentialId)
                .response(response)
                .clientExtensionResults(ClientAssertionExtensionOutputs.builder().build())
                .build()
        return credential
    }

    /**
     * Create authenticator data for testing
     */
    fun createAuthenticatorData(
        aaguid: ByteArray = Defaults.aaguid,
        keyPair: KeyPair,
        keyAlgorithm: COSEAlgorithmIdentifier = Defaults.keyAlgorithm
    ): ByteArray {
        val publicKeyCose = when (val pub = keyPair.public) {
            is ECPublicKey -> WebAuthnTestCodecs.ecPublicKeyToCose(pub)
            is RSAPublicKey -> WebAuthnTestCodecs.rsaPublicKeyToCose(pub, keyAlgorithm)
            // Note: BCEdDSAPublicKey handling would need proper import
            else -> throw IllegalArgumentException("Unsupported public key type: ${pub.javaClass}")
        }

        val authDataBytes = makeAuthDataBytes(
            rpId = Defaults.rpId,
            attestedCredentialDataBytes = makeAttestedCredentialDataBytes(
                aaguid = aaguid,
                publicKeyCose = publicKeyCose
            )
        )

        return authDataBytes
    }

    /**
     * Create authenticator data bytes
     */
    fun makeAuthDataBytes(
        rpId: String = Defaults.rpId,
        flags: AuthenticatorDataFlags? = null,
        signatureCount: Int? = null,
        attestedCredentialDataBytes: ByteArray? = null,
        extensionsCborBytes: ByteArray? = null
    ): ByteArray {
        val atFlag = if (attestedCredentialDataBytes != null) 0x40 else 0x00
        val edFlag = if (extensionsCborBytes != null) 0x80 else 0x00

        val flagsByte = (flags?.value ?: 0x00.toByte()).toInt() or 0x01 or atFlag or edFlag

        val bytes = mutableListOf<Byte>()

        // RP ID hash (32 bytes)
        bytes.addAll(sha256(rpId).bytes.toList())

        // Flags (1 byte)
        bytes.add(flagsByte.toByte())

        // Signature counter (4 bytes)
        val counterBytes = BinaryUtil.encodeUint32((signatureCount ?: 1337).toLong())
        bytes.addAll(counterBytes.toList())

        // Attested credential data (variable length)
        attestedCredentialDataBytes?.let {
            bytes.addAll(it.bytes.toList())
        }

        // Extensions (variable length)
        extensionsCborBytes?.let {
            bytes.addAll(it.bytes.toList())
        }

        return ByteArray(bytes.toByteArray())
    }

    private fun toBytes(s: String): ByteArray = ByteArray(s.toByteArray(Charsets.UTF_8))

    fun sha256(s: String): ByteArray = sha256(toBytes(s))

    fun sha256(b: ByteArray): ByteArray =
        ByteArray(MessageDigest.getInstance("SHA-256").digest(b.bytes))

    /**
     * Create a credential for testing
     */
    fun createAuthenticatorAttestationCredential(
        authDataBytes: ByteArray,
        credentialKeypair: KeyPair,
        attestationMaker: AttestationMaker,
        clientDataJson: String,
        clientExtensions: ClientRegistrationExtensionOutputs =
            ClientRegistrationExtensionOutputs.builder().build()
    ): Triple<
            PublicKeyCredential<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs>,
            KeyPair,
            List<Pair<X509Certificate, PrivateKey>>
            > {
        val clientDataJsonBytes = toBytes(
            clientDataJson
        )

        val attestationObjectBytes = attestationMaker.makeAttestationObjectBytes(
            authDataBytes,
            clientDataJsonBytes
        )

        val response = AuthenticatorAttestationResponse.builder()
            .attestationObject(attestationObjectBytes)
            .clientDataJSON(clientDataJsonBytes)
            .build()

        val credential =
            PublicKeyCredential.builder<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs>()
                .id(response.attestation.authenticatorData.attestedCredentialData.get().credentialId)
                .response(response)
                .clientExtensionResults(clientExtensions)
                .build()

        return Triple(
            credential,
            credentialKeypair,
            attestationMaker.certChain.map { (cert, key) -> Pair(cert, key) }
        )
    }

    /**
     * Create client data JSON for WebAuthn testing
     */
    fun createClientData(
        challenge: ByteArray,
        type: String,
        clientData: JsonNode? = null,
        origin: String = Defaults.origin,
        tokenBindingStatus: String = Defaults.TokenBinding.status,
        tokenBindingId: String? = Defaults.TokenBinding.id
    ): String {
        return JacksonCodecs.json().writeValueAsString(
            clientData ?: run {
                val objectMapper = JacksonCodecs.json()
                val rootNode = objectMapper.createObjectNode()

                rootNode.put("challenge", challenge.base64Url)
                rootNode.put("origin", origin)
                rootNode.put("type", type)

                if (tokenBindingStatus === "present") {
                    val tokenBinding = objectMapper.createObjectNode()
                    tokenBinding.put("status", tokenBindingStatus)
                    tokenBindingId?.let { id ->
                        tokenBinding.put("id", id)
                    }
                    rootNode.set<JsonNode>("tokenBinding", tokenBinding)
                }
                rootNode
            }
        )
    }

    /**
     * Helper function to create JSON ObjectNode from a map builder
     */
    private fun <V : JsonNode> jsonMap(
        mapBuilder: (JsonNodeFactory) -> Map<String, V>
    ): ObjectNode {
        val factory = JacksonCodecs.json().nodeFactory
        val objectNode = factory.objectNode()
        val map = mapBuilder(factory)

        map.forEach { (key, value) ->
            objectNode.set<JsonNode>(key, value)
        }

        return objectNode
    }

    private val random = SecureRandom()

    fun generateKeypair(algorithm: COSEAlgorithmIdentifier): KeyPair =
        when (algorithm) {
            COSEAlgorithmIdentifier.EdDSA -> generateEddsaKeypair()
            COSEAlgorithmIdentifier.ES256 -> generateEcKeypair("secp256r1")
            COSEAlgorithmIdentifier.ES384 -> generateEcKeypair("secp384r1")
            COSEAlgorithmIdentifier.ES512 -> generateEcKeypair("secp521r1")
            COSEAlgorithmIdentifier.RS256,
            COSEAlgorithmIdentifier.RS384,
            COSEAlgorithmIdentifier.RS512,
            COSEAlgorithmIdentifier.RS1 -> generateRsaKeypair()
        }

    fun generateEcKeypair(curve: String = "secp256r1"): KeyPair {
        val ecSpec = ECGenParameterSpec(curve)

        // Need to use BouncyCastle provider here because JDK15 standard providers do not support secp256k1
        val g: KeyPairGenerator =
            KeyPairGenerator.getInstance("EC", BouncyCastleProvider())

        g.initialize(ecSpec, random)

        return g.generateKeyPair()
    }

    fun generateEddsaKeypair(): KeyPair {
        val alg = "Ed25519"
        // Need to use BouncyCastle provider here because JDK before 14 does not support EdDSA
        val keyPairGenerator =
            KeyPairGenerator.getInstance(alg, BouncyCastleProvider())
        return keyPairGenerator.generateKeyPair()
    }

    fun generateRsaKeypair(): KeyPair {
        val keyPairGenerator = KeyPairGenerator.getInstance("RSA")
        keyPairGenerator.initialize(2048, random)
        return keyPairGenerator.generateKeyPair()
    }

    fun makeAssertionSignature(
        authenticatorData: ByteArray,
        clientDataHash: ByteArray,
        key: PrivateKey,
        alg: COSEAlgorithmIdentifier = COSEAlgorithmIdentifier.ES256
    ): ByteArray =
        sign(authenticatorData.concat(clientDataHash), key, alg)

    fun sign(
        data: ByteArray,
        key: PrivateKey,
        alg: COSEAlgorithmIdentifier
    ): ByteArray {
        val jAlg = WebAuthnCodecs.getJavaAlgorithmName(alg)

        // Need to use BouncyCastle provider here because JDK15 standard providers do not support secp256k1
        val sig = java.security.Signature.getInstance(jAlg, BouncyCastleProvider())

        sig.initSign(key)
        sig.update(data.bytes)
        val signedData = sig.sign()
        return ByteArray(signedData)
    }
}
