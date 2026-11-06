"""Bounded, read-only inventory and evidence collection for game directories."""
from __future__ import annotations

import os
import re
import struct
from pathlib import Path

from agpt.models import Evidence, FileRecord, GameInventory, normalize_path

MAX_FILES = 100_000
SIGNATURE_READ_BYTES = 2 * 1024 * 1024
MAX_SIGNATURE_FILES = 512
MAX_SIGNATURE_BYTES = 64 * 1024 * 1024
EXECUTABLE_SUFFIXES = {".exe", ".dll", ".so", ".bin", ".elf"}
PE_MACHINES = {
    0x014C: "x86", 0x8664: "x86_64", 0x01C0: "arm",
    0x01C4: "armv7", 0xAA64: "arm64", 0x0200: "ia64",
}
ELF_MACHINES = {3: "x86", 40: "arm", 62: "x86_64", 183: "arm64", 243: "riscv"}

def _identify_binary(path: Path, read_limit: int = SIGNATURE_READ_BYTES) -> tuple[str, str | None, bytes]:
    try:
        with path.open("rb") as stream:
            head = stream.read(max(0, read_limit))
    except OSError:
        return "unreadable", None, b""
    if head.startswith(b"MZ") and len(head) >= 0x40:
        pe_offset = struct.unpack_from("<I", head, 0x3C)[0]
        if pe_offset + 6 <= len(head) and head[pe_offset:pe_offset + 4] == b"PE\0\0":
            machine = struct.unpack_from("<H", head, pe_offset + 4)[0]
            return "pe", PE_MACHINES.get(machine, f"unknown_pe_0x{machine:04x}"), head
        return "mz", None, head
    if head.startswith(b"\x7fELF") and len(head) >= 20:
        endian = "<" if head[5] == 1 else ">" if head[5] == 2 else None
        if endian:
            machine = struct.unpack_from(endian + "H", head, 18)[0]
            return "elf", ELF_MACHINES.get(machine, f"unknown_elf_{machine}"), head
        return "elf", None, head
    return "data", None, head

def _kind(path: Path, binary_kind: str) -> str:
    suffix = path.suffix.lower()
    if binary_kind == "pe":
        return "windows_binary"
    if binary_kind == "elf":
        return "elf_binary"
    if suffix in {".pak", ".pck", ".rpa", ".zip", ".7z", ".dat", ".wad", ".utoc", ".ucas"}:
        return "archive_or_game_data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".dds", ".ktx", ".bmp"}:
        return "image_asset"
    if suffix in {".ogg", ".wav", ".mp3", ".flac", ".bank"}:
        return "audio_asset"
    if suffix in {".json", ".ini", ".cfg", ".xml", ".toml", ".yaml", ".yml", ".txt"}:
        return "configuration"
    if suffix == ".exe":
        return "possible_windows_executable"
    return "other"

