"""Opt-in Android NDK CMake build adapter (builds native libraries, not APKs)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class NdkBuildError(RuntimeError):
    """A local Android NDK/CMake build failed validation or execution."""


SUPPORTED_ABIS = {"arm64-v8a", "armeabi-v7a", "x86", "x86_64"}
BUILD_TYPES = {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}


@dataclass(frozen=True)
class NdkBuildResult:
    source_dir: str
    build_dir: str
    ndk_dir: str
    ndk_version: str | None
    cmake: str
    abi: str
    android_api: int
    build_type: str
    libraries: list[dict[str, Any]]
    configure_log: str
    build_log: str
    provenance_path: str
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers) or (0,)


def discover_ndk(ndk_dir: str | Path | None = None, sdk_dir: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if ndk_dir:
        candidates.append(Path(ndk_dir).expanduser())
    for name in ("ANDROID_NDK_HOME", "ANDROID_NDK_ROOT"):
        if os.environ.get(name):
            candidates.append(Path(os.environ[name]).expanduser())
    sdk = Path(sdk_dir).expanduser() if sdk_dir else None
    if sdk is None:
        for name in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
            if os.environ.get(name):
                sdk = Path(os.environ[name]).expanduser()
                break
    if sdk:
        ndk_root = sdk / "ndk"
        if ndk_root.is_dir():
            versions = sorted((item for item in ndk_root.iterdir() if item.is_dir()),
                              key=lambda item: _version_key(item.name), reverse=True)
            candidates.extend(versions)
        legacy = sdk / "ndk-bundle"
        candidates.append(legacy)
    for candidate in candidates:
        toolchain = candidate / "build" / "cmake" / "android.toolchain.cmake"
        if candidate.is_dir() and toolchain.is_file():
            return candidate.resolve()
    raise NdkBuildError(
        "Android NDK was not found. Pass --ndk or set ANDROID_NDK_HOME; "
        "an Android SDK with side-by-side ndk/<version> is also supported."
    )


def discover_cmake(cmake: str | Path | None = None, sdk_dir: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if cmake:
        explicit = Path(cmake).expanduser()
        if explicit.is_dir():
            binary_name = "cmake.exe" if os.name == "nt" else "cmake"
            candidates.extend([explicit / binary_name, explicit / "bin" / binary_name,
                               explicit / "Contents" / "bin" / binary_name])
        else:
            candidates.append(explicit)
            resolved_command = shutil.which(str(cmake))
            if resolved_command:
                candidates.append(Path(resolved_command))
    if sdk_dir:
        cmake_root = Path(sdk_dir).expanduser() / "cmake"
        if cmake_root.is_dir():
            versions = sorted((item for item in cmake_root.iterdir() if item.is_dir()),
                              key=lambda item: _version_key(item.name), reverse=True)
            candidates.extend(item / "bin" / ("cmake.exe" if os.name == "nt" else "cmake")
                              for item in versions)
    found = shutil.which("cmake")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise NdkBuildError("CMake was not found. Install CMake or pass --cmake explicitly.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, timeout: int, log_path: Path, stage: str) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                check=False, shell=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        log_path.write_text(f"{stage} timed out after {timeout}s\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n", encoding="utf-8")
        raise NdkBuildError(f"CMake {stage} timed out after {timeout}s; see {log_path}") from exc
    log_path.write_text(
        f"COMMAND: {json.dumps(command, ensure_ascii=False)}\nEXIT: {result.returncode}\n\n"
        f"STDOUT\n{result.stdout or ''}\n\nSTDERR\n{result.stderr or ''}\n", encoding="utf-8")
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "")[-3000:]
        raise NdkBuildError(f"CMake {stage} failed with exit code {result.returncode}; see {log_path}. {output}")


def build_native(
    source_dir: str | Path,
    build_dir: str | Path,
    *,
    ndk_dir: str | Path | None = None,
    sdk_dir: str | Path | None = None,
    cmake: str | Path | None = None,
    abi: str = "arm64-v8a",
    android_api: int = 26,
    build_type: str = "Debug",
    timeout: int = 900,
    jobs: int = 2,
    generator: str | None = None,
) -> NdkBuildResult:
    """Configure and build a CMake Android native library using a local NDK.

    This runs CMake project scripts. Only invoke it on source trees whose build files
    you trust. It does not build an APK or install anything on a device.
    """
    source_input = Path(source_dir).expanduser()
    if source_input.is_symlink() or not source_input.is_dir() or not (source_input / "CMakeLists.txt").is_file():
        raise NdkBuildError("source-dir must be a regular directory containing CMakeLists.txt, not a symlink")
    source = source_input.resolve()
    if abi not in SUPPORTED_ABIS:
        raise ValueError(f"Unsupported Android ABI '{abi}'. Choose one of: {', '.join(sorted(SUPPORTED_ABIS))}")
    if android_api < 21 or android_api > 100:
        raise ValueError("android-api must be between 21 and 100")
    if build_type not in BUILD_TYPES:
        raise ValueError(f"Unsupported build type: {build_type}")
    if timeout < 10 or timeout > 7200:
        raise ValueError("timeout must be between 10 and 7200 seconds")
    if jobs < 1 or jobs > 64:
        raise ValueError("jobs must be between 1 and 64")

    ndk = discover_ndk(ndk_dir, sdk_dir)
    sdk = Path(sdk_dir).expanduser() if sdk_dir else None
    if sdk is None:
        sdk_env = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        sdk = Path(sdk_env).expanduser() if sdk_env else None
    cmake_bin = discover_cmake(cmake, sdk)
    toolchain = ndk / "build" / "cmake" / "android.toolchain.cmake"
    build_input = Path(build_dir).expanduser()
    if build_input.is_symlink():
        raise NdkBuildError("build-dir must not be a symlink")
    build = build_input.resolve()
    if build.exists() and not build.is_dir():
        raise NdkBuildError("build-dir exists but is not a directory")
    try:
        build.relative_to(source)
    except ValueError:
        pass
    else:
        raise NdkBuildError("build-dir must be outside source-dir to keep the source tree unchanged")
    if build.exists() and any(build.iterdir()) and not (build / "CMakeCache.txt").is_file():
        raise NdkBuildError("build-dir is not empty and has no CMakeCache.txt; choose an empty build directory")
    build.mkdir(parents=True, exist_ok=True)
    cache_path = build / "CMakeCache.txt"
    if cache_path.is_symlink():
        raise NdkBuildError("CMakeCache.txt must not be a symlink")
    if cache_path.is_file():
        if cache_path.stat().st_size > 16 * 1024 * 1024:
            raise NdkBuildError("CMakeCache.txt exceeds the 16 MiB safety limit")
        cache = cache_path.read_text(encoding="utf-8", errors="replace")
        if f"CMAKE_HOME_DIRECTORY:INTERNAL={source}" not in cache:
            raise NdkBuildError("existing CMake build directory belongs to a different source directory")

    logs = build / "agpt-logs"
    if logs.is_symlink():
        raise NdkBuildError("agpt-logs must not be a symlink")
    logs.mkdir(exist_ok=True)
    configure_log = logs / "configure.log"
    build_log = logs / "build.log"
    provenance_path = build / "agpt-build-provenance.json"
    if any(path.is_symlink() for path in (configure_log, build_log, provenance_path)):
        raise NdkBuildError("build logs and provenance output paths must not be symlinks")
    selected_generator = generator
    if selected_generator is None and shutil.which("ninja"):
        selected_generator = "Ninja"

    configure = [
        str(cmake_bin), "-S", str(source), "-B", str(build),
        "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain),
        "-DANDROID_ABI=" + abi,
        "-DANDROID_PLATFORM=android-" + str(android_api),
        "-DANDROID_STL=c++_shared",
        "-DCMAKE_BUILD_TYPE=" + build_type,
        "-DANDROID_TOOLCHAIN=clang",
    ]
    if selected_generator:
        configure.extend(["-G", selected_generator])
    started = time.monotonic()
    _run(configure, timeout=timeout, log_path=configure_log, stage="configure")
    build_command = [str(cmake_bin), "--build", str(build), "--config", build_type, "--parallel", str(jobs)]
    _run(build_command, timeout=timeout, log_path=build_log, stage="build")

    libraries = []
    for artifact in sorted(build.rglob("*.so")):
        if artifact.is_file() and not artifact.is_symlink():
            libraries.append({
                "path": str(artifact.relative_to(build).as_posix()),
                "size": artifact.stat().st_size,
                "sha256": sha256_file(artifact),
            })
    if not libraries:
        raise NdkBuildError("CMake build succeeded but produced no .so library; see build log. This adapter expects a native-library target.")

    ndk_version = None
    properties = ndk / "source.properties"
    if properties.is_file():
        match = re.search(r"^Pkg\.Revision\s*=\s*(.+)$", properties.read_text(encoding="utf-8", errors="replace"), re.M)
        if match:
            ndk_version = match.group(1).strip()
    provenance = {
        "schema_version": "1.0",
        "status": "native_library_build_success",
        "source_dir": str(source),
        "build_dir": str(build),
        "ndk_dir": str(ndk),
        "ndk_version": ndk_version,
        "cmake": str(cmake_bin),
        "abi": abi,
        "android_api": android_api,
        "build_type": build_type,
        "generator": selected_generator or "cmake-default",
        "libraries": libraries,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "limitations": [
            "This result verifies native CMake library outputs only; it is not an APK.",
            "No device install or gameplay verification was performed.",
            "The build invokes CMake project logic; only build files you trust should be used.",
        ],
    }
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return NdkBuildResult(
        source_dir=str(source), build_dir=str(build), ndk_dir=str(ndk), ndk_version=ndk_version,
        cmake=str(cmake_bin), abi=abi, android_api=android_api, build_type=build_type,
        libraries=libraries, configure_log=str(configure_log), build_log=str(build_log),
        provenance_path=str(provenance_path), elapsed_seconds=provenance["elapsed_seconds"],
    )
