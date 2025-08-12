plugins {
    id("java-library")
    id("maven-publish")
}

java {
    sourceCompatibility = JavaVersion.VERSION_1_8
    targetCompatibility = JavaVersion.VERSION_1_8
}

// Configure version from parent project or environment
val clientVersion = if (project.hasProperty("clientVersion")) {
    project.property("clientVersion") as String
} else {
    System.getenv("CLIENT_VERSION") ?: "1.0.0-SNAPSHOT"
}

// Configure artifact ID from parent project or environment
val androidArtifactId = if (project.hasProperty("androidArtifactId")) {
    project.property("androidArtifactId") as String
} else {
    System.getenv("ANDROID_ARTIFACT_ID") ?: "mpo-webauthn-android-client"
}

// Configure group ID from parent project or environment
val androidGroupId = if (project.hasProperty("androidGroupId")) {
    project.property("androidGroupId") as String
} else {
    System.getenv("ANDROID_GROUP_ID") ?: "io.github.hitoshura25"
}

version = clientVersion

publishing {
    publications {
        create<MavenPublication>("maven") {
            groupId = androidGroupId
            artifactId = androidArtifactId
            version = clientVersion

            from(components["java"])

            pom {
                name.set("MPO WebAuthn Android Client")
                description.set("Generated Android client for MPO WebAuthn API")
                url.set("https://github.com/hitoshura25/mpo-api-authn-server")

                licenses {
                    license {
                        name.set("MIT License")
                        url.set("https://opensource.org/licenses/MIT")
                    }
                }

                developers {
                    developer {
                        id.set("webauthn-server")
                        name.set("WebAuthn Server Team")
                        email.set("support@example.com")
                    }
                }

                scm {
                    connection.set("scm:git:git://github.com/hitoshura25/mpo-api-authn-server.git")
                    developerConnection.set("scm:git:ssh://github.com:hitoshura25/mpo-api-authn-server.git")
                    url.set("https://github.com/hitoshura25/mpo-api-authn-server/tree/main")
                }
            }
        }
    }

    repositories {
        maven {
            name = "GitHubPackages"
            url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
            credentials {
                username = System.getenv("ANDROID_PUBLISH_USER")
                password = System.getenv("ANDROID_PUBLISH_TOKEN")
            }
        }
    }
}