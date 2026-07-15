plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val memcoachStartUrl =
    (project.findProperty("memcoachStartUrl") as String?)
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
        ?: "http://127.0.0.1:8000"
val memcoachStartUrlEscaped = memcoachStartUrl.replace("\\", "\\\\").replace("\"", "\\\"")

android {
    namespace = "com.memcoach.wrapper"
    compileSdk = 36

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.memcoach.wrapper"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "MEMCOACH_START_URL", "\"${memcoachStartUrlEscaped}\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
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
    implementation("androidx.appcompat:appcompat:1.7.0")
}
