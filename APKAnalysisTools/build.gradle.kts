import com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    application
    kotlin("jvm") version "1.9.0"
    kotlin("plugin.serialization") version "1.9.0"
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

group = "tool.xfy9326.apk.analysis"
version = "1.0"

repositories {
    mavenCentral()
    google()
    maven {
        url = uri("https://jitpack.io")
    }
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.7.2")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.5.1")
    implementation("org.apache.commons:commons-text:1.10.0")
    implementation("com.google.guava:guava:32.1.2-jre")
    implementation("com.github.ajalt.clikt:clikt-jvm:4.2.0")
    implementation("com.android.tools.smali:smali-dexlib2:3.0.3")
    implementation("io.github.reandroid:ARSCLib:1.2.3")
    testImplementation(kotlin("test"))
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
    sourceCompatibility = JavaVersion.VERSION_11
    targetCompatibility = JavaVersion.VERSION_11
}

kotlin {
    jvmToolchain(17)
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_11)
        freeCompilerArgs.addAll(
            "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi", "-opt-in=kotlinx.serialization.ExperimentalSerializationApi"
        )
    }
}

application {
    mainClass.set("tool.xfy9326.apk.analysis.AppKt")
}

tasks.test {
    useJUnitPlatform()
}

tasks.jar { enabled = false }

artifacts.archives(tasks.shadowJar)

tasks.withType<ShadowJar> {
    // The jar remains up to date even when changing excludes
    // https://github.com/johnrengelman/shadow/issues/62
    outputs.upToDateWhen { false }

    exclude(
        "LICENSE",
        "arsclib.properties",
        "DebugProbesKt.bin",
        "META-INF/com.android.tools/**",
        "META-INF/maven/**",
        "META-INF/proguard/**",
        "META-INF/*.version",
        "META-INF/LICENSE",
        "META-INF/LICENSE.txt",
        "META-INF/LGPL2.1",
        "META-INF/AL2.0",
    )

    mergeServiceFiles()
}

tasks.register("releaseJar") {
    group = "release"
    dependsOn("clean")
    dependsOn(tasks.withType<ShadowJar>().map { it.name })
}
