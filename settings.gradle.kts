pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "rings-watchface"
// app: the Rings watch face; disque: the Disque watch face (Watch Face Format, no code).
// mobile + wear: the companion that feeds events and the timer to the watch face.
include(":app", ":disque", ":mobile", ":wear")
