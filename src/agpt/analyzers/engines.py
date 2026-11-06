"""Read-only engine/package metadata probes for common PC game formats."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

from agpt.models import Evidence

MAX_TEXT_BYTES = 256 * 1024
MAX_HEADER_BYTES = 4096
PAK_MAGIC_LE = struct.pack("<I", 0x5A6F12E1)

def _read(path: Path, limit: int = MAX_TEXT_BYTES, offset: int = 0) -> bytes:
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read(limit)

def _evidence(category: str, value: str, source: str, detail: str, weight: int = 2) -> Evidence:
    return Evidence(category, value, source, detail, weight)

def _parse_godot_pck(path: Path) -> list[Evidence]:
    size = path.stat().st_size
    offset = 0
    header = _read(path, 32)
    if header[:4] != b"GDPC" and size >= 12:
        trailer = _read(path, 12, size - 12)
        if trailer[-4:] == b"GDPC":
            embedded_size = struct.unpack_from("<Q", trailer, 0)[0]
            if 20 <= embedded_size <= size - 12:
                offset = size - 12 - embedded_size
                header = _read(path, 32, offset)
    if header[:4] != b"GDPC" or len(header) < 20:
        return []
    fmt, major, minor, patch = struct.unpack_from("<IIII", header, 4)
    if fmt > 16 or major > 100 or minor > 1000 or patch > 10000:
        return [_evidence("analysis_warning", "suspicious_godot_pck_header", path.name,
                          "GDPC marker found but header values are outside conservative plausibility bounds", 0)]
    return [
        _evidence("engine", "godot", path.name, "Godot PCK magic GDPC", 5),
        _evidence("engine_version", f"{major}.{minor}.{patch}", path.name,
                  f"Godot PCK engine version; pack format {fmt}", 5),
        _evidence("package_format", "godot_pck", path.name,
                  f"GDPC package, pack format {fmt}, header offset {offset}", 4),
    ]

def _parse_unreal_build_version(path: Path) -> list[Evidence]:
    try:
        raw = _read(path, MAX_TEXT_BYTES)
        data = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    fields = ("MajorVersion", "MinorVersion", "PatchVersion")
    if not all(isinstance(data.get(k), int) for k in fields):
        return []
    version = ".".join(str(data[k]) for k in fields)
    changelist = data.get("Changelist")
    detail = "Unreal Build.version metadata"
    if isinstance(changelist, int):
        detail += f"; changelist {changelist}"
    return [
        _evidence("engine", "unreal", path.name, "Unreal Build.version file", 5),
        _evidence("engine_version", version, path.name, detail, 5),
    ]

def _parse_unreal_pak(path: Path) -> list[Evidence]:
    size = path.stat().st_size
    if size < 8:
        return []
    tail_size = min(64 * 1024, size)
    tail = _read(path, tail_size, size - tail_size)
    index = tail.rfind(PAK_MAGIC_LE)
    if index < 0 or index + 8 > len(tail):
        return []
    version = struct.unpack_from("<I", tail, index + 4)[0]
    if version > 100:
        return [_evidence("package_format", "unreal_pak", path.name,
                          "Unreal PAK footer magic found; version field is unusual", 3)]
    return [
        _evidence("engine", "unreal", path.name, "Unreal PAK footer magic", 4),
        _evidence("package_format", f"unreal_pak_v{version}", path.name,
                  "PAK footer magic and version field", 5),
    ]

def _parse_unity_bundle(path: Path) -> list[Evidence]:
    try:
        header = _read(path, MAX_HEADER_BYTES)
    except OSError:
        return []
    if not header.startswith(b"UnityFS\0") or len(header) < 16:
        return []
    format_version = struct.unpack_from(">I", header, 8)[0]
    pos = 12
    strings = []
    for _ in range(2):
        end = header.find(b"\0", pos, min(len(header), pos + 128))
        if end < 0:
            return [_evidence("package_format", "unityfs", path.name,
                              f"UnityFS header found; format version {format_version}", 4)]
        strings.append(header[pos:end].decode("ascii", errors="replace"))
        pos = end + 1
    version = strings[0].strip()
    revision = strings[1].strip()
    result = [
        _evidence("engine", "unity", path.name, "UnityFS asset bundle header", 4),
        _evidence("package_format", f"unityfs_v{format_version}", path.name,
                  "UnityFS bundle format marker", 4),
    ]
    if re.fullmatch(r"\d{1,4}\.\d{1,4}\.\d{1,4}[abfp]\d{1,5}", version):
        result.append(_evidence("engine_version", version, path.name,
                                f"UnityFS player version; revision {revision or 'unknown'}", 5))
    return result

def _parse_unity_project_version(path: Path) -> list[Evidence]:
    try:
        text = _read(path, 16 * 1024).decode("utf-8", errors="replace")
    except OSError:
        return []
    match = re.search(r"(?m)^\s*m_EditorVersion:\s*([0-9]+\.[0-9]+\.[0-9]+[abfp][0-9]+)\s*$", text)
    if not match:
        return []
    return [
        _evidence("engine", "unity", path.name, "Unity ProjectVersion.txt", 5),
        _evidence("engine_version", match.group(1), path.name, "Unity editor version declared by project", 5),
    ]

def _parse_il2cpp_metadata(path: Path) -> list[Evidence]:
    try:
        raw = _read(path, 8)
    except OSError:
        return []
    if len(raw) < 8 or struct.unpack_from("<I", raw, 0)[0] != 0xFAB11BAF:
        return []
    version = struct.unpack_from("<I", raw, 4)[0]
    return [
        _evidence("engine", "unity", path.name, "IL2CPP global-metadata.dat magic", 4),
        _evidence("package_metadata", f"il2cpp_metadata_v{version}", path.name,
                  "IL2CPP metadata version; not the Unity editor version", 4),
    ]

def analyze_engine_metadata(root: str | Path, records) -> list[Evidence]:
    base = Path(root)
    result: list[Evidence] = []
    paths = [base / record.path for record in records]
    for record, path in zip(records, paths):
        low = record.path.lower().replace("\\", "/")
        name = path.name.lower()
        if name == "projectversion.txt" and "projectsettings/" in low:
            result.extend(_parse_unity_project_version(path))
        elif name == "build.version" and ("engine/build/" in low or "/build.version" in low):
            result.extend(_parse_unreal_build_version(path))
        elif path.suffix.lower() == ".pck":
            result.extend(_parse_godot_pck(path))
        elif path.suffix.lower() == ".pak":
            result.extend(_parse_unreal_pak(path))
        elif path.suffix.lower() in {".bundle", ".assetbundle"}:
            result.extend(_parse_unity_bundle(path))
        elif name == "global-metadata.dat":
            result.extend(_parse_il2cpp_metadata(path))
        elif name == "project.godot":
            result.append(_evidence("engine", "godot", record.path,
                                    "Godot project.godot project marker", 4))

    lowered = [record.path.lower().replace("\\", "/") for record in records]
    if any("/content/paks/" in f and f.endswith((".pak", ".utoc", ".ucas")) for f in lowered):
        result.append(_evidence("engine", "unreal", "inventory", "Unreal Content/Paks package layout", 4))
        for ext in (".utoc", ".ucas"):
            if any(f.endswith(ext) for f in lowered):
                result.append(_evidence("package_format", f"unreal_iostore_{ext[1:]}", "inventory",
                                        "Unreal IoStore package extension; no extraction performed", 3))
    if any("unityplayer.dll" in f or "gameassembly.dll" in f for f in lowered):
        result.append(_evidence("engine", "unity", "inventory", "Unity runtime binary marker", 4))
    return result
