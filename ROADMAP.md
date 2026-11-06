# Roadmap

## v0.1.0 — Foundation
- [x] Portable project manifest and project initialization
- [x] Read-only directory inventory
- [x] PE/ELF architecture identification
- [x] Initial engine/API evidence heuristics
- [x] Explainable native/compatibility/hybrid route scoring
- [x] Toolchain diagnostics and starter templates
- [x] Analyzer plugin entry-point contract
- [x] Unit tests and GitHub Actions CI

## v0.2.0 — Better reconnaissance (implemented)
- [x] PE import-table extraction with RVA-to-file mapping and bounded reads
- [x] ELF PT_DYNAMIC / DT_NEEDED dependency extraction
- [x] Unity version/package metadata probes
- [x] Unreal Build.version, PAK footer, and IoStore layout probes
- [x] Godot PCK engine/pack version probe
- [x] ZIP central-directory metadata inspection without extraction
- [x] Synthetic binary/package fixtures and malformed-input tests
- [ ] Public real-game sample corpus with licensing review
- [ ] Confidence calibration against labeled real-game observations
- [ ] Machine-readable target-device capability matrix

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
