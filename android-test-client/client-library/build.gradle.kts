plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("maven-publish")
}

// Version constants
val okhttpVersion = "4.12.0"
val gsonVersion = "2.10.1"
val gsonFireVersion = "1.9.0"
val openApiToolsVersion = "0.2.6"
val javaxWsRsVersion = "2.1.1"
val commonsLang3Version = "3.14.0"
val androidxAnnotationVersion = "1.7.1"
val jsr305Version = "3.0.2"
val javaxAnnotationVersion = "1.3.2"
val junitVersion = "4.13.2"
val androidxTestJunitVersion = "1.1.5"
val espressoVersion = "3.5.1"

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
    implementation("com.squareup.okhttp3:okhttp:$okhttpVersion")
    implementation("com.squareup.okhttp3:logging-interceptor:$okhttpVersion")

    // JSON Processing
    implementation("com.google.code.gson:gson:$gsonVersion")
    implementation("io.gsonfire:gson-fire:$gsonFireVersion")
    implementation("org.openapitools:jackson-databind-nullable:$openApiToolsVersion")

    // Web Service Support
    implementation("javax.ws.rs:javax.ws.rs-api:$javaxWsRsVersion")

    // Utilities
    implementation("org.apache.commons:commons-lang3:$commonsLang3Version")

    // Annotation Support (Android-compatible)
    implementation("androidx.annotation:annotation:$androidxAnnotationVersion")
    implementation("com.google.code.findbugs:jsr305:$jsr305Version")
    implementation("javax.annotation:javax.annotation-api:$javaxAnnotationVersion")

    // Unit Testing
    testImplementation("junit:junit:$junitVersion")

    // Instrumentation Testing
    androidTestImplementation("androidx.test.ext:junit:$androidxTestJunitVersion")
    androidTestImplementation("androidx.test.espresso:espresso-core:$espressoVersion")
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