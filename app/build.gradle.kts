plugins {
    id("com.android.application")
}

android {
    namespace = "io.github.satoshimiyasaka.ringswatchface"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.satoshimiyasaka.ringswatchface"
        // Watch Face Format v2 (weather data) requires Wear OS 5 = API 34.
        minSdk = 34
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}
