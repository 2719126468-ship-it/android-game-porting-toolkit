# Safety, legal, and technical limits

- The reconnaissance scanner does not execute imported EXE/DLL/SO files.
- Symlinks are skipped during scanning and rejected as patch targets; file traversal is capped.
- Patch proposals remain review-only until a human invokes `agpt patch apply ... --approve`; application checks proposal metadata and source SHA-256 values, rejects stale/unsafe targets, and uses an atomic replacement.
- PE, ELF, and archive analyzers enforce per-file, entry-count, and metadata-size limits.
- ZIP inspection reads central-directory metadata only; it never decompresses or extracts members.
- Route scores are triage heuristics, not compatibility probabilities.
- Ghidra analysis imports a selected binary read-only into a disposable project, but analysis can consume significant CPU and memory.
- The NDK adapter executes CMake configure/build logic from the supplied source tree. Do not build untrusted source on a host containing secrets; use an isolated worker with least privilege and restricted network access.
- A native .so build does not create an APK or verify gameplay.
- Real-device validation must separately test install, launch, rendering, touch/controller input, audio, save/load, stability, and performance.
- The patch executor applies one UTF-8 text file at a time. It does not run build commands or game code; review the proposal and keep a version-control backup before approval.
- Use AGPT only with software and assets you are authorized to inspect and modify. It does not bypass DRM, license checks, anti-cheat, online authentication, or other access controls.
