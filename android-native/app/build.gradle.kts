plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

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
    namespace = "com.memcoach.offline"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.memcoach.offline"
        minSdk = 26
        targetSdk = 36
        versionCode = 3
        versionName = "0.3.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
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
                "proguard-rules.pro",
            )
        }
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
        }
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
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
    implementation(project(":core-scheduling"))
    implementation(project(":core-grading"))

    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.navigation:navigation-compose:2.8.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("androidx.test:core:1.6.1")
    testImplementation("org.robolectric:robolectric:4.13")
    testImplementation("androidx.room:room-testing:2.6.1")
    testImplementation("androidx.arch.core:core-testing:2.2.0")
}
