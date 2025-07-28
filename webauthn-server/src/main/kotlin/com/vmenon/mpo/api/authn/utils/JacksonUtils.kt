package com.vmenon.mpo.api.authn.utils

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule

/**
 * Shared test utilities to avoid duplication across test classes
 */
object JacksonUtils {

    /**
     * Pre-configured ObjectMapper for WebAuthn testing with all necessary modules
     */
    val objectMapper: ObjectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
        registerModule(Jdk8Module())
    }
}