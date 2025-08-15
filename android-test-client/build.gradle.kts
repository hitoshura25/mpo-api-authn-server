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
println("githubPackagesPassword=${if (githubPackagesPassword?.isNotBlank() == true) "***SET***" else "NOT_SET"}")

repositories {
    if (gitHubPackagesUsername?.isNotBlank() == true && githubPackagesPassword?.isNotBlank() == true) {
        // GitHub Packages for staging client library
        println("✅ Adding GitHub Packages repository with credentials")
        println("   URL: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
        println("   Username: $gitHubPackagesUsername")
        maven {
            url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
            credentials {
                username = gitHubPackagesUsername
                password = githubPackagesPassword
            }
        }
    } else {
        println("❌ GitHub Packages repository NOT added - missing credentials:")
        println("   Username: ${gitHubPackagesUsername ?: "NOT_SET"}")
        println("   Password: ${if (githubPackagesPassword?.isNotBlank() == true) "SET" else "NOT_SET"}")
    }
}
