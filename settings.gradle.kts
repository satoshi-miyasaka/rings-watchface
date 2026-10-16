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
// app: the watch face itself (Watch Face Format, no code).
// mobile + wear: the companion that feeds events and the timer to the watch face.
include(":app", ":mobile", ":wear")
