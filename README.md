# Android Game Porting Toolkit (AGPT)

**AI-assisted, evidence-driven PC-to-Android game porting workspace.**

AGPT is an orchestration and analysis toolkit—not a universal emulator and not a promise that every PC game can be converted automatically. It inventories a game directory, detects file formats and common engine signals, produces a traceable route recommendation, checks the local toolchain, and creates starter projects for native Android and compatibility workflows.

> **v0.1.0 scope:** project management, read-only game inspection, heuristic route planning, plugin interfaces, toolchain diagnostics, starter templates, tests, and CI. It does not execute imported games, defeat DRM/anti-cheat, unpack protected content, or claim that an APK is playable merely because it builds.

## What it can do today

- Create a portable `Port Project` manifest without copying or modifying the source game.
- Inventory files safely (skip symlinks; do not execute binaries) and identify PE/ELF architecture from headers.
- Detect evidence for Unity, Unreal, Godot, Ren'Py, RPG Maker, SDL, DirectX, and unknown/custom engines.
- Compare native, compatibility, and hybrid routes using explainable heuristics.
- Produce JSON and Markdown reports with evidence and uncertainty.
- Check for optional tools such as Ghidra, Java, CMake, Ninja, Android SDK/NDK, ADB, Wine, Box64, and Gradle.
- Generate a minimal Android NDK/CMake starter project or a compatibility-run profile.
- Load third-party analyzer plugins through Python entry points.

## Requirements

- Python 3.10 or later.
- No runtime third-party Python dependencies.
- Optional: `pytest` for the test suite; Android SDK/NDK, JDK, CMake, Wine/Box64, and Ghidra only when using those workflows.

## Install

```bash
python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
agpt --help
```

Without installing the package:

```bash
PYTHONPATH=src python -m agpt --help
```

## Quick start

```bash
agpt init ./projects/my-game --name "My Game" --source "/path/to/game"
agpt analyze ./projects/my-game
agpt doctor
agpt scaffold native ./work/my-game-android --package-id com.example.mygame
agpt scaffold compatibility ./work/my-game-compat --executable game.exe
```

The analysis writes `analysis/analysis.json` and `analysis/report.md` inside the project. The source game remains untouched.

## Route model

| Route | Intended use | v0.1.0 behavior |
|---|---|---|
| Native | Reuse or port engine/game code to ARM64/Android | Provides a minimal NDK/CMake starter and evidence report |
| Compatibility | Run an original Windows build under an appropriate compatibility stack | Generates a profile; does not bundle or launch Wine/Box64 |
| Hybrid | Replace selected modules while retaining a compatibility runtime | Produces a plan and flags module boundaries for human review |

The route scores are heuristic fit scores, not probabilities, benchmarks, or compatibility guarantees.

## Safety and legal boundaries

AGPT is designed for games and assets the operator is authorized to inspect and modify. It performs read-only inventory and header/signature analysis by default. It does not bypass DRM, license checks, anti-cheat, online authentication, or other access controls; it does not fetch proprietary game data; and it does not redistribute game files. Keep commercial game binaries and assets out of Git.

See [SECURITY.md](SECURITY.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AGENTS.md](docs/AGENTS.md), [docs/PLUGIN_API.md](docs/PLUGIN_API.md), and [PUBLISH.md](PUBLISH.md).

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m agpt --help
```

Contributions should include tests and preserve the rule that imported game binaries are never executed by analyzers. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

`0.1.0` is an early foundation release. The next milestones are stronger format analyzers, repeatable device-based validation, isolated build workers, and opt-in integrations with Ghidra/NDK/Wine/Box64. See [ROADMAP.md](ROADMAP.md).
