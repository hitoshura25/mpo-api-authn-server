pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

rootProject.name = "webauthn-ecosystem"

include(
    ":webauthn-server",
    ":webauthn-test-service",
    ":android-test-client:app",
    ":android-test-client:client-library"
)