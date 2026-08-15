plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    test {
        resources.srcDir("../../contracts")
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
