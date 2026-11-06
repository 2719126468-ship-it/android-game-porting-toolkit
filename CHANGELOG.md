# Changelog

## Unreleased — v0.4.x patch proposals and Android APK publishing

- Add read-only unified-diff patch proposals with SHA-256 source baselines, evidence, file-size limits, and path/symlink traversal protection; no patch application or source mutation is enabled.
- Add the original AGPT Orbit Snake SDL2 sample and an Android CI workflow that builds API 27+ ARMv7/ARM64 APKs, uploads CI artifacts, and supports tag-triggered GitHub Releases with license notices.

## Unreleased — v0.4.x task planning preview

- Add `agpt plan` to create a dependency-ordered Native, Compatibility, or Hybrid task graph with acceptance criteria and explicit human approval gates.
- Keep task generation plan-only: no task executor is available, proposed capabilities are not granted, and no source mutation, build, package, install, or game launch occurs.

## 0.3.1 — Source-native reconnaissance and real NDK build (2026-11-06)

- Add bounded, read-only source/build probes for C/C++, CMake, Android.mk, Application.mk, Gradle, and Makefile projects.
- Detect SDL2, SDL2_image, SDL2_mixer, SDL2_net, and SDL2_ttf from bounded build declarations and source includes.
- Feed source-language, native-target, Android ABI/API, and build-system evidence into route planning.
- Add the `agpt ndk-build build` adapter for trusted Android.mk projects, with isolated outputs, bounded timeout, logs, hashes, and provenance.
- Add mocked tests for source recognition, ndk-build outputs, Windows launcher handling, and retry-safe build workspaces.
- Run a real GitHub Actions Android NDK smoke build against a pinned DungeonRush Android reference project: NDK 21.4.7075529, arm64-v8a, API 21; eight shared libraries were produced and hashed. This is not an APK or gameplay claim.
- Add a repeatable workflow artifact containing the Android shared libraries, logs, and provenance.
- Build the pinned upstream DungeonRush Android reference APK successfully with NDK r21e, Gradle 5.6, AGP 3.5.0, and JDK 8; verify package ID, min API 16, and both arm64-v8a/armeabi-v7a ABIs (16 shared libraries total). This validates packaging only; it is not an AGPT-generated port or a gameplay test, and the APK is not redistributed while asset rights remain unresolved.
- Publish a validation report, manifest badging, and ABI/library inventory as a GitHub Actions artifact; document device/gameplay testing as the next acceptance gate.

## 0.3.0 — Reproducible tool adapters

- Add opt-in Ghidra Headless analysis for one explicitly selected binary.
- Bundle a bounded Ghidra metadata exporter for program format, address range, external libraries, functions, and memory-block count.
- Use a disposable Ghidra project, read-only import, process timeout, logs, and before/after input SHA-256 verification.
- Add an opt-in Android NDK/CMake native-library build adapter.
- Record NDK version, ABI/API, build type, logs, output library hashes, and build provenance.
- Add `agpt ghidra analyze` and `agpt ndk build` commands.
- Fix CI setup for the `src` package layout by installing the package before running tests.
- Update GitHub Actions to Node 24-compatible action releases.

## 0.2.0 — Better reconnaissance

- Parse PE import tables and ELF DT_NEEDED dependencies.
- Detect Unity, Unreal, and Godot metadata.
- Inspect ZIP central-directory metadata without extracting members.
- Add malformed-input and resource-limit tests.

## 0.1.0 — Foundation

- Port Project manifest, CLI, read-only inventory, route planner, analyzer plugin contract, starter templates, tests, and CI.
