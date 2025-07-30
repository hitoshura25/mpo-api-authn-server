plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("maven-publish")
}

android {
    namespace = "com.vmenon.mpo.api.authn.client"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
        targetSdk = 34

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }

    packaging {
        jniLibs {
            pickFirsts += "**/libc++_shared.so"
            pickFirsts += "**/libjsc.so"
        }
    }
}

dependencies {
    // HTTP Client Dependencies
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // JSON Processing
    implementation("com.google.code.gson:gson:2.10.1")
    implementation("io.gsonfire:gson-fire:1.9.0")
    implementation("org.openapitools:jackson-databind-nullable:0.2.6")

    // Web Service Support
    implementation("javax.ws.rs:javax.ws.rs-api:2.1.1")

    // Utilities
    implementation("org.apache.commons:commons-lang3:3.14.0")

    // Annotation Support (Android-compatible)
    implementation("androidx.annotation:annotation:1.7.1")
    implementation("com.google.code.findbugs:jsr305:3.0.2")
    implementation("javax.annotation:javax.annotation-api:1.3.2")

    // Unit Testing
    testImplementation("junit:junit:4.13.2")

    // Instrumentation Testing
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}

// Configure version from parent project or environment
val clientVersion = if (project.hasProperty("clientVersion")) {
    project.property("clientVersion") as String
} else {
    System.getenv("CLIENT_VERSION") ?: "1.0.0-SNAPSHOT"
}

version = clientVersion

publishing {
    publications {
        create<MavenPublication>("maven") {
            groupId = "com.vmenon.mpo.api.authn"
            artifactId = "mpo-webauthn-android-client"
            version = clientVersion

            afterEvaluate {
                from(components["release"])
            }

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
                username = project.findProperty("gpr.user") as String? ?: System.getenv("USERNAME")
                password = project.findProperty("gpr.key") as String? ?: System.getenv("TOKEN")
            }
        }
    }
}