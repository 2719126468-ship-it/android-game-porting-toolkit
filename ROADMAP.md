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

## v0.3.0 — Reproducible adapters
- [x] Optional Ghidra Headless adapter with disposable read-only project
- [x] Bounded metadata exporter, timeout, input SHA-256 verification
- [x] Optional Android NDK/CMake native shared-library build adapter
- [x] Logs, artifact hashes, build provenance, CLI commands
- [x] Mocked external-process tests
- [ ] Validate with an installed Ghidra distribution
- [ ] Validate with a real Android NDK/CMake smoke project
- [ ] ADB device test protocol

## v0.4.x — AI-assisted port workflow
- [ ] Agent task graph with bounded permissions
- [ ] Human-reviewed patch proposals
- [ ] Build/test/repair loop with hard budgets
- [ ] Module-level native/hybrid boundary planner
- [ ] Checkpointing and resumable jobs

A milestone is complete only when its tests and documented acceptance criteria pass. A generated APK alone does not constitute a verified game port.
