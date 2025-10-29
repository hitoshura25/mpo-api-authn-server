package com.vmenon.mpo.api.authn.security

import com.fasterxml.jackson.module.kotlin.readValue
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import org.bouncycastle.jce.provider.BouncyCastleProvider
import org.bouncycastle.pqc.crypto.crystals.kyber.KyberKEMExtractor
import org.bouncycastle.pqc.crypto.crystals.kyber.KyberKEMGenerator
import org.bouncycastle.pqc.crypto.crystals.kyber.KyberPrivateKeyParameters
import org.bouncycastle.pqc.crypto.util.PrivateKeyFactory
import org.bouncycastle.pqc.crypto.util.PublicKeyFactory
import org.bouncycastle.pqc.jcajce.provider.BouncyCastlePQCProvider
import org.bouncycastle.pqc.jcajce.spec.KyberParameterSpec
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.SecureRandom
import java.security.Security
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Post-Quantum Cryptography service providing quantum-resistant encryption by default
 * Uses Kyber768 KEM + AES-256-GCM hybrid approach for optimal security and performance
 */
class PostQuantumCryptographyService {
    companion object {
        // Hybrid approach: AES-256-GCM for data + Kyber768 for key encapsulation
        private const val AES_ALGORITHM = "AES/GCM/NoPadding"
        private const val GCM_IV_LENGTH = 12
        private const val GCM_TAG_LENGTH = 16
        private const val PQ_KEM_ALGORITHM = "Kyber"
        private const val PQ_KEM_SPEC = "kyber768" // NIST Level 3 security
        private const val AES_KEY_SIZE_BYTES = 32 // 256 bits / 8
        private const val BITS_PER_BYTE = 8
        private const val KYBER768_ENCAPSULATION_SIZE = 1088 // Kyber768 specific
        private const val AES_KEY_SIZE_BITS = 256 // AES-256

        // Reuse shared Jackson mapper for JSON serialization
        private val objectMapper = JacksonUtils.objectMapper

        init {
            // Register BouncyCastle post-quantum provider
            Security.addProvider(BouncyCastleProvider())
            Security.addProvider(BouncyCastlePQCProvider())
        }
    }

    /**
     * Encrypts data using quantum-safe hybrid encryption (Kyber768 KEM + AES-256-GCM)
     */
    fun encrypt(data: String): EncryptedData {
        // Generate AES key for data encryption
        val aesKey = generateAESKey()

        // Encrypt data with AES-256-GCM
        val cipher = Cipher.getInstance(AES_ALGORITHM)
        val iv = ByteArray(GCM_IV_LENGTH)
        SecureRandom().nextBytes(iv)

        val parameterSpec = GCMParameterSpec(GCM_TAG_LENGTH * BITS_PER_BYTE, iv)
        cipher.init(Cipher.ENCRYPT_MODE, aesKey, parameterSpec)
        val encryptedData = cipher.doFinal(data.toByteArray())

        // Generate Kyber key pair for KEM
        val kyberKeyPair = generateKyberKeyPair()

        // Use BouncyCastle Kyber KEM to encapsulate a shared secret
        val kyberPublicKeyBC = PublicKeyFactory.createKey(kyberKeyPair.public.encoded)
        val kemGenerator = KyberKEMGenerator(SecureRandom())
        val secretWithEncapsulation = kemGenerator.generateEncapsulated(kyberPublicKeyBC)

        val kemSharedSecret = secretWithEncapsulation.secret
        val kemEncapsulation = secretWithEncapsulation.encapsulation

        // Use the KEM shared secret to encrypt our AES key
        val kemAesKey = SecretKeySpec(kemSharedSecret.sliceArray(0 until AES_KEY_SIZE_BYTES), "AES")
        val kemCipher = Cipher.getInstance(AES_ALGORITHM)
        val kemIv = ByteArray(GCM_IV_LENGTH)
        SecureRandom().nextBytes(kemIv)

        val kemParamSpec = GCMParameterSpec(GCM_TAG_LENGTH * BITS_PER_BYTE, kemIv)
        kemCipher.init(Cipher.ENCRYPT_MODE, kemAesKey, kemParamSpec)
        val encryptedAESKey = kemCipher.doFinal(aesKey.encoded)

        // Combine all components
        val payload = iv + encryptedData
        val keyMaterial = kemIv + encryptedAESKey + kemEncapsulation + kyberKeyPair.private.encoded

        return EncryptedData(
            method = "KYBER768-AES256-GCM",
            data = Base64.getEncoder().encodeToString(payload),
            keyMaterial = Base64.getEncoder().encodeToString(keyMaterial),
            metadata =
                mapOf(
                    "aes_algorithm" to AES_ALGORITHM,
                    "kem_algorithm" to PQ_KEM_SPEC,
                    "security_level" to "post-quantum",
                    "nist_level" to "3",
                    "created" to System.currentTimeMillis().toString(),
                ),
        )
    }

