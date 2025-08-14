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

val gitHubPackagesUsername = System.getenv("GITHUB_PACKAGES_USERNAME")
    ?: project.findProperty("GitHubPackagesUsername") as String?

val githubPackagesPassword = System.getenv("GITHUB_PACKAGES_PASSWORD")
    ?: project.findProperty("GitHubPackagesPassword") as String?

println("githubPackagesUsername=$gitHubPackagesUsername")

repositories {
    if (githubPackagesPassword?.isNotBlank() == true && githubPackagesPassword?.isNotBlank() == true) {
        // GitHub Packages for staging client library
        maven {
            url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
            credentials {
                username = gitHubPackagesUsername
                password = githubPackagesPassword
            }
        }
    }
}
