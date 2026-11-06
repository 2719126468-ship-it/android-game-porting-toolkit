# External-tool adapters

## Ghidra Headless

The adapter is opt-in and operates on one explicitly supplied regular file. It launches a user-installed Ghidra Headless executable, imports the file with Ghidra read-only mode into a disposable temporary project, runs the bundled AGPT metadata exporter, and writes a JSON report plus a diagnostic log.

Configure discovery with GHIDRA_INSTALL_DIR or GHIDRA_ANALYZE_HEADLESS, or pass --ghidra:

    agpt ghidra analyze ./game.exe --output ./reports/game.json --timeout 1800

The exporter reports program format/language/compiler metadata, address range, external library names, a capped function/entry-point list, and memory-block count. It does not decompile, patch, or execute the imported program. The adapter hashes the input before and after analysis and refuses to publish the report if the input changed.

## Android NDK + CMake

The CMake adapter builds a trusted CMake source tree for a selected Android ABI/API. Supply an NDK path or set ANDROID_NDK_HOME; optionally set SDK path or ANDROID_SDK_ROOT. CMake is discovered from PATH or the SDK's CMake components.

    agpt ndk build ./native-source --build-dir ./build/arm64 --abi arm64-v8a --api 26

The source tree must contain CMakeLists.txt. The build directory must be outside the source tree and either empty or carry AGPT's source-bound CMake cache marker. The adapter records configure/build logs, NDK version when available, selected ABI/API, generated shared-library SHA-256 hashes, and build provenance.

## Android ndk-build / Android.mk

The ndk-build adapter supports projects with a regular Android.mk and optional Application.mk:

    agpt ndk-build build ./jni --build-dir ./build/game-arm64 --abi arm64-v8a --api 21 --jobs 2

It locates the ndk-build launcher inside the selected NDK, routes generated objects and libraries into a separate AGPT-owned output workspace, preserves the source tree, and records the NDK version, ABI/API, shared-library sizes and SHA-256 hashes, log, and provenance. A failed build leaves an owned workspace marker so the same source/ABI/API can be retried safely. A non-empty unrelated output directory is refused.

**Both NDK adapters build shared libraries only.** They do not create an APK, install to a device, launch a game, or verify gameplay.

## Trust and isolation

All adapters are opt-in. AGPT does not install, download, or update external tools. Ghidra can be CPU/memory intensive. CMake/Android.mk build files are executable project logic: only build source you trust, preferably on an isolated worker with least privilege, bounded resources, and restricted network access.
