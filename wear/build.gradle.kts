plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "io.github.satoshimiyasaka.rings"
    compileSdk = 35

    defaultConfig {
        // Must match the mobile module so the two can talk over the Data Layer.
        applicationId = "io.github.satoshimiyasaka.rings"
        // GOAL_PROGRESS complications need Wear OS 4 (API 33).
        minSdk = 33
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    signingConfigs {
        getByName("debug") {
            storeFile = file("../app/debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.wear.watchface:watchface-complications-data-source-ktx:1.2.1")
    implementation("com.google.android.gms:play-services-wearable:18.2.0")
    testImplementation("junit:junit:4.13.2")
}
