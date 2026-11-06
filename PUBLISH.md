# Repository publication status

AGPT v0.3.0 adds opt-in Ghidra Headless metadata export and Android NDK/CMake native-library builds.

- Repository: https://github.com/2719126468-ship-it/android-game-porting-toolkit
- Default branch: `main`
- Previous release: `0.2.0`
- Current release: `0.3.0`

The adapter tests mock the external processes. Real Ghidra script execution and a real NDK/CMake build remain explicit validation tasks; see `docs/ADAPTERS.md` and `ROADMAP.md`. The CI workflow runs the Python test suite but does not install proprietary/external toolchains.

Do not commit commercial game binaries, proprietary assets, save files, credentials, license tokens, or generated APKs. See `.gitignore` and `SECURITY.md`.
