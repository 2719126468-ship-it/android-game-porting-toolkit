# Architecture

## Design principles

1. **Evidence before automation.** Detectors emit evidence records and uncertainty; the planner never invents an engine or claims a game is playable.
2. **Read-only by default.** v0.1.0 inventories files and reads bounded headers/signatures. It does not execute binaries or unpack archives.
3. **Three interchangeable strategies.** Native, compatibility, and hybrid engines implement one strategy contract.
4. **Adapters isolate external tools.** Ghidra, Android SDK/NDK, Wine, Box64, and device tools are optional integrations, not hard dependencies.
5. **Projects are portable.** The manifest references the original source path and analysis artifacts; game files are not copied into the project.

## Data flow

```text
Source directory
   -> bounded scanner
   -> file inventory + evidence
   -> engine/API classification
   -> route planner (explainable heuristic scores)
   -> Port Project analysis artifacts
   -> optional adapter/build worker
   -> install + gameplay verification (future milestone)
```

## Port Project

`agpt init` creates a directory with `agpt.project.json`. The manifest is versioned and contains the source path, target Android ABI/API, preferred route, and creation timestamp. Analysis results are stored beneath `analysis/`. Large binaries and assets remain outside the project.

## Route planner

The planner returns three fit scores in the 0–100 range and a recommended route. Scores are not statistical probabilities. Rules are intentionally transparent and stored as reasons in the report. Missing evidence is treated as unknown, not as proof that a feature is absent.

## Plugin model

Python entry points under `agpt.analyzers` expose analyzer classes. An analyzer accepts a read-only `GameInventory` and returns a JSON-serializable dictionary. Plugin failures are isolated and recorded; plugins must not mutate or execute source files. See [PLUGIN_API.md](PLUGIN_API.md).

## Trust boundaries

Game files, plugin code, generated patches, and AI output are untrusted. Future build workers must be isolated, time- and resource-limited, and deny network access unless a task explicitly requires it. Human review is required before applying patches or running a generated executable.
