plugins {
    kotlin("jvm") version "1.9.23" apply false
    kotlin("plugin.serialization") version "1.9.23" apply false
    id("com.github.johnrengelman.shadow") version "8.1.1" apply false
    id("org.jetbrains.kotlinx.kover") version "0.9.1" apply false
    id("org.openapi.generator") version "7.2.0" apply false
    id("com.android.application") version "8.2.2" apply false
    id("com.android.library") version "8.2.2" apply false
    kotlin("android") version "1.9.23" apply false
}

allprojects {
    group = "com.vmenon.webauthn"
    version = "1.0.0"
    
    repositories {
        mavenCentral()
        google()
    }
}

subprojects {
    // Only apply JVM target to server projects, not Android
    if (project.name == "webauthn-server" || project.name == "webauthn-test-service") {
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
            kotlinOptions {
                jvmTarget = "21"
                freeCompilerArgs += "-Xjsr305=strict"
            }
        }
    }
}