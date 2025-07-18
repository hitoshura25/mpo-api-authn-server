plugins {
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("application")
    id("com.github.johnrengelman.shadow") version "8.1.1"
    id("org.jetbrains.kotlinx.kover") version "0.9.1"
}

val kotlinVersion = "1.9.23"
val ktorVersion = "2.3.7"
val junitVersion = "5.11.3"
val webauthnVersion = "2.6.0"
val jacksonVersion = "2.16.1"
val logbackVersion = "1.4.14"
val mockkVersion = "1.13.8"
val bouncyCastleVersion = "1.78"
val testContainersVersion = "1.21.3"
val testContainersRedisVersion = "2.2.2"
val jedisVersion = "5.1.0"
val postgresqlVersion = "42.7.2"
val hikariCpVersion = "5.0.1"
val koinVersion = "3.5.3"
val micrometerVersion = "1.12.2"
val openTelemetryVersion = "1.32.0"
val openTelemetryKtorVersion = "2.17.1-alpha"

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
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jdk8:$jacksonVersion")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-cbor:$jacksonVersion")

    implementation("ch.qos.logback:logback-classic:$logbackVersion")

    // Redis for scalable storage
    implementation("redis.clients:jedis:$jedisVersion")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-smile:$jacksonVersion")

    // PostgreSQL for credential storage
    implementation("org.postgresql:postgresql:$postgresqlVersion")
    implementation("com.zaxxer:HikariCP:$hikariCpVersion")

    // Post-Quantum Cryptography
    implementation("org.bouncycastle:bcprov-jdk18on:$bouncyCastleVersion")
    implementation("org.bouncycastle:bcpkix-jdk18on:$bouncyCastleVersion")

    // Dependency Injection
    implementation("io.insert-koin:koin-ktor:$koinVersion")
    implementation("io.insert-koin:koin-logger-slf4j:$koinVersion")
    implementation("io.insert-koin:koin-core:$koinVersion")

    // Monitoring dependencies
    implementation("io.ktor:ktor-server-metrics-micrometer:$ktorVersion")
    implementation("io.ktor:ktor-server-call-logging:$ktorVersion")
    implementation("io.micrometer:micrometer-registry-prometheus:$micrometerVersion")

    // OpenTelemetry for tracing
    implementation("io.opentelemetry:opentelemetry-api:$openTelemetryVersion")
    implementation("io.opentelemetry:opentelemetry-sdk:$openTelemetryVersion")
    implementation("io.opentelemetry:opentelemetry-extension-trace-propagators:$openTelemetryVersion")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp:$openTelemetryVersion")
    implementation("io.opentelemetry.instrumentation:opentelemetry-ktor-2.0:$openTelemetryKtorVersion")
    implementation("io.opentelemetry.instrumentation:opentelemetry-instrumentation-annotations:$openTelemetryVersion")
    runtimeOnly("io.opentelemetry.semconv:opentelemetry-semconv:$openTelemetryVersion")

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter-api:$junitVersion")
    testImplementation("io.insert-koin:koin-test:$koinVersion")
    testImplementation("io.insert-koin:koin-test-junit5:$koinVersion")

    // Testcontainers for end-to-end testing with real databases
    testImplementation("org.testcontainers:junit-jupiter:$testContainersVersion")
    testImplementation("org.testcontainers:postgresql:$testContainersVersion")
    testImplementation("org.testcontainers:testcontainers:$testContainersVersion")
    testImplementation("com.redis:testcontainers-redis:$testContainersRedisVersion")

    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:$junitVersion")
    testImplementation("io.ktor:ktor-server-test-host:$ktorVersion")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:$kotlinVersion")
    testImplementation("io.mockk:mockk:$mockkVersion")
    testImplementation("com.upokecenter:cbor")
    testImplementation("com.google.guava:guava")
}

application {
    mainClass.set("com.vmenon.mpo.api.authn.ApplicationKt")
}

tasks.shadowJar {
    archiveClassifier.set("all")
    manifest {
        attributes["Main-Class"] = "com.vmenon.mpo.api.authn.ApplicationKt"
    }
}

tasks.build {
    dependsOn(tasks.shadowJar)
}

tasks.withType<Test> {
    useJUnitPlatform()
}