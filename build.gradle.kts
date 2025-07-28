plugins {
    kotlin("jvm") version "1.9.23" apply false
    kotlin("plugin.serialization") version "1.9.23" apply false
    id("com.github.johnrengelman.shadow") version "8.1.1" apply false
    id("org.jetbrains.kotlinx.kover") version "0.9.1" apply false
    id("org.openapi.generator") version "7.2.0" apply false
}

allprojects {
    group = "com.vmenon.webauthn"
    version = "1.0.0"
    
    repositories {
        mavenCentral()
    }
}

subprojects {
    tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
        kotlinOptions {
            jvmTarget = "21"
            freeCompilerArgs += "-Xjsr305=strict"
        }
    }
}