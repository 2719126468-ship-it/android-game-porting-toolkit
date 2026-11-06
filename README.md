# Android Game Porting Toolkit (AGPT)

AI-assisted, evidence-driven PC-to-Android game porting workspace.

AGPT is an orchestration and analysis toolkit—not a universal emulator and not a promise that every PC game can be converted automatically. It inventories game directories, identifies executable/package metadata, produces traceable route recommendations, checks local toolchains, and creates starter projects for native Android and compatibility workflows.

> v0.3.0 scope: bounded read-only reconnaissance, PE/ELF dependency extraction, Unity/Unreal/Godot metadata probes, metadata-only ZIP inspection, route planning, analyzer plugins, an opt-in Ghidra Headless adapter, and an opt-in Android NDK/CMake native-library build adapter. AGPT does not execute imported games, bypass DRM/anti-cheat, unpack protected content, or claim that a native library or APK is playable merely because it builds.

## Capabilities

- Create portable Port Project manifests without copying or modifying source game directories.
- Inventory files safely; skip symlinks and never execute imported game binaries during analysis.
- Parse PE import tables and ELF DT_NEEDED entries with bounded reads.
- Detect Unity editor/player/package metadata, Unreal build/PAK metadata, and Godot PCK versions.
- Inspect ZIP/APK/JAR central-directory metadata without decompression or extraction.
- Flag unsafe archive member paths and suspicious declared compression ratios.
- Compare native, compatibility, and hybrid routes using traceable heuristic evidence.
- Run Ghidra Headless for one user-selected binary and export bounded program metadata.
- Configure and build Android native shared libraries using a user-installed NDK/CMake toolchain, recording logs, hashes, and provenance.
- Check optional tools including Ghidra, Java, CMake, Android SDK/NDK, ADB, Wine, and Box64.

## Install

Python 3.10+; no runtime third-party Python dependencies.

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"
    agpt --help

## Quick start

    agpt init ./projects/my-game --name "My Game" --source "/path/to/game"
    agpt analyze ./projects/my-game
    agpt doctor --json
    agpt ghidra analyze ./game.exe --output ./reports/game-ghidra.json
    agpt ndk build ./native-source --build-dir ./build/game-arm64 --abi arm64-v8a --api 26 --build-type Release

Analysis writes JSON and Markdown reports under the Port Project. Source game files remain untouched.

## Route model

| Route | Intended use | Current behavior |
|---|---|---|
| Native | Reuse/port engine and game code to Android ARM64 | NDK/CMake starter and optional native-library build adapter |
| Compatibility | Run an original Windows build under an appropriate runtime | Generate profiles; runtime setup/launch is not automatic |
| Hybrid | Replace selected modules while keeping other components | Planning and evidence only; integration is project-specific |

Route scores are heuristic fit scores, not probabilities, benchmarks, or compatibility guarantees. Unknown or ambiguous evidence should result in manual review.

## External tools and trust boundaries

Ghidra and Android SDK/NDK/CMake are optional user-installed tools. AGPT does not download, install, or update them. Ghidra imports with read-only mode into a disposable project and exports metadata only; it does not decompile or patch the selected binary. The NDK adapter executes CMake project build logic from the supplied source tree. Only build source you trust, preferably in an isolated worker with no unrelated secrets and restricted network access.

A successful native-library build does not mean an APK was assembled, installed, or that gameplay works. APK packaging and real-device gameplay QA are separate milestones.

See SECURITY.md, docs/ARCHITECTURE.md, docs/ADAPTERS.md, docs/SAFETY_AND_LIMITS.md, and ROADMAP.md.
