plugins {
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("application")
    id("org.jetbrains.kotlinx.kover") version "0.9.1"
}

val kotlinVersion = "1.9.23"
val ktorVersion = "2.3.7"
val junitVersion = "5.11.3"
val webauthnVersion = "2.6.0"
val jacksonVersion = "2.16.1"
val logbackVersion = "1.4.14"
val mockkVersion = "1.13.8"
val bouncyCastleVersion = "1.81"

group = "com.vmenon.mpo.api.authn"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib")
    implementation("com.yubico:webauthn-server-core:$webauthnVersion")
    implementation("io.ktor:ktor-server-netty:$ktorVersion")
    implementation("io.ktor:ktor-server-core:$ktorVersion")
    implementation("io.ktor:ktor-server-content-negotiation:$ktorVersion")
    implementation("io.ktor:ktor-serialization-jackson:$ktorVersion")
    implementation("io.ktor:ktor-server-status-pages:$ktorVersion")
    implementation("io.ktor:ktor-server-cors:$ktorVersion")
    implementation("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:$jacksonVersion")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:$jacksonVersion")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jdk8:${jacksonVersion}")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-cbor:${jacksonVersion}")

    implementation("ch.qos.logback:logback-classic:$logbackVersion")

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter-api:$junitVersion")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:$junitVersion")
    testImplementation("io.ktor:ktor-server-test-host:$ktorVersion")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:$kotlinVersion")
    testImplementation("io.mockk:mockk:$mockkVersion")
    testImplementation("com.upokecenter:cbor")
    testImplementation("org.bouncycastle:bcpkix-jdk18on:$bouncyCastleVersion")
    testImplementation("org.bouncycastle:bcprov-jdk18on:$bouncyCastleVersion")
    testImplementation("com.google.guava:guava")
}

application {
    mainClass.set("com.vmenon.mpo.api.authn.ApplicationKt")
}

tasks.withType<Test> {
    useJUnitPlatform()
}