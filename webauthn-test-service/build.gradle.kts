plugins {
    kotlin("jvm") version "1.9.23"
    kotlin("plugin.serialization") version "1.9.23"
    application
    id("com.github.johnrengelman.shadow") version "8.1.1"
    id("org.jetbrains.kotlinx.kover") version "0.9.1"
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

group = "com.vmenon.webauthn"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    // Shared WebAuthn test library
    implementation(project(":webauthn-test-lib"))

    // Ktor Server
    implementation("io.ktor:ktor-server-core-jvm:2.3.8")
    implementation("io.ktor:ktor-server-netty-jvm:2.3.8")
    implementation("io.ktor:ktor-server-content-negotiation-jvm:2.3.8")
    implementation("io.ktor:ktor-serialization-jackson-jvm:2.3.8")
    implementation("io.ktor:ktor-server-cors-jvm:2.3.8")
    implementation("io.ktor:ktor-server-status-pages-jvm:2.3.8")

    // Logging
    implementation("ch.qos.logback:logback-classic:1.4.14")

    // Testing
    testImplementation("io.ktor:ktor-server-tests-jvm:2.3.8")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.23")
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:5.10.0")
    testImplementation("io.ktor:ktor-client-content-negotiation:2.3.8")
}

application {
    mainClass.set("com.vmenon.webauthn.testservice.ApplicationKt")
}

kotlin {
    jvmToolchain(21)
}

tasks.withType<Test> {
    useJUnitPlatform()
}

// Shadow JAR configuration for easy deployment
tasks.shadowJar {
    archiveBaseName.set("webauthn-test-service")
    archiveClassifier.set("")
    archiveVersion.set("")
}
