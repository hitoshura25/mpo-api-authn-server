plugins {
    kotlin("jvm") version "1.9.23"
}

group = "com.vmenon.webauthn"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    // WebAuthn Core (exposed as API for dependent projects)
    api("com.yubico:webauthn-server-core:2.5.0")
    
    // JSON Processing (exposed as API for dependent projects)
    api("com.fasterxml.jackson.module:jackson-module-kotlin:2.16.1")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.16.1")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jdk8:2.16.1")
    
    // Cryptography (exposed as API for dependent projects)
    api("org.bouncycastle:bcprov-jdk18on:1.77")
    api("org.bouncycastle:bcpkix-jdk18on:1.77")
    
    // CBOR for WebAuthn Data Encoding (exposed as API for dependent projects)
    api("com.upokecenter:cbor:4.5.2")
    
    // HTTP Client for Test Flows
    implementation("io.ktor:ktor-client-core:2.3.8")
    implementation("io.ktor:ktor-client-content-negotiation:2.3.8")
    implementation("io.ktor:ktor-serialization-jackson:2.3.8")
}

kotlin {
    jvmToolchain(21)
}