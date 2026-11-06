# Roadmap

## v0.1.0 — Foundation (this release)
- [x] Portable project manifest and project initialization
- [x] Read-only directory inventory
- [x] PE/ELF architecture detection
- [x] Engine/API evidence heuristics
- [x] Explainable native/compatibility/hybrid route scoring
- [x] Toolchain diagnostics
- [x] Native Android NDK starter template
- [x] Compatibility profile template
- [x] Analyzer plugin entry-point contract
- [x] Unit tests and GitHub Actions CI

## v0.2.x — Better reconnaissance
- [ ] Robust PE import-table and ELF dependency extraction
- [ ] Unity/Unreal/Godot version and packaging analyzers
- [ ] Archive metadata inspection with size/decompression limits
- [ ] Evidence confidence calibration using a public test corpus
- [ ] Machine-readable capability matrix per target device

## v0.3.x — Reproducible adapters
- [ ] Optional Ghidra headless adapter (user-installed Ghidra only)
- [ ] Optional Android SDK/NDK build adapter
- [ ] Wine/Box64 profile validation without automatic execution by default
- [ ] Artifact provenance, hashes, and build logs
- [ ] Device test protocol via explicit ADB target selection

## v0.4.x — AI-assisted port workflow
- [ ] Agent task graph with bounded permissions
- [ ] Human-reviewed patch proposals
- [ ] Build/test/repair loop with hard budgets
- [ ] Module-level native/hybrid boundary planner
- [ ] Checkpointing and resumable jobs

## v1.0 — Stable platform
- [ ] Versioned plugin compatibility policy
- [ ] Signed build provenance and reproducible build guidance
- [ ] Real-device validation matrix
- [ ] Documented support tiers and known limitations

A milestone is complete only when its tests and documented acceptance criteria pass. A generated APK alone does not constitute a verified game port.
