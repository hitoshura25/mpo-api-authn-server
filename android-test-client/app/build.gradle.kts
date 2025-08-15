plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Version constants
val androidxCoreVersion = "1.12.0"
val androidxAppCompatVersion = "1.6.1"
val materialVersion = "1.11.0"
val constraintLayoutVersion = "2.1.4"
val lifecycleVersion = "2.7.0"
val biometricVersion = "1.1.0"
val playServicesFidoVersion = "20.1.0"
val gsonVersion = "2.10.1"
val junitVersion = "4.13.2"
val mockitoVersion = "5.8.0"
val mockitoKotlinVersion = "5.2.1"
val archCoreTestingVersion = "2.2.0"
val coroutinesTestVersion = "1.7.3"
val androidxTestJunitVersion = "1.1.5"
val espressoVersion = "3.5.1"
val androidxTestRunnerVersion = "1.5.2"
val androidxTestRulesVersion = "1.5.0"
val okhttpVersion = "4.12.0"

android {
    namespace = "com.vmenon.mpo.authn.testclient"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.vmenon.mpo.authn.testclient"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            isDebuggable = true
            buildConfigField("String", "SERVER_URL", "\"http://10.0.2.2:8080\"")
        }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "SERVER_URL", "\"https://your-production-server.com\"")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    packaging {
        jniLibs {
            pickFirsts += "**/libc++_shared.so"
            pickFirsts += "**/libjsc.so"
        }
        resources {
            // Handle duplicate META-INF files from Jakarta dependencies
            pickFirsts += "**/META-INF/NOTICE.md"
            pickFirsts += "**/META-INF/LICENSE.md"
            pickFirsts += "**/META-INF/NOTICE"
            pickFirsts += "**/META-INF/LICENSE"
            pickFirsts += "**/META-INF/NOTICE.txt"
            pickFirsts += "**/META-INF/LICENSE.txt"
            pickFirsts += "**/META-INF/ASL2.0"
            pickFirsts += "**/META-INF/LGPL2.1"
        }
    }
}

dependencies {
    // Android Core
    implementation("androidx.core:core-ktx:$androidxCoreVersion")
    implementation("androidx.appcompat:appcompat:$androidxAppCompatVersion")
    implementation("com.google.android.material:material:$materialVersion")
    implementation("androidx.constraintlayout:constraintlayout:$constraintLayoutVersion")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:$lifecycleVersion")
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:$lifecycleVersion")

    // WebAuthn/FIDO2 Support
    implementation("androidx.biometric:biometric:$biometricVersion")
    implementation("com.google.android.gms:play-services-fido:$playServicesFidoVersion")

    // Published Android client library from GitHub Packages
    implementation("io.github.hitoshura25:mpo-webauthn-android-client:latest.release")
    
    // JSON Processing
    implementation("com.google.code.gson:gson:$gsonVersion")

    // Unit Testing
    testImplementation("junit:junit:$junitVersion")
    testImplementation("org.mockito:mockito-core:$mockitoVersion")
    testImplementation("org.mockito.kotlin:mockito-kotlin:$mockitoKotlinVersion")
    testImplementation("androidx.arch.core:core-testing:$archCoreTestingVersion") // For InstantTaskExecutorRule
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:$coroutinesTestVersion") // For StandardTestDispatcher

    // Instrumentation Testing
    androidTestImplementation("androidx.test.ext:junit:$androidxTestJunitVersion")
    androidTestImplementation("androidx.test.espresso:espresso-core:$espressoVersion")
    androidTestImplementation("androidx.test:runner:$androidxTestRunnerVersion")
    androidTestImplementation("androidx.test:rules:$androidxTestRulesVersion")
    androidTestImplementation("com.squareup.okhttp3:okhttp:$okhttpVersion") // HTTP client for test service communication
}