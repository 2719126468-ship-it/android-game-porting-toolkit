# Android Game Porting Toolkit (AGPT)

**AI-assisted, evidence-driven PC-to-Android game porting workspace.**

AGPT is an orchestration and analysis toolkit—not a universal emulator and not a promise that every PC game can be converted automatically. It inventories game directories, identifies executable and package metadata, produces traceable route recommendations, checks the local toolchain, and creates starter projects for native Android and compatibility workflows.

> **v0.2.0 scope:** project management, bounded read-only inspection, PE/ELF dependency extraction, Unity/Unreal/Godot metadata probes, metadata-only ZIP inspection, route planning, plugin interfaces, starter templates, tests, and CI. It does not execute imported games, defeat DRM/anti-cheat, unpack protected content, or claim that an APK is playable merely because it builds.

## What it can do

- Create a portable Port Project manifest without copying or modifying the source game.
- Inventory files safely (skip symlinks; do not execute binaries) and identify PE/ELF architecture.
- Parse PE import tables and ELF DT_NEEDED entries with bounded reads.
- Detect Unity editor/player/package metadata, Unreal build and PAK metadata, and Godot PCK versions.
- Inspect ZIP/APK/JAR central-directory metadata without decompressing or extracting members.
- Flag unsafe archive member paths and suspicious declared compression ratios.
- Detect evidence for Ren'Py, RPG Maker, SDL, DirectX, and other common runtime clues.
- Compare native, compatibility, and hybrid routes using explainable heuristics.
- Produce JSON and Markdown reports with evidence and uncertainty.
- Check optional tools such as Ghidra, Java, CMake, Ninja, Android SDK/NDK, ADB, Wine, Box64, and Gradle.
- Generate a minimal Android NDK/CMake starter project or a compatibility profile.
- Load third-party analyzer plugins through Python entry points.

## Requirements

- Python 3.10 or later.
- No runtime third-party Python dependencies.
- Optional: pytest for the test suite; Android SDK/NDK, JDK, CMake, Wine/Box64, and Ghidra only when using those workflows.

## Install

    python -m venv .venv
    . .venv/bin/activate                 # Windows: .venv\Scripts\activate
    python -m pip install -e ".[dev]"
    agpt --help

Without installing the package:

    PYTHONPATH=src python -m agpt --help

## Quick start

    agpt init ./projects/my-game --name "My Game" --source "/path/to/game"
    agpt analyze ./projects/my-game
    agpt doctor
    agpt scaffold native ./work/my-game-android --package-id com.example.mygame
    agpt scaffold compatibility ./work/my-game-compat --executable game.exe

The analysis writes analysis/analysis.json and analysis/report.md inside the project. The source game remains untouched.

## Route model

| Route | Intended use | Current behavior |
|---|---|---|
| Native | Reuse or port engine/game code to ARM64/Android | Provides an NDK/CMake starter and evidence report |
| Compatibility | Run an original Windows build under an appropriate compatibility stack | Generates a profile; does not bundle or launch Wine/Box64 |
| Hybrid | Replace selected modules while retaining a compatibility runtime | Produces a plan and flags module boundaries for human review |

Route scores are heuristic fit scores, not probabilities, benchmarks, or compatibility guarantees. Unknown or ambiguous evidence should result in manual review.

## Analysis limits and safety

- PE/ELF parsing has per-file byte budgets and descriptor/program-header limits.
- Binary files are never executed during analysis.
- ZIP inspection reads only the end record and central directory. It never decompresses or extracts members; ZIP64 directory parsing is reported as unsupported in this release.
- Unsupported, malformed, oversized, or ambiguous inputs produce warnings rather than inferred success.
- Engine version probes are format-specific and do not guarantee every build exposes its version.
- Use AGPT only with software and assets you are authorized to inspect and modify. It does not bypass DRM, license checks, anti-cheat, online authentication, or other access controls. Keep commercial game binaries and assets out of Git.

See SECURITY.md, docs/ARCHITECTURE.md, docs/AGENTS.md, docs/PLUGIN_API.md, docs/SAFETY_AND_LIMITS.md, and ROADMAP.md.

## Development

    python -m unittest discover -s tests -v
    python -m compileall -q src tests
    python -m agpt --help

Contributions should include tests and preserve the rule that imported game binaries are never executed by analyzers. See CONTRIBUTING.md.

## Status

0.2.0 is an early alpha. The next milestones are a licensed real-game test corpus, calibrated confidence estimates, target-device capability profiles, and optional external tool adapters. See ROADMAP.md.
