// Top-level build file for Android WebAuthn Test Client
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("com.android.library") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.23" apply false
}

buildscript {
    dependencies {
        classpath("com.android.tools.build:gradle:8.2.2")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.23")
    }
}

// NOTE: Repository configuration moved to settings.gradle.kts 
// when using dependencyResolutionManagement

// Enable selective dependency locking for Android project and all subprojects
// Provides supply chain security while allowing staging client library flexibility
allprojects {
    dependencyLocking {
        // Lock all configurations except those that might need staging client library versions
        // This allows CI workflows to dynamically replace client library versions for E2E testing
        // while maintaining security for all other dependencies
        ignoredDependencies.add("io.github.hitoshura25:mpo-webauthn-android-client")
        ignoredDependencies.add("io.github.hitoshura25:mpo-webauthn-android-client-staging")
        lockAllConfigurations()
    }
}
