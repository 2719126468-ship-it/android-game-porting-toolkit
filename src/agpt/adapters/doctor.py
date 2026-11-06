"""Optional toolchain discovery for AGPT."""
from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus:
    name: str
    available: bool
    path: str | None
    purpose: str
    required_for: str


def _first(candidates):
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def inspect_toolchain():
    checks = [
        ("python", ["python3", "python"], "AGPT runtime", "core"),
        ("java", ["java"], "JVM for Ghidra/Gradle", "reverse/build"),
        ("ninja", ["ninja"], "Native build generator", "native"),
        ("clang", ["clang"], "Native compiler", "native"),
        ("adb", ["adb"], "Android device QA", "device QA"),
        ("gradle", ["gradle"], "Android project orchestration", "APK packaging"),
        ("wine", ["wine", "wine64"], "Windows compatibility runtime", "compatibility"),
        ("box64", ["box64"], "x86-64 translation on supported ARM64 systems", "compatibility"),
    ]
    results = []
    for name, candidates, purpose, required_for in checks:
        path = _first(candidates)
        results.append(ToolStatus(name, path is not None, path, purpose, required_for))

    cmake = shutil.which("cmake")
    results.append(ToolStatus("cmake", cmake is not None, cmake, "Native build generation", "native"))
    for env in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        if os.environ.get(env):
            results.append(ToolStatus("android-sdk", True, os.environ[env], "Android SDK", "native/package"))
            break
    else:
        results.append(ToolStatus("android-sdk", False, None, "Android SDK", "native/package"))

    from agpt.adapters.ghidra import discover_ghidra, AdapterError
    try:
        path = str(discover_ghidra())
        results.append(ToolStatus("ghidra-headless", True, path, "Ghidra Headless analysis", "reverse"))
    except AdapterError:
        results.append(ToolStatus("ghidra-headless", False, None, "Ghidra Headless analysis", "reverse"))

    from agpt.adapters.ndk import discover_ndk, NdkBuildError
    try:
        path = str(discover_ndk())
        results.append(ToolStatus("android-ndk", True, path, "Android native compiler/toolchain", "native"))
    except NdkBuildError:
        results.append(ToolStatus("android-ndk", False, None, "Android native compiler/toolchain", "native"))

    return results


def doctor_dict():
    statuses = inspect_toolchain()
    return {
        "schema_version": "1.0",
        "core_ready": any(item.name == "python" and item.available for item in statuses),
        "tools": [asdict(item) for item in statuses],
        "note": "Missing optional tools do not prevent project creation or static inspection.",
    }
