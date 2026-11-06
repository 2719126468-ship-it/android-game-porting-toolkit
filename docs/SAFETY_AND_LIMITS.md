# Safety, legal, and technical limits

- The reconnaissance scanner does not execute imported EXE/DLL/SO files.
- Symlinks are skipped and file traversal is capped.
- PE, ELF, and archive analyzers enforce per-file, entry-count, and metadata-size limits.
- ZIP inspection reads central-directory metadata only; it never decompresses or extracts members.
- Route scores are triage heuristics, not compatibility probabilities.
- Ghidra analysis imports a selected binary read-only into a disposable project, but analysis can consume significant CPU and memory.
- The NDK adapter executes CMake configure/build logic from the supplied source tree. Do not build untrusted source on a host containing secrets; use an isolated worker with least privilege and restricted network access.
- A native .so build does not create an APK or verify gameplay.
- Real-device validation must separately test install, launch, rendering, touch/controller input, audio, save/load, stability, and performance.
- Use AGPT only with software and assets you are authorized to inspect and modify. It does not bypass DRM, license checks, anti-cheat, online authentication, or other access controls.
