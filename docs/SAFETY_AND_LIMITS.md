# Safety, legal, and technical limits

- File inspection is read-only and never executes a game's EXE/DLL.
- Symlinks are skipped and file traversal is capped.
- Only bounded prefixes are read for engine/API signatures; archives are not extracted in v0.1.0.
- Heuristic scoring is a triage aid, not a compatibility test.
- Engine detection may be incomplete, especially for custom engines, packed binaries, encrypted assets, and stripped builds.
- Commercial titles may depend on DRM, online services, anti-cheat, proprietary middleware, or licensed assets. AGPT does not bypass those systems.
- Compatibility depends on the exact game build, CPU ABI, GPU driver, Android version, memory, and runtime versions.
- A successful native library build or APK installation is not proof of a playable port. Gameplay verification requires real-device testing.
