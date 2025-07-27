plugins {
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("application")
    id("com.github.johnrengelman.shadow") version "8.1.1"
    id("org.jetbrains.kotlinx.kover") version "0.9.1"
    id("org.openapi.generator") version "7.2.0"
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

    // OpenAPI/Swagger support
    implementation("io.ktor:ktor-server-openapi:$ktorVersion")
    implementation("io.ktor:ktor-server-swagger:$ktorVersion")
    implementation("io.swagger.core.v3:swagger-core:2.2.19")

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

// OpenAPI specification file location - use the static file instead of fetching from server
val openApiSpecFile = layout.buildDirectory.file("openapi/openapi.yaml")
val staticOpenApiSpecFile = file("src/main/resources/openapi/documentation.yaml")

// Task to copy static OpenAPI spec to build directory
tasks.register<Copy>("copyOpenApiSpec") {
    group = "openapi"
    description = "Copy static OpenAPI specification to build directory"

    from(staticOpenApiSpecFile)
    into(layout.buildDirectory.dir("openapi"))
    rename { "openapi.yaml" }

    inputs.file(staticOpenApiSpecFile)
    outputs.file(openApiSpecFile)
}

// TypeScript/JavaScript client generation
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateTsClient") {
    group = "openapi"
    description = "Generate TypeScript client library"

    dependsOn("copyOpenApiSpec")

    generatorName.set("typescript-axios")
    inputSpec.set(staticOpenApiSpecFile.absolutePath)
    outputDir.set(layout.buildDirectory.dir("generated-clients/typescript").get().asFile.absolutePath)

    configOptions.set(
        mapOf(
            "supportsES6" to "true",
            "npmName" to "mpo-webauthn-client",
            "npmVersion" to project.version.toString(),
            "modelPropertyNaming" to "camelCase"
        )
    )

    inputs.file(staticOpenApiSpecFile)
    outputs.dir(layout.buildDirectory.dir("generated-clients/typescript"))
}

// Java client generation
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateJavaClient") {
    group = "openapi"
    description = "Generate Java client library"

    dependsOn("copyOpenApiSpec")

    generatorName.set("java")
    inputSpec.set(staticOpenApiSpecFile.absolutePath)
    outputDir.set(layout.buildDirectory.dir("generated-clients/java").get().asFile.absolutePath)

    configOptions.set(
        mapOf(
            "library" to "okhttp-gson",
            "groupId" to "com.vmenon.mpo.api.authn",
            "artifactId" to "mpo-webauthn-client",
            "artifactVersion" to project.version.toString(),
            "invokerPackage" to "com.vmenon.mpo.api.authn.client",
            "apiPackage" to "com.vmenon.mpo.api.authn.client.api",
            "modelPackage" to "com.vmenon.mpo.api.authn.client.model"
        )
    )

    inputs.file(staticOpenApiSpecFile)
    outputs.dir(layout.buildDirectory.dir("generated-clients/java"))
}

// Python client generation
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generatePythonClient") {
    group = "openapi"
    description = "Generate Python client library"

    dependsOn("copyOpenApiSpec")

    generatorName.set("python")
    inputSpec.set(staticOpenApiSpecFile.absolutePath)
    outputDir.set(layout.buildDirectory.dir("generated-clients/python").get().asFile.absolutePath)

    configOptions.set(
        mapOf(
            "packageName" to "mpo_webauthn_client",
            "packageVersion" to project.version.toString(),
            "projectName" to "mpo-webauthn-client"
        )
    )

    inputs.file(staticOpenApiSpecFile)
    outputs.dir(layout.buildDirectory.dir("generated-clients/python"))
}

// C# client generation
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateCsharpClient") {
    group = "openapi"
    description = "Generate C# client library"

    dependsOn("copyOpenApiSpec")

    generatorName.set("csharp")
    inputSpec.set(staticOpenApiSpecFile.absolutePath)
    outputDir.set(layout.buildDirectory.dir("generated-clients/csharp").get().asFile.absolutePath)

    configOptions.set(
        mapOf(
            "packageName" to "MpoWebAuthnClient",
            "packageVersion" to project.version.toString(),
            "clientPackage" to "MpoWebAuthnClient"
        )
    )

    inputs.file(staticOpenApiSpecFile)
    outputs.dir(layout.buildDirectory.dir("generated-clients/csharp"))
}

// Android client generation (specifically configured for Android)
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateAndroidClient") {
    group = "openapi"
    description = "Generate Android client library"

    dependsOn("copyOpenApiSpec")

    generatorName.set("java")
    inputSpec.set(staticOpenApiSpecFile.absolutePath)
    outputDir.set(layout.buildDirectory.dir("generated-clients/android").get().asFile.absolutePath)

    configOptions.set(
        mapOf(
            "library" to "okhttp-gson",
            "groupId" to "com.vmenon.mpo.api.authn",
            "artifactId" to "mpo-webauthn-android-client",
            "artifactVersion" to project.version.toString(),
            "invokerPackage" to "com.vmenon.mpo.api.authn.client",
            "apiPackage" to "com.vmenon.mpo.api.authn.client.api",
            "modelPackage" to "com.vmenon.mpo.api.authn.client.model",
            "android" to "true",
            "dateLibrary" to "java8",
            "withXml" to "false",
            "hideGenerationTimestamp" to "true",
            "useJakartaEe" to "false",
            "annotationLibrary" to "none"
        )
    )

    inputs.file(staticOpenApiSpecFile)
    outputs.dir(layout.buildDirectory.dir("generated-clients/android"))
}

