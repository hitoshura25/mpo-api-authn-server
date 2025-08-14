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
    }
}

rootProject.name = "WebAuthn Test Client"
include(":app")
// Removed ':client-library' - now using published packages from GitHub Packages
