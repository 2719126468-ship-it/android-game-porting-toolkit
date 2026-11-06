from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ToolStatus:
    name: str
    available: bool
    path: str | None
    purpose: str
    required_for: str


def inspect_toolchain() -> list[ToolStatus]:
    tools = [
        ("python", ["python3", "python"], "AGPT runtime", "core"),
        ("java", ["java"], "JVM required by common Ghidra/Gradle workflows", "reverse/build"),
        ("ghidra-analyzeHeadless", ["analyzeHeadless", "ghidra-analyzeHeadless"], "Headless binary analysis", "reverse"),
        ("cmake", ["cmake"], "Native build generation", "native"),
        ("ninja", ["ninja"], "Fast native builds", "native"),
        ("clang", ["clang"], "Native compiler", "native"),
        ("ndk-build", ["ndk-build"], "Android NDK", "native"),
        ("adb", ["adb"], "Android device installation/testing", "device QA"),
        ("gradle", ["gradle"], "Android project orchestration", "APK packaging"),
        ("wine", ["wine", "wine64"], "Windows compatibility runtime", "compatibility"),
        ("box64", ["box64"], "x86-64 userspace translation on supported ARM64 systems", "compatibility"),
        ("fex", ["FEXInterpreter", "fex"], "x86/x86-64 translation on supported hosts", "compatibility"),
    ]
    results = []
    for name, candidates, purpose, required_for in tools:
        found = next((shutil.which(candidate) for candidate in candidates if shutil.which(candidate)), None)
        results.append(ToolStatus(name, found is not None, found, purpose, required_for))
    sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    ndk = os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_ROOT")
    results.append(ToolStatus("android-sdk-env", bool(sdk), sdk, "Android SDK environment variable", "APK packaging"))
    results.append(ToolStatus("android-ndk-env", bool(ndk), ndk, "Android NDK environment variable", "native"))
    return results


def doctor_dict() -> dict:
    statuses = inspect_toolchain()
    return {
        "schema_version": "1.0",
        "core_ready": next(item.available for item in statuses if item.name == "python"),
        "tools": [asdict(item) for item in statuses],
        "note": "Missing optional tools do not prevent project creation or static inspection.",
    }
