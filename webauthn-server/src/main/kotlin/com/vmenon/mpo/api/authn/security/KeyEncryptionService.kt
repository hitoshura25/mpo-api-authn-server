package com.vmenon.mpo.api.authn.security

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Service for encrypting and decrypting JWT private keys at rest.
 *
 * Uses AES-256-GCM for authenticated encryption, providing both confidentiality
 * and integrity protection for private keys stored in the database.
 */
interface KeyEncryptionService {
    /**
     * Encrypt plaintext data.
     *
     * @param plaintext The data to encrypt (e.g., PEM-encoded private key)
     * @return Base64-encoded ciphertext with embedded IV
     */
    fun encrypt(plaintext: String): String

    /**
     * Decrypt ciphertext back to plaintext.
     *
     * @param ciphertext Base64-encoded encrypted data
     * @return Original plaintext
     * @throws Exception if decryption fails (wrong key, tampered data, etc.)
     */
    fun decrypt(ciphertext: String): String
}

/**
 * AES-GCM implementation of KeyEncryptionService.
 *
 * Security properties:
 * - Algorithm: AES-256-GCM (Galois/Counter Mode)
 * - Key size: 256 bits (derived from master key via SHA-256)
 * - Authentication tag: 128 bits (detects tampering)
 * - IV: 12-byte random nonce (MUST be unique per encryption to prevent CWE-323)
 *
 * IV/Nonce Security (Addresses Semgrep kotlin.lang.security.gcm-detection):
 * Each encryption operation explicitly generates a cryptographically random 12-byte IV
 * using SecureRandom. The IV is stored with the ciphertext and must never be reused
 * with the same key, as this would break GCM's confidentiality and authenticity guarantees.
 * Semgrep finding is acknowledged and suppressed with justification in code comments.
 *
 * Format of encrypted data: [IV_LENGTH(1 byte)][IV(12 bytes)][CIPHERTEXT + AUTH_TAG]
 *
 * @param masterKey Master encryption key from environment variable
 */
class AesGcmKeyEncryptionService(masterKey: String) : KeyEncryptionService {
    private val secretKey: SecretKeySpec

    private companion object {
        const val GCM_TAG_LENGTH_BITS = 128 // bits (16 bytes) - detects tampering
    }

    private val gcmTagLength = GCM_TAG_LENGTH_BITS

    init {
        // Derive 256-bit AES key from master key using SHA-256
        // This ensures consistent key derivation regardless of master key length
        val keyBytes = MessageDigest.getInstance("SHA-256").digest(masterKey.toByteArray())
        secretKey = SecretKeySpec(keyBytes, "AES")
    }

    override fun encrypt(plaintext: String): String {
        // nosemgrep: kotlin.lang.security.gcm-detection.gcm-detection
        // Justification: IV/nonce uniqueness is guaranteed by explicit SecureRandom generation.
        // Each encryption operation generates a fresh random 12-byte IV, preventing CWE-323
        // (nonce reuse). The IV is stored with ciphertext and never reused with the same key.
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")

        // Explicitly generate unique random IV to prevent nonce reuse (CWE-323)
        val iv = ByteArray(12) // GCM standard IV length (96 bits)
        SecureRandom().nextBytes(iv)

        val parameterSpec = GCMParameterSpec(gcmTagLength, iv)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, parameterSpec)

        val encryptedBytes = cipher.doFinal(plaintext.toByteArray())

        // Combine IV and ciphertext (IV doesn't need to be secret, but must be unique)
        // Format: [IV_LENGTH(1 byte)][IV(12 bytes)][CIPHERTEXT + AUTH_TAG]
        val combined = ByteArray(1 + iv.size + encryptedBytes.size)
        combined[0] = iv.size.toByte()
        System.arraycopy(iv, 0, combined, 1, iv.size)
        System.arraycopy(encryptedBytes, 0, combined, 1 + iv.size, encryptedBytes.size)

        return Base64.getEncoder().encodeToString(combined)
    }

    override fun decrypt(ciphertext: String): String {
        // nosemgrep: kotlin.lang.security.gcm-detection.gcm-detection
        // Justification: GCMParameterSpec usage is safe - IV is extracted from ciphertext
        // (where it was stored during encryption). Each ciphertext has its own unique IV.
        val combined = Base64.getDecoder().decode(ciphertext)

        // Extract IV length from first byte
        val ivLength = combined[0].toInt()

        // Extract IV and encrypted data
        val iv = ByteArray(ivLength)
        val encryptedBytes = ByteArray(combined.size - 1 - ivLength)

        System.arraycopy(combined, 1, iv, 0, ivLength)
        System.arraycopy(combined, 1 + ivLength, encryptedBytes, 0, encryptedBytes.size)

        // Decrypt with extracted IV
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, secretKey, GCMParameterSpec(gcmTagLength, iv))

        val decryptedBytes = cipher.doFinal(encryptedBytes)
        return String(decryptedBytes)
    }
}
