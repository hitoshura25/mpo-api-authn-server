plugins {
    kotlin("jvm") version "1.9.23" apply false
    kotlin("plugin.serialization") version "1.9.23" apply false
    id("com.github.johnrengelman.shadow") version "8.1.1" apply false
    id("org.jetbrains.kotlinx.kover") version "0.9.1" apply false
    id("org.openapi.generator") version "7.2.0" apply false
    id("io.gitlab.arturbosch.detekt") version "1.23.7" apply false
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1" apply false
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
    
    // Apply ktlint configuration to all subprojects
    apply(plugin = "org.jlleitschuh.gradle.ktlint")
    
    configure<org.jlleitschuh.gradle.ktlint.KtlintExtension> {
        verbose.set(true)
        android.set(false)
        coloredOutput.set(true)
        outputToConsole.set(true)
        outputColorName.set("RED")
        ignoreFailures.set(false)
        enableExperimentalRules.set(false)
    }
}