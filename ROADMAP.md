# Roadmap

## v0.1.0 — Foundation
- [x] Port Project manifest, CLI, read-only scanner, route planner, plugin contract
- [x] Starter templates, tests, security docs and CI

## v0.2.0 — Better reconnaissance
- [x] PE import table and ELF DT_NEEDED parsing
- [x] Unity/Unreal/Godot metadata probes
- [x] ZIP central-directory metadata inspection
- [x] Synthetic and malformed-input tests
- [ ] Licensed real-game corpus and confidence calibration

## v0.3.0 — External-tool adapters
- [x] Optional Ghidra Headless adapter with disposable read-only project
- [x] Bounded metadata exporter, timeout, input SHA-256 verification
- [x] Optional Android NDK/CMake native shared-library build adapter
- [x] Logs, artifact hashes, build provenance, CLI commands
- [x] Mocked external-process tests

## v0.3.1 — Source-native reconnaissance and real build validation
- [x] Bounded C/C++ source and build-system metadata probes
- [x] SDL2 dependency recognition
- [x] Android.mk/Application.mk ABI/API detection
- [x] Android ndk-build adapter and Windows launcher support
- [x] Real NDK 21.4.7075529 arm64-v8a/API 21 smoke build against a pinned DungeonRush Android project
- [x] Eight native shared libraries verified and SHA-256 recorded
- [ ] Package/install APK and test launch on an Android device
- [ ] Test touch/input, audio, saves, rendering, and performance on real hardware

## v0.4.x — AI-assisted port workflow
- [ ] Agent task graph with bounded permissions
- [ ] Human-reviewed patch proposals
- [ ] Build/test/repair loop with hard budgets
- [ ] Module-level native/hybrid boundary planner
- [ ] Checkpointing and resumable jobs

A milestone is complete only when its tests and documented acceptance criteria pass. A generated APK alone does not constitute a verified game port.
