"""Opt-in ndk-build adapter for Android.mk projects; emits shared libraries, not APKs."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from agpt.adapters.ndk import SUPPORTED_ABIS, discover_ndk


class NdkMakeError(RuntimeError):
    """An ndk-build project failed validation or execution."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_native(source_dir, build_dir, *, ndk_dir=None, abi="arm64-v8a",
                 android_api=21, timeout=1800, jobs=2):
    """Build a trusted Android.mk project in a separate, AGPT-owned output tree."""
    source_input = Path(source_dir).expanduser()
    if source_input.is_symlink() or not source_input.is_dir():
        raise NdkMakeError("source-dir must be a regular directory")
    source = source_input.resolve()
    android_mk = source / "Android.mk"
    app_mk = source / "Application.mk"
    if android_mk.is_symlink() or not android_mk.is_file():
        raise NdkMakeError("source-dir must contain a regular Android.mk file")
    if app_mk.is_symlink():
        raise NdkMakeError("Application.mk must not be a symlink")
    if abi not in SUPPORTED_ABIS:
        raise ValueError(f"Unsupported ABI: {abi}")
    if not 21 <= android_api <= 100:
        raise ValueError("android-api must be between 21 and 100")
    if not 10 <= timeout <= 7200:
        raise ValueError("timeout must be between 10 and 7200 seconds")
    if not 1 <= jobs <= 64:
        raise ValueError("jobs must be between 1 and 64")

    ndk = discover_ndk(ndk_dir)
    launcher = ndk / ("ndk-build.cmd" if os.name == "nt" else "ndk-build")
    if not launcher.is_file():
        raise NdkMakeError(f"ndk-build launcher not found in {ndk}")

    build_input = Path(build_dir).expanduser()
    if build_input.is_symlink():
        raise NdkMakeError("build-dir must not be a symlink")
    build = build_input.resolve()
    try:
        build.relative_to(source)
    except ValueError:
        pass
    else:
        raise NdkMakeError("build-dir must be outside source-dir")
    marker = build / "agpt-ndkbuild-project.json"
    identity = {"source_dir": str(source), "abi": abi, "android_api": android_api}
    if marker.is_symlink():
        raise NdkMakeError("workspace marker must not be a symlink")
    if build.exists() and any(build.iterdir()):
        if not marker.is_file() or marker.stat().st_size > 1024 * 1024:
            raise NdkMakeError("build-dir is non-empty and is not an AGPT-owned workspace")
        try:
            previous = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NdkMakeError("workspace marker is invalid") from exc
        if any(previous.get(k) != v for k, v in identity.items()):
            raise NdkMakeError("build-dir belongs to a different source/ABI/API")

    build.mkdir(parents=True, exist_ok=True)
    out_dir, libs_dir, logs_dir = build / "out", build / "libs", build / "agpt-logs"
    for folder in (out_dir, libs_dir, logs_dir):
        if folder.is_symlink():
            raise NdkMakeError(f"output directory must not be a symlink: {folder}")
        folder.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "ndk-build.log"
    provenance_path = build / "agpt-ndkbuild-provenance.json"
    if log_path.is_symlink() or provenance_path.is_symlink():
        raise NdkMakeError("log/provenance path must not be a symlink")

    # Mark the workspace before execution so failed builds can be retried safely.
    marker.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    args = [
        "NDK_PROJECT_PATH=null", f"APP_BUILD_SCRIPT={android_mk}",
        f"NDK_OUT={out_dir}", f"NDK_LIBS_OUT={libs_dir}",
        f"APP_ABI={abi}", f"APP_PLATFORM=android-{android_api}", f"-j{jobs}", "-B",
    ]
    if app_mk.is_file():
        args.insert(1, f"NDK_APPLICATION_MK={app_mk}")
    if os.name == "nt":
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c",
                   subprocess.list2cmdline([str(launcher), *args])]
    else:
        command = [str(launcher), *args]

    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=str(source), capture_output=True, text=True,
                                timeout=timeout, check=False, shell=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        log_path.write_text(f"TIMEOUT after {timeout}s\nSTDOUT\n{stdout}\nSTDERR\n{stderr}\n", encoding="utf-8")
        raise NdkMakeError(f"ndk-build timed out; see {log_path}") from exc
    log_path.write_text(
        f"COMMAND: {json.dumps(command)}\nEXIT: {result.returncode}\n"
        f"STDOUT\n{result.stdout or ''}\nSTDERR\n{result.stderr or ''}\n",
        encoding="utf-8",
    )
    if result.returncode:
        raise NdkMakeError(f"ndk-build failed ({result.returncode}); see {log_path}: {(result.stderr or result.stdout or '')[-3000:]}")

    libraries = []
    for path in sorted(libs_dir.rglob("*.so")):
        if path.is_file() and not path.is_symlink():
            libraries.append({"path": path.relative_to(build).as_posix(),
                              "size": path.stat().st_size, "sha256": _sha256(path)})
    if not libraries:
        raise NdkMakeError(f"ndk-build produced no .so libraries; see {log_path}")

    revision = None
    properties = ndk / "source.properties"
    if properties.is_file():
        for line in properties.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("Pkg.Revision") and "=" in line:
                revision = line.split("=", 1)[1].strip()
                break
    provenance = {
        "schema_version": "1.0", "status": "ndk_make_native_library_build_success",
        **identity, "ndk_dir": str(ndk), "ndk_version": revision,
        "ndk_build": str(launcher), "libraries": libraries,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "limitations": ["This is a shared-library build, not an APK.",
                        "No device install, launch, or gameplay verification was performed.",
                        "Android.mk files are executable build logic; use only trusted source."],
    }
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**provenance, "build_dir": str(build), "build_log": str(log_path),
            "provenance_path": str(provenance_path)}
