pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        mavenLocal() // For locally published generated clients
        
        // GitHub Packages for staging client library (conditional on credentials)
        val gitHubPackagesUsername = System.getenv("GITHUB_PACKAGES_USERNAME")
            ?: providers.gradleProperty("GitHubPackagesUsername").orNull
        val githubPackagesPassword = System.getenv("GITHUB_PACKAGES_PASSWORD") 
            ?: providers.gradleProperty("GitHubPackagesPassword").orNull
            
        if (!gitHubPackagesUsername.isNullOrBlank() && !githubPackagesPassword.isNullOrBlank()) {
            println("✅ Adding GitHub Packages repository to dependency resolution")
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
            println("❌ GitHub Packages repository NOT added to dependency resolution - missing credentials:")
            println("   Username: ${gitHubPackagesUsername ?: "NOT_SET"}")
            println("   Password: ${if (!githubPackagesPassword.isNullOrBlank()) "SET" else "NOT_SET"}")
        }
    }
}

rootProject.name = "WebAuthn Test Client"
include(":app")
// Removed ':client-library' - now using published packages from GitHub Packages
