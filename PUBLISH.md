# Repository publication status

AGPT code version 0.3.1 is published on the `main` branch.

- Repository: https://github.com/2719126468-ship-it/android-game-porting-toolkit
- Default branch: `main`
- Previous version: `0.3.0`
- Current code version: `0.3.1`

This version adds source/build metadata probes and the Android ndk-build adapter. The repository's DungeonRush Android smoke workflow uses a pinned reference commit and Android NDK 21.4.7075529 to build arm64-v8a/API 21 shared libraries. It uploads shared libraries, build logs, and provenance. It does not build or verify an APK or game launch.

Do not commit commercial game binaries, proprietary assets, save files, credentials, license tokens, or generated APKs. See `.gitignore` and `SECURITY.md`.