// Copy generated client code to library module
tasks.register<Copy>("copyGeneratedClientToLibrary") {
    group = "openapi"
    description = "Copy generated Android client code to library module"

    dependsOn("generateAndroidClient")

    from(layout.buildDirectory.dir("generated-clients/android/src/main/java"))
    into(file("android-test-client/client-library/src/main/java"))

    inputs.dir(layout.buildDirectory.dir("generated-clients/android/src/main/java"))
    outputs.dir(file("android-test-client/client-library/src/main/java"))
}

// Build generated clients
tasks.register("buildGeneratedClients") {
    group = "openapi"
    description = "Build all generated client libraries"

    dependsOn("generateAllClients")

    doLast {
        // Build Java client
        val javaClientDir = layout.buildDirectory.dir("generated-clients/java").get().asFile
        if (javaClientDir.exists()) {
            exec {
                workingDir = javaClientDir
                commandLine("./gradlew", "build", "publishToMavenLocal")
            }
        }

        // Build Android client  
        val androidClientDir = layout.buildDirectory.dir("generated-clients/android").get().asFile
        if (androidClientDir.exists()) {
            exec {
                workingDir = androidClientDir
                commandLine("./gradlew", "build", "publishToMavenLocal")
            }
        }

        // Build TypeScript client
        val tsClientDir = layout.buildDirectory.dir("generated-clients/typescript").get().asFile
        if (tsClientDir.exists() && File(tsClientDir, "package.json").exists()) {
            exec {
                workingDir = tsClientDir
                commandLine("npm", "install")
            }
            exec {
                workingDir = tsClientDir
                commandLine("npm", "run", "build")
            }
        }
    }
}

// Prepare clients for publishing
tasks.register("prepareClientPublishing") {
    group = "openapi"
    description = "Prepare all generated clients for publishing to repositories"

    dependsOn("buildGeneratedClients")

    doLast {
        val distributionDir = layout.buildDirectory.dir("client-distributions").get().asFile
        distributionDir.mkdirs()

        println("📦 Client libraries prepared for publishing:")

        // Java/Android clients (Maven)
        listOf("java", "android").forEach { clientType ->
            val clientDir = layout.buildDirectory.dir("generated-clients/$clientType").get().asFile
            if (clientDir.exists()) {
                val jarFiles = clientDir.walkTopDown()
                    .filter { it.extension == "jar" && !it.name.contains("sources") }
                    .toList()

                jarFiles.forEach { jar ->
                    val destFile = File(distributionDir, "${clientType}-${jar.name}")
                    jar.copyTo(destFile, overwrite = true)
                    println("   📋 ${clientType.uppercase()}: ${destFile.absolutePath}")
                }
            }
        }

        // TypeScript client (NPM)
        val tsClientDir = layout.buildDirectory.dir("generated-clients/typescript").get().asFile
        if (tsClientDir.exists()) {
            val tgzFiles = tsClientDir.walkTopDown()
                .filter { it.extension == "tgz" }
                .toList()

            tgzFiles.forEach { tgz ->
                val destFile = File(distributionDir, "typescript-${tgz.name}")
                tgz.copyTo(destFile, overwrite = true)
                println("   📋 TYPESCRIPT: ${destFile.absolutePath}")
            }
        }

        // Python client (PyPI)
        val pythonClientDir = layout.buildDirectory.dir("generated-clients/python").get().asFile
        if (pythonClientDir.exists()) {
            val distDir = File(pythonClientDir, "dist")
            if (distDir.exists()) {
                distDir.listFiles()?.forEach { distFile ->
                    val destFile = File(distributionDir, "python-${distFile.name}")
                    distFile.copyTo(destFile, overwrite = true)
                    println("   📋 PYTHON: ${destFile.absolutePath}")
                }
            }
        }

        println("\n🚀 Publishing commands:")
        println("   Maven:     mvn deploy (from generated-clients/java or generated-clients/android)")
        println("   NPM:       npm publish (from generated-clients/typescript)")
        println("   PyPI:      twine upload dist/* (from generated-clients/python)")
        println("   NuGet:     dotnet nuget push (from generated-clients/csharp)")
    }
}

// Generate all clients
tasks.register("generateAllClients") {
    group = "openapi"
    description = "Generate all client libraries"

    dependsOn(
        "generateTsClient",
        "generateJavaClient",
        "generatePythonClient",
        "generateCsharpClient",
        "generateAndroidClient"
    )
}
