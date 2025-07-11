package com.vmenon.mpo.api.authn.yubico

import com.fasterxml.jackson.annotation.JsonInclude.Include
import com.fasterxml.jackson.core.Base64Variants
import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.json.JsonMapper
import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.dataformat.cbor.CBORFactory
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.upokecenter.cbor.CBORObject
import java.io.IOException

/**
Taken from https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/yubico-util/src/main/java/com/yubico/internal/util/JacksonCodecs.java
 */
object JacksonCodecs {
    fun cbor(): ObjectMapper {
        return ObjectMapper(CBORFactory()).setBase64Variant(Base64Variants.MODIFIED_FOR_URL)
    }

    fun json(): ObjectMapper {
        return JsonMapper.builder()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)
            .serializationInclusion(Include.NON_ABSENT)
            .defaultBase64Variant(Base64Variants.MODIFIED_FOR_URL)
            .addModule(Jdk8Module())
            .addModule(JavaTimeModule())
            .build()
    }

    fun deepCopy(a: CBORObject): CBORObject {
        return CBORObject.DecodeFromBytes(a.EncodeToBytes())
    }

    fun deepCopy(a: ObjectNode): ObjectNode {
        try {
            return json().readTree(json().writeValueAsString(a)) as ObjectNode
        } catch (e: IOException) {
            throw RuntimeException(e)
        }
    }
}