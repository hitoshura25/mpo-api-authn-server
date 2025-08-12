import org.gradle.api.initialization.resolve.RepositoriesMode

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        mavenLocal() // For locally published generated clients
    }
}

rootProject.name = "WebAuthn Test Client"
include ':app'
// Removed ':client-library' - now using published packages from GitHub Packages
