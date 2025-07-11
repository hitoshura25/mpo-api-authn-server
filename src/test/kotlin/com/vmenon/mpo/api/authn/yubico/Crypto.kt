import com.google.common.hash.Hashing
import com.yubico.webauthn.data.ByteArray

/**
 * Taken from https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/webauthn-server-core/src/main/java/com/yubico/webauthn/Crypto.java
 */
object Crypto {
    fun sha256(bytes: ByteArray): ByteArray {
        return ByteArray(Hashing.sha256().hashBytes(bytes.bytes).asBytes())
    }
}