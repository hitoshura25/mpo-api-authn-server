plugins {
    kotlin("jvm") version "1.9.23"
    id("io.gitlab.arturbosch.detekt") version "1.23.7"
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1"
}

// Detekt configuration
detekt {
    buildUponDefaultConfig = true
    config.setFrom("$rootDir/detekt.yml")
    parallel = true
}

// ktlint configuration - enforce formatting and import standards
ktlint {
    version.set("1.0.1")
    android.set(false)
    ignoreFailures.set(false)
    reporters {
        reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.PLAIN)
        reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.CHECKSTYLE)
        reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.SARIF)
    }
    filter {
        exclude("**/generated/**")
        exclude("**/build/**")
    }
}

// Version constants
val webauthnVersion = "2.6.0"
val jacksonVersion = "2.16.1"
val bouncyCastleVersion = "1.78"
val cborVersion = "4.5.2"
val ktorClientVersion = "2.3.8"

group = "com.vmenon.webauthn"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    // WebAuthn Core (exposed as API for dependent projects)
    api("com.yubico:webauthn-server-core:$webauthnVersion")

    // JSON Processing (exposed as API for dependent projects)
    api("com.fasterxml.jackson.module:jackson-module-kotlin:$jacksonVersion")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:$jacksonVersion")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jdk8:$jacksonVersion")

    // Cryptography (exposed as API for dependent projects)
    api("org.bouncycastle:bcprov-jdk18on:$bouncyCastleVersion")
    api("org.bouncycastle:bcpkix-jdk18on:$bouncyCastleVersion")

    // CBOR for WebAuthn Data Encoding (exposed as API for dependent projects)
    api("com.upokecenter:cbor:$cborVersion")

    // HTTP Client for Test Flows
    implementation("io.ktor:ktor-client-core:$ktorClientVersion")
    implementation("io.ktor:ktor-client-content-negotiation:$ktorClientVersion")
    implementation("io.ktor:ktor-serialization-jackson:$ktorClientVersion")
}

kotlin {
    jvmToolchain(21)
}