def scan_game(root: str | Path, *, max_files: int = MAX_FILES) -> GameInventory:
    """Inventory a directory without following symlinks or executing its files."""
    base = Path(root).expanduser()
    if not base.exists():
        raise FileNotFoundError(f"Game directory does not exist: {base}")
    if not base.is_dir():
        raise NotADirectoryError(f"Game source must be a directory: {base}")
    if max_files < 1:
        raise ValueError("max_files must be at least 1")
    inventory = GameInventory(root=normalize_path(base))
    signature_blobs: list[tuple[str, bytes]] = []
    signature_bytes = 0

    for current, dirs, filenames in os.walk(base, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for dirname in dirs:
            candidate = current_path / dirname
            if candidate.is_symlink():
                inventory.skipped_symlinks += 1
            else:
                kept_dirs.append(dirname)
        dirs[:] = kept_dirs
        for filename in filenames:
            path = current_path / filename
            if path.is_symlink():
                inventory.skipped_symlinks += 1
                continue
            try:
                stat = path.stat()
                if not path.is_file():
                    continue
                rel = path.relative_to(base).as_posix()
                can_read_signature = (
                    path.suffix.lower() in EXECUTABLE_SUFFIXES
                    and len(signature_blobs) < MAX_SIGNATURE_FILES
                    and signature_bytes < MAX_SIGNATURE_BYTES
                )
                remaining = MAX_SIGNATURE_BYTES - signature_bytes
                binary_kind, arch, head = (
                    _identify_binary(path, min(SIGNATURE_READ_BYTES, remaining))
                    if can_read_signature else ("data", None, b"")
                )
                inventory.records.append(FileRecord(rel, stat.st_size, _kind(path, binary_kind), arch))
                inventory.scanned_files += 1
                if head:
                    signature_blobs.append((rel, head))
                    signature_bytes += len(head)
                if inventory.scanned_files >= max_files:
                    inventory.truncated = True
                    break
            except OSError:
                inventory.warnings.append(f"Could not inspect file: {path.name}")
        if inventory.truncated:
            break

    _collect_path_and_string_evidence(inventory, signature_blobs)
    # Deeper analyzers are bounded and read-only; failures become evidence warnings.
    from agpt.analyzers.binary import collect_binary_evidence
    from agpt.analyzers.engines import analyze_engine_metadata
    from agpt.analyzers.archives import analyze_archives
    from agpt.analyzers.source_build import analyze_source_build
    inventory.evidence.extend(collect_binary_evidence(base, inventory.records))
    inventory.evidence.extend(analyze_engine_metadata(base, inventory.records))
    inventory.evidence.extend(analyze_archives(base, inventory.records))
    inventory.evidence.extend(analyze_source_build(base, inventory.records))
    if not any(item.category == "engine" for item in inventory.evidence):
        inventory.evidence.append(Evidence(
            "engine", "unknown", "inventory",
            "No known engine marker found; custom, packed, or encrypted engine remains possible", 0
        ))
    inventory.evidence.sort(key=lambda item: (item.category, item.value, item.source))
    inventory.records.sort(key=lambda item: item.path.casefold())
    return inventory

def _collect_path_and_string_evidence(inventory: GameInventory, blobs: list[tuple[str, bytes]]) -> None:
    names = [record.path.lower().replace("\\", "/") for record in inventory.records]

    def add(category: str, value: str, source: str, detail: str, weight: int = 1) -> None:
        inventory.evidence.append(Evidence(category, value, source, detail, weight))

    rules = [
        ("unity", ("unityplayer.dll", "gameassembly.dll", "globalgamemanagers", "resources.assets"),
         "Unity runtime/data marker"),
        ("unreal", ("/content/paks/", "ue4game", "unrealengine", "globalshadercache",
                    ".utoc", ".ucas", "engine/binaries/"),
         "Unreal runtime/package marker"),
        ("godot", ("project.godot", "godot.windows", "godotengine"),
         "Godot project/runtime marker"),
        ("renpy", ("renpy/", "renpy.exe", "script.rpyc"),
         "Ren'Py script/runtime marker"),
        ("rpg_maker", ("rpg_rt.exe", "www/data/system.json", "www/js/rpg_core.js"),
         "RPG Maker data/runtime marker"),
        ("sdl", ("sdl2.dll", "sdl3.dll", "libsdl"),
         "SDL library marker"),
    ]
    for engine, markers, description in rules:
        matches = [name for name in names if any(marker in name for marker in markers)]
        if matches:
            add("engine", engine, matches[0], description, min(5, len(matches)))

    api_patterns = [
        (b"d3d12.dll", "directx12"), (b"d3d11.dll", "directx11"),
        (b"d3d9.dll", "directx9"), (b"vulkan-1.dll", "vulkan"),
        (b"opengl32.dll", "opengl"), (b"xinput1_", "xinput"),
    ]
    for rel, blob in blobs:
        lower = blob.lower()
        for marker, api in api_patterns:
            if marker in lower:
                add("graphics_or_input_api", api, rel,
                    f"Binary string marker: {marker.decode('ascii', errors='ignore')}", 2)
        dlls = sorted(set(
            match.decode("ascii", errors="ignore")
            for match in re.findall(rb"[A-Za-z0-9_.-]{2,80}\.dll", lower)
        ))
        for dll in dlls[:40]:
            if dll in {"kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll"}:
                continue
            add("dll_string", dll, rel, "DLL name found in bounded binary string scan", 1)
