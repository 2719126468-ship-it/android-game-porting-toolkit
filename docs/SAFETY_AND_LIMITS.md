# Safety, legal, and technical limits

- File inspection is read-only and never executes a game's EXE/DLL/SO.
- Symlinks are skipped and file traversal is capped.
- PE analysis caps the number of sections, import descriptors, per-name reads, and aggregate bytes read per binary.
- ELF analysis caps program headers, PT_DYNAMIC size, dynamic entries, string-table size, and aggregate bytes read per binary.
- Binary dependency inspection is limited to a bounded number of candidates per scan.
- ZIP analysis reads the end-of-central-directory record and central-directory metadata only; it never decompresses members. It caps archive size, central-directory size, candidate count, member count, and member-name length.
- ZIP64 archives are identified but their full central directories are not parsed in this version.
- Archive member paths are flagged when absolute, drive-qualified, or containing parent traversal components. AGPT does not extract them.
- Declared compression ratios are untrusted metadata and only used as warning signals.
- Godot PCK, UnityFS, Unreal PAK, and RPA probes read bounded headers/footers only.
- Heuristic scores are a triage aid, not a compatibility test.
- Engine detection may be incomplete, especially for custom engines, packed binaries, encrypted assets, and stripped builds.
- Commercial titles may depend on DRM, online services, anti-cheat, proprietary middleware, or licensed assets. AGPT does not bypass those systems.
- Compatibility depends on the exact game build, CPU ABI, GPU driver, Android version, memory, and runtime versions.
- A successful native library build or APK installation is not proof of a playable port. Gameplay verification requires real-device testing.
