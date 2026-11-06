# Changelog

## 0.3.0 — Reproducible tool adapters (2026-11-06)

- Add opt-in Ghidra Headless analysis for one explicitly selected binary.
- Bundle a bounded Ghidra metadata exporter for program format, address range, external libraries, functions, and memory-block count.
- Use a disposable Ghidra project, read-only import, process timeout, logs, and before/after input SHA-256 verification.
- Add an opt-in Android NDK/CMake adapter for native shared-library builds.
- Record NDK version, ABI/API, build type, logs, output library hashes, and build provenance.
- Add `agpt ghidra analyze` and `agpt ndk build` commands.
- Fix CI setup for the `src` package layout by installing the package before running tests.
- Update GitHub Actions to Node 24-compatible action releases.

External adapters are tested with mocked tools in this environment. Real Ghidra and NDK executions remain separate validation tasks.

## 0.2.0 — Better reconnaissance

- Parse PE import tables and ELF DT_NEEDED dependencies.
- Detect Unity, Unreal, and Godot metadata.
- Inspect ZIP central-directory metadata without extracting members.
- Add malformed-input and resource-limit tests.

## 0.1.0 — Foundation

- Port Project manifest, CLI, read-only inventory, route planner, analyzer plugin contract, starter templates, tests, and CI.
