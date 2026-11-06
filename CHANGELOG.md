# Changelog

## 0.2.0 — Better reconnaissance

- Parse PE optional headers and section mappings to extract direct import DLL names.
- Parse ELF program headers and PT_DYNAMIC to extract bounded DT_NEEDED dependencies.
- Detect Unity ProjectVersion.txt, UnityFS bundle headers, and IL2CPP metadata markers.
- Detect Unreal Build.version metadata, PAK footer/version markers, and IoStore package layout.
- Detect Godot PCK engine and pack versions, including the documented embedded-pack trailer layout.
- Inspect ZIP central-directory metadata without decompressing or extracting members.
- Flag suspicious archive paths, extreme declared compression ratios, unsupported ZIP64 metadata, and parser-limit conditions.
- Add synthetic binary/package fixtures and malformed-input tests.
- Keep analyzers read-only, with explicit input, entry-count, header-read, and metadata-size limits.

## 0.1.0 — Foundation

- Port Project manifest and CLI lifecycle.
- Read-only bounded game directory scanning.
- PE/ELF architecture and engine/API evidence heuristics.
- Explainable native/compatibility/hybrid route scoring with manual-review fallback.
- Deterministic Scout and Route Planner agents.
- Optional trusted analyzer entry-point plugins.
- Toolchain diagnostics, native Android NDK starter, and compatibility profile template.
- Unit tests, security guidance, plugin documentation, roadmap, and GitHub Actions CI.
