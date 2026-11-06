"""Bounded source/build metadata probes. Does not execute project source or build scripts."""
from __future__ import annotations

import re
from pathlib import Path

from agpt.models import Evidence

MAX_BUILD_BYTES = 256 * 1024
MAX_SOURCE_FILE_BYTES = 64 * 1024
MAX_SOURCE_FILES = 512
MAX_SOURCE_BYTES = 4 * 1024 * 1024

_PACKAGES = {
    "sdl2": "sdl2", "sdl2_image": "sdl2_image", "sdl2-image": "sdl2_image",
    "sdl2_mixer": "sdl2_mixer", "sdl2-mixer": "sdl2_mixer",
    "sdl2_net": "sdl2_net", "sdl2-net": "sdl2_net",
    "sdl2_ttf": "sdl2_ttf", "sdl2-ttf": "sdl2_ttf",
}
_HEADERS = {
    "sdl.h": "sdl2", "sdl_image.h": "sdl2_image",
    "sdl_mixer.h": "sdl2_mixer", "sdl_net.h": "sdl2_net",
    "sdl_ttf.h": "sdl2_ttf",
}


def _read(path: Path, limit: int) -> str | None:
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError:
        return None
    return raw[:limit].decode("utf-8", errors="replace")


def _emit(out, category, value, source, detail, weight=2):
    out.append(Evidence(category, value, source, detail, weight))


def _package(value: str) -> str | None:
    return _PACKAGES.get(value.strip().strip("\"'").lower().replace("::", "_"))


def analyze_source_build(root, records) -> list[Evidence]:
    """Inspect known build manifests and bounded C/C++ include metadata."""
    base = Path(root)
    out: list[Evidence] = []
    build_names = {
        "cmakelists.txt", "android.mk", "application.mk", "makefile",
        "meson.build", "build.gradle", "build.gradle.kts",
    }
    build_paths = [r.path for r in records if Path(r.path).name.lower() in build_names]
    cmake = [p for p in build_paths if Path(p).name.lower() == "cmakelists.txt"]
    android_mk = [p for p in build_paths if Path(p).name.lower() == "android.mk"]
    application_mk = [p for p in build_paths if Path(p).name.lower() == "application.mk"]
    gradle = [p for p in build_paths if Path(p).name.lower() in {"build.gradle", "build.gradle.kts"}]
    dependencies: dict[str, tuple[str, str]] = {}

    for rel in cmake:
        text = _read(base / rel, MAX_BUILD_BYTES)
        if text is None:
            continue
        _emit(out, "build_system", "cmake", rel, "CMakeLists.txt build configuration found", 4)
        for match in re.finditer(r"(?im)^\s*find_package\s*\(\s*([A-Za-z0-9_.+-]+)", text):
            package = _package(match.group(1))
            if package:
                dependencies[package] = (rel, f"find_package({match.group(1)})")
        for match in re.finditer(r"(?im)^\s*add_(?:executable|library)\s*\(\s*([\w.+-]+)", text):
            _emit(out, "native_target", match.group(1), rel, "CMake native target declaration", 2)

    for rel in android_mk:
        text = _read(base / rel, MAX_BUILD_BYTES)
        if text is None:
            continue
        _emit(out, "build_system", "ndk-build", rel, "Android.mk NDK build configuration found", 5)
        for variable in ("LOCAL_SHARED_LIBRARIES", "LOCAL_STATIC_LIBRARIES", "LOCAL_WHOLE_STATIC_LIBRARIES"):
            pattern = rf"(?im)^\s*{variable}\s*[:+]?=\s*([^\n#]+)"
            for match in re.finditer(pattern, text):
                for item in match.group(1).split():
                    package = _package(item)
                    if package:
                        dependencies[package] = (rel, f"{variable} declares {item}")

    for rel in application_mk:
        text = _read(base / rel, MAX_BUILD_BYTES)
        if text is None:
            continue
        for match in re.finditer(r"(?im)^\s*APP_ABI\s*[:+]?=\s*([^\n#]+)", text):
            for abi in re.split(r"[,\s]+", match.group(1).strip()):
                if abi:
                    _emit(out, "target_abi", abi, rel, "Application.mk APP_ABI target", 4)
        for match in re.finditer(r"(?im)^\s*APP_PLATFORM\s*[:+]?=\s*([^\s#]+)", text):
            _emit(out, "target_android_api", match.group(1), rel, "Application.mk APP_PLATFORM target", 4)

    for rel in gradle:
        text = _read(base / rel, MAX_BUILD_BYTES) or ""
        if "com.android.application" in text or "com.android.library" in text:
            _emit(out, "build_system", "android-gradle", rel, "Android Gradle plugin found", 4)

    if any(Path(p).name.lower() == "makefile" for p in build_paths) and not cmake:
        _emit(out, "build_system", "make", "Makefile", "Makefile build configuration found", 2)

    sources = sorted(
        (r.path for r in records if Path(r.path).suffix.lower() in
         {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".m", ".mm"}),
        key=str.casefold,
    )
    languages: set[str] = set()
    total_bytes = 0
    scanned = 0
    for rel in sources[:MAX_SOURCE_FILES]:
        suffix = Path(rel).suffix.lower()
        languages.add("c" if suffix in {".c", ".h"} else
                      "c++" if suffix in {".cc", ".cpp", ".cxx", ".hpp"} else "objective-c")
        remaining = MAX_SOURCE_BYTES - total_bytes
        if remaining <= 0:
            break
        text = _read(base / rel, min(MAX_SOURCE_FILE_BYTES, remaining))
        if text is None:
            continue
        total_bytes += len(text.encode("utf-8", errors="replace"))
        scanned += 1
        for match in re.finditer(r'(?m)^\s*#\s*include\s*[<"]([^>"]+)[>"]', text):
            header = Path(match.group(1)).name.lower()
            package = _HEADERS.get(header)
            if package:
                dependencies[package] = (rel, f"source include {match.group(1)}")

    for language in sorted(languages):
        _emit(out, "source_language", language, "source inventory", f"{language.upper()} source/header files found", 2)
    if scanned:
        _emit(out, "source_code", "native", "source inventory",
              f"Read bounded include metadata from {scanned} files; source was not executed", 3)
    if len(sources) > MAX_SOURCE_FILES or total_bytes >= MAX_SOURCE_BYTES:
        _emit(out, "analysis_limit", "source_probe_truncated", "source inventory",
              f"Stopped after {scanned} files / {total_bytes} bytes", 0)

    for package, (source, detail) in sorted(dependencies.items()):
        _emit(out, "dependency", package, source, detail, 3)
    if any(name.startswith("sdl2") for name in dependencies):
        _emit(out, "engine", "sdl", "source/build metadata",
              "SDL portability-layer evidence found; this does not prove a full game engine", 5)
    return out
