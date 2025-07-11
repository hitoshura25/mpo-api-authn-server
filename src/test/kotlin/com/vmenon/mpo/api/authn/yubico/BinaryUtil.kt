/**
Taken from https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/yubico-util/src/main/java/com/yubico/internal/util/BinaryUtil.java
 */

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Arrays

object BinaryUtil {
    /**
     * @param hex String of hexadecimal digits to decode as bytes.
     */
    fun fromHex(hex: String): ByteArray {
        require(hex.length % 2 == 0) { "Length of hex string is not even: $hex" }

        val result = ByteArray(hex.length / 2)
        for (i in 0..<hex.length) {
            val d = hex[i].digitToIntOrNull(16) ?: -1
            require(d >= 0) { "Invalid hex digit at index $i in: $hex" }
            result[i / 2] = (result[i / 2].toInt() or (d shl (((i + 1) % 2) * 4))).toByte()
        }
        return result
    }

    /**
     * Copy `src` into `dest` beginning at the offset `destFrom`,
     * then return the modified `dest`.
     */
    fun copyInto(src: ByteArray, dest: ByteArray, destFrom: Int): ByteArray {
        require(dest.size - destFrom >= src.size) { "Source array will not fit in destination array" }
        require(destFrom >= 0) { "Invalid destination range" }

        for (i in src.indices) {
            dest[destFrom + i] = src[i]
        }

        return dest
    }

    /** Return a new array containing the concatenation of the argument `arrays`.  */
    fun concat(vararg arrays: ByteArray): ByteArray {
        val len = Arrays.stream(arrays).map { a: ByteArray -> a.size }
            .reduce(0) { a: Int, b: Int -> Integer.sum(a, b) }
        val result = ByteArray(len)
        var i = 0
        for (src in arrays) {
            copyInto(src, result, i)
            i += src.size
        }
        return result
    }

    fun encodeDerLength(length: Int): ByteArray {
        require(length >= 0) { "Length is negative: $length" }
        if (length <= 0x7f) {
            return byteArrayOf((length and 0xff).toByte())
        } else if (length <= 0xff) {
            return byteArrayOf((0x80 or 0x01).toByte(), (length and 0xff).toByte())
        } else if (length <= 0xffff) {
            return byteArrayOf(
                (0x80 or 0x02).toByte(), ((length shr 8) and 0xff).toByte(), (length and 0xff).toByte()
            )
        } else if (length <= 0xffffff) {
            return byteArrayOf(
                (0x80 or 0x03).toByte(),
                ((length shr 16) and 0xff).toByte(),
                ((length shr 8) and 0xff).toByte(),
                (length and 0xff).toByte()
            )
        } else {
            return byteArrayOf(
                (0x80 or 0x04).toByte(),
                ((length shr 24) and 0xff).toByte(),
                ((length shr 16) and 0xff).toByte(),
                ((length shr 8) and 0xff).toByte(),
                (length and 0xff).toByte()
            )
        }
    }

    fun encodeDerSequence(vararg items: ByteArray): ByteArray {
        val content: ByteArray = concat(*items)
        return concat(byteArrayOf(0x30), encodeDerLength(content.size), content)
    }

    fun encodeDerObjectId(oid: ByteArray): ByteArray {
        val result = ByteArray(2 + oid.size)
        result[0] = 0x06
        result[1] = oid.size.toByte()
        return copyInto(oid, result, 2)
    }

    fun encodeDerBitStringWithZeroUnused(content: ByteArray): ByteArray {
        return concat(
            byteArrayOf(0x03), encodeDerLength(1 + content.size), byteArrayOf(0), content
        )
    }

    fun encodeUint32(value: Long): ByteArray {
        val b: ByteBuffer = ByteBuffer.allocate(8)
        b.order(ByteOrder.BIG_ENDIAN)
        b.putLong(value)
        b.rewind()
        return b.array().copyOfRange(4, 8)
    }
}