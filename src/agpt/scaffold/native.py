from __future__ import annotations

import re
from pathlib import Path


def _validate_package_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*){1,}", value):
        raise ValueError("package-id must look like com.example.game")
    return value


def _jni_mangle(value: str) -> str:
    """Mangle a Java package/class name for a JNI exported symbol."""
    return value.replace("_", "_1").replace(".", "_")


def generate_native_scaffold(destination: str | Path, package_id: str) -> Path:
    package_id = _validate_package_id(package_id)
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Destination is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    package_path = Path(*package_id.split("."))
    files = {
        "settings.gradle.kts": '''pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name = "AGPTNativeStarter"
include(":app")
''',
        "build.gradle.kts": '''plugins { id("com.android.application") version "8.7.3" apply false }
''',
        "gradle.properties": '''org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8
android.useAndroidX=true
''',
        "app/build.gradle.kts": '''plugins { id("com.android.application") }

android {
    namespace = "''' + package_id + '''"
    compileSdk = 35
    defaultConfig {
        applicationId = "''' + package_id + '''"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        ndk { abiFilters += listOf("arm64-v8a") }
        externalNativeBuild { cmake { cppFlags += "-std=c++17" } }
    }
    externalNativeBuild { cmake { path = file("src/main/cpp/CMakeLists.txt") } }
}
''',
        "app/src/main/AndroidManifest.xml": '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="AGPT Native Starter" android:hasCode="true">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
        </activity>
    </application>
</manifest>
''',
        f"app/src/main/java/{package_path}/MainActivity.java": '''package ''' + package_id + ''';

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public final class MainActivity extends Activity {
    static { System.loadLibrary("agpt_native"); }
    private native String nativeStatus();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView view = new TextView(this);
        view.setText(nativeStatus());
        view.setTextSize(18);
        view.setPadding(32, 32, 32, 32);
        setContentView(view);
    }
}
''',
        "app/src/main/cpp/CMakeLists.txt": '''cmake_minimum_required(VERSION 3.22.1)
project(agpt_native LANGUAGES C CXX)
add_library(agpt_native SHARED native-lib.cpp)
find_library(log-lib log)
target_link_libraries(agpt_native ${log-lib})
''',
        "app/src/main/cpp/native-lib.cpp": '''#include <jni.h>

extern "C" JNIEXPORT jstring JNICALL
Java_''' + _jni_mangle(package_id) + '''_MainActivity_nativeStatus(JNIEnv* env, jobject) {
    return env->NewStringUTF("AGPT native starter is running. Game engine code is not included.");
}
''',
        "README.md": '''# AGPT Native Android Starter

This is a minimal Android NDK/CMake starter, not a port of a game. It targets `arm64-v8a` and demonstrates loading a native library from an Android Activity.

Requirements: Android Studio or Gradle, JDK, Android SDK, and Android NDK/CMake. Open this directory in Android Studio and let it configure the SDK/NDK versions. Then build the `app` debug variant.

Replace the sample Activity and native library only with code and assets you have rights to use. Add an actual engine integration, input/audio/rendering, lifecycle handling, save management, and device tests before calling it a game port.
''',
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root
