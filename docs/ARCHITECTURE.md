# Architecture

## Design principles

1. Evidence before automation: detectors report observed evidence and uncertainty.
2. Read-only reconnaissance: imported binaries are never executed by the scanner.
3. Three route strategies: native, compatibility, and hybrid share project/report contracts.
4. External tools are optional adapters: Ghidra, Android SDK/NDK, Wine, Box64, and device tools are not hard dependencies.
5. Portable projects: game files remain at the user-provided source path.

## Data flow

```text
Source directory
  -> bounded scanner
  -> PE/ELF and engine metadata probes
  -> route planner
  -> Port Project JSON/Markdown report
  -> plan-only task graph with dependencies and approval gates
  -> optional Ghidra metadata export
  -> optional NDK/CMake native-library build
  -> explicit APK packaging and device/gameplay verification
```

## Plan and execution boundary

`build_task_graph` converts observed inventory and the route recommendation into a dependency-ordered plan. Each task declares acceptance criteria and proposed capabilities. Capabilities such as writing project files, executing a build, packaging an APK, installing an app, or launching a game are marked as requiring explicit approval.

The current task graph is a planning artifact only. It does not grant capabilities or execute tasks; a future executor must enforce approvals, isolated workers, time/output budgets, and independent verification.

## External adapter boundaries

The Ghidra adapter imports one selected binary read-only into a disposable project and exports bounded metadata. It does not decompile, patch, or execute the imported program.

The Android NDK adapter configures and builds a CMake native-library project, hashes the resulting shared libraries, and records build provenance. CMake build files are executable project logic; build workers must be isolated and must not expose unrelated secrets.

Neither adapter runs automatically during a normal game scan. Both require explicit user invocation and user-installed toolchains.