    /**
     * Decrypts quantum-safe encrypted data
     */
    fun decrypt(encryptedData: EncryptedData): String {
        require(encryptedData.method == "KYBER768-AES256-GCM") {
            "Unsupported encryption method: ${encryptedData.method}"
        }

        val payload = Base64.getDecoder().decode(encryptedData.data)
        val keyMaterial = Base64.getDecoder().decode(encryptedData.keyMaterial)

        // Extract components from payload
        val iv = payload.sliceArray(0 until GCM_IV_LENGTH)
        val encrypted = payload.sliceArray(GCM_IV_LENGTH until payload.size)

        // Extract components from keyMaterial
        val kemIv = keyMaterial.sliceArray(0 until GCM_IV_LENGTH)
        val encryptedAESKeySize = AES_KEY_SIZE_BYTES + GCM_TAG_LENGTH
        val encryptedAESKey =
            keyMaterial.sliceArray(
                GCM_IV_LENGTH until GCM_IV_LENGTH + encryptedAESKeySize,
            )

        val kemEncapsulationStart = GCM_IV_LENGTH + encryptedAESKeySize
        val kemEncapsulationSize = KYBER768_ENCAPSULATION_SIZE
        val kemEncapsulation =
            keyMaterial.sliceArray(
                kemEncapsulationStart until kemEncapsulationStart + kemEncapsulationSize,
            )

        val kyberPrivateKeyBytes =
            keyMaterial.sliceArray(
                kemEncapsulationStart + kemEncapsulationSize until keyMaterial.size,
            )

        // Use BouncyCastle Kyber KEM to extract the shared secret
        val kyberPrivateKeyBC =
            PrivateKeyFactory.createKey(
                kyberPrivateKeyBytes,
            ) as KyberPrivateKeyParameters
        val kemExtractor = KyberKEMExtractor(kyberPrivateKeyBC)
        val kemSharedSecret = kemExtractor.extractSecret(kemEncapsulation)

        // Use KEM shared secret to decrypt the AES key
        val kemAesKey = SecretKeySpec(kemSharedSecret.sliceArray(0 until AES_KEY_SIZE_BYTES), "AES")
        val kemCipher = Cipher.getInstance(AES_ALGORITHM)
        val kemParamSpec = GCMParameterSpec(GCM_TAG_LENGTH * BITS_PER_BYTE, kemIv)
        kemCipher.init(Cipher.DECRYPT_MODE, kemAesKey, kemParamSpec)
        val aesKeyBytes = kemCipher.doFinal(encryptedAESKey)

        // Decrypt the actual data
        val aesKey = SecretKeySpec(aesKeyBytes, "AES")
        val cipher = Cipher.getInstance(AES_ALGORITHM)
        val parameterSpec = GCMParameterSpec(GCM_TAG_LENGTH * BITS_PER_BYTE, iv)
        cipher.init(Cipher.DECRYPT_MODE, aesKey, parameterSpec)

        return String(cipher.doFinal(encrypted))
    }

    /**
     * Convenience method: Encrypt data and serialize to JSON string.
     * Compatible with String-based storage (database TEXT columns).
     *
     * @param plaintext Data to encrypt
     * @return JSON string representation of EncryptedData
     */
    fun encryptToString(plaintext: String): String {
        val encryptedData = encrypt(plaintext)
        return objectMapper.writeValueAsString(encryptedData)
    }

    /**
     * Convenience method: Deserialize JSON string and decrypt data.
     * Compatible with String-based storage (database TEXT columns).
     *
     * @param encryptedJson JSON string representation of EncryptedData
     * @return Decrypted plaintext
     */
    fun decryptFromString(encryptedJson: String): String {
        val encryptedData: EncryptedData = objectMapper.readValue(encryptedJson)
        return decrypt(encryptedData)
    }

    private fun generateAESKey(): SecretKey {
        val keyGen = KeyGenerator.getInstance("AES")
        keyGen.init(AES_KEY_SIZE_BITS)
        return keyGen.generateKey()
    }

    private fun generateKyberKeyPair(): KeyPair {
        val keyPairGen = KeyPairGenerator.getInstance(PQ_KEM_ALGORITHM, "BCPQC")
        keyPairGen.initialize(KyberParameterSpec.kyber768, SecureRandom())
        return keyPairGen.generateKeyPair()
    }
}

/**
 * Data class representing encrypted data with metadata
 */
data class EncryptedData(
    // Encryption method used
    val method: String,
    // Base64 encoded encrypted data
    val data: String,
    // Base64 encoded key material
    val keyMaterial: String,
    // Additional metadata
    val metadata: Map<String, String> = emptyMap(),
)
