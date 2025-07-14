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
val bouncyCastleVersion = "1.81"
val testContainersVersion = "1.21.3"
val testContainersRedisVersion = "2.2.2"


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

    // Redis for scalable storage
    implementation("redis.clients:jedis:5.1.0")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-smile:${jacksonVersion}")

    // PostgreSQL for credential storage
    implementation("org.postgresql:postgresql:42.7.2")
    implementation("com.zaxxer:HikariCP:5.0.1")

    // Dependency Injection
    implementation("io.insert-koin:koin-ktor:3.5.3")
    implementation("io.insert-koin:koin-logger-slf4j:3.5.3")
    implementation("io.insert-koin:koin-core:3.5.3")

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter-api:$junitVersion")
    testImplementation("io.insert-koin:koin-test:3.5.3")
    testImplementation("io.insert-koin:koin-test-junit5:3.5.3")

    // Testcontainers for end-to-end testing with real databases
    testImplementation("org.testcontainers:junit-jupiter:$testContainersVersion")
    testImplementation("org.testcontainers:postgresql:$testContainersVersion")
    testImplementation("org.testcontainers:testcontainers:$testContainersVersion")
    testImplementation("com.redis:testcontainers-redis:${testContainersRedisVersion}")

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