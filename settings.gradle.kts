pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

rootProject.name = "mpo-api-authn-server"

include(
    ":webauthn-server",
    ":webauthn-test-credentials-service",
    ":webauthn-test-lib",
    ":android-client-library"
)
