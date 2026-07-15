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
val uploadStoreFile = System.getenv("MEMCOACH_UPLOAD_STORE_FILE")
val uploadStorePassword = System.getenv("MEMCOACH_UPLOAD_STORE_PASSWORD")
val uploadKeyAlias = System.getenv("MEMCOACH_UPLOAD_KEY_ALIAS")
val uploadKeyPassword = System.getenv("MEMCOACH_UPLOAD_KEY_PASSWORD")
val uploadSigningValues = listOf(uploadStoreFile, uploadStorePassword, uploadKeyAlias, uploadKeyPassword)
val hasUploadSigning = uploadSigningValues.all { !it.isNullOrBlank() }

if (uploadSigningValues.any { !it.isNullOrBlank() } && !hasUploadSigning) {
    throw GradleException("Set all MEMCOACH_UPLOAD_* signing variables.")
}

gradle.taskGraph.whenReady {
    val buildsRelease = allTasks.any { task ->
        task.project == project && task.name.contains("release", ignoreCase = true)
    }
    if (buildsRelease && !hasUploadSigning) {
        throw GradleException("Release builds require all MEMCOACH_UPLOAD_* signing variables.")
    }
}

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

    signingConfigs {
        create("release") {
            if (hasUploadSigning) {
                storeFile = file(requireNotNull(uploadStoreFile))
                storePassword = requireNotNull(uploadStorePassword)
                keyAlias = requireNotNull(uploadKeyAlias)
                keyPassword = requireNotNull(uploadKeyPassword)
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (hasUploadSigning) signingConfigs.getByName("release") else null
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
    testImplementation("junit:junit:4.13.2")
}
