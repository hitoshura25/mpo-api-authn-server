package com.vmenon.mpo.api.authn.security

import java.security.MessageDigest
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
 * - IV: Random 12-byte nonce (unique per encryption)
 *
 * Format of encrypted data: [IV_LENGTH(1 byte)][IV(12 bytes)][CIPHERTEXT + AUTH_TAG]
 *
 * @param masterKey Master encryption key from environment variable
 */
class AesGcmKeyEncryptionService(masterKey: String) : KeyEncryptionService {
    private val secretKey: SecretKeySpec
    private val gcmTagLength = 128 // bits (16 bytes)

    init {
        // Derive 256-bit AES key from master key using SHA-256
        // This ensures consistent key derivation regardless of master key length
        val keyBytes = MessageDigest.getInstance("SHA-256").digest(masterKey.toByteArray())
        secretKey = SecretKeySpec(keyBytes, "AES")
    }

    override fun encrypt(plaintext: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")

        // Initialize with random IV (GCM mode generates unique IV automatically)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)

        val iv = cipher.iv
        val encryptedBytes = cipher.doFinal(plaintext.toByteArray())

        // Combine IV and ciphertext into single byte array
        // Format: [IV_LENGTH(1 byte)][IV][ENCRYPTED_DATA + AUTH_TAG]
        val combined = ByteArray(1 + iv.size + encryptedBytes.size)
        combined[0] = iv.size.toByte()
        System.arraycopy(iv, 0, combined, 1, iv.size)
        System.arraycopy(encryptedBytes, 0, combined, 1 + iv.size, encryptedBytes.size)

        return Base64.getEncoder().encodeToString(combined)
    }

    override fun decrypt(ciphertext: String): String {
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
