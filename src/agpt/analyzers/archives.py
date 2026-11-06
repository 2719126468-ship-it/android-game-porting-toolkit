"""Metadata-only archive inspection. No member data is decompressed or extracted."""
from __future__ import annotations

import re
import struct
from pathlib import Path

from agpt.models import Evidence

MAX_ARCHIVE_ENTRIES = 10_000
MAX_CENTRAL_DIRECTORY = 4 * 1024 * 1024
MAX_NAME_BYTES = 4096
MAX_ARCHIVE_SIZE = 8 * 1024 * 1024 * 1024
EOCD = b"PK\x05\x06"
CENTRAL = b"PK\x01\x02"

def inspect_zip_metadata(path: str | Path) -> dict:
    """Read only the ZIP end record and central directory, never compressed members."""
    source = Path(path)
    size = source.stat().st_size
    if size < 22 or size > MAX_ARCHIVE_SIZE:
        raise ValueError("ZIP size outside configured inspection bounds")
    with source.open("rb") as stream:
        tail_size = min(size, 65_557)
        stream.seek(size - tail_size)
        tail = stream.read(tail_size)
        eocd_pos = tail.rfind(EOCD)
        if eocd_pos < 0 or eocd_pos + 22 > len(tail):
            raise ValueError("ZIP end-of-central-directory record not found")
        _, disk, cd_disk, disk_entries, total_entries, cd_size, cd_offset, comment_len = struct.unpack_from(
            "<4s4H2IH", tail, eocd_pos
        )
        if disk != 0 or cd_disk != 0 or disk_entries != total_entries:
            raise ValueError("multi-disk ZIP archives are not supported")
        if total_entries == 0xFFFF or cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF:
            return {"format": "zip64", "complete": False, "entry_count": None, "members": [],
                    "warning": "ZIP64 archive detected; bounded ZIP64 central-directory parsing is not enabled"}
        if total_entries > MAX_ARCHIVE_ENTRIES:
            raise ValueError(f"ZIP has {total_entries} entries; limit is {MAX_ARCHIVE_ENTRIES}")
        if cd_size > MAX_CENTRAL_DIRECTORY:
            raise ValueError("ZIP central directory exceeds configured size limit")
        if cd_offset + cd_size > size or cd_size < total_entries * 46:
            raise ValueError("ZIP central directory bounds are invalid")
        stream.seek(cd_offset)
        central = stream.read(cd_size)
        if len(central) != cd_size:
            raise ValueError("short ZIP central directory read")

    members = []
    cursor = 0
    for _ in range(total_entries):
        if cursor + 46 > len(central) or central[cursor:cursor + 4] != CENTRAL:
            raise ValueError("invalid ZIP central directory entry")
        fields = struct.unpack_from("<4s6H3I5H2I", central, cursor)
        flags, method = fields[3], fields[4]
        compressed_size, uncompressed_size = fields[8], fields[9]
        name_len, extra_len, member_comment_len = fields[10], fields[11], fields[12]
        entry_end = cursor + 46 + name_len + extra_len + member_comment_len
        if name_len > MAX_NAME_BYTES or entry_end > len(central):
            raise ValueError("ZIP member name or entry exceeds configured bounds")
        raw_name = central[cursor + 46:cursor + 46 + name_len]
        name = raw_name.decode("utf-8" if flags & 0x800 else "cp437", errors="replace")
        normalized = name.replace("\\", "/")
        unsafe = (
            normalized.startswith("/")
            or normalized.startswith("//")
            or bool(re.match(r"^[A-Za-z]:", normalized))
            or any(part == ".." for part in normalized.split("/"))
        )
        members.append({
            "name": name, "compressed_size": compressed_size,
            "uncompressed_size": uncompressed_size, "method": method,
            "encrypted": bool(flags & 1), "unsafe_path": unsafe,
        })
        cursor = entry_end

    total_uncompressed = sum(item["uncompressed_size"] for item in members)
    suspicious_ratio = any(
        (item["compressed_size"] == 0 and item["uncompressed_size"] > 0)
        or (item["compressed_size"] > 0 and item["uncompressed_size"] / item["compressed_size"] > 1000)
        for item in members
    )
    return {
        "format": "zip", "complete": True, "entry_count": len(members),
        "total_uncompressed_size": total_uncompressed, "suspicious_ratio": suspicious_ratio,
        "unsafe_member_count": sum(item["unsafe_path"] for item in members),
        "members": members,
    }

def analyze_archives(root: str | Path, records) -> list[Evidence]:
    base = Path(root)
    evidence: list[Evidence] = []
    candidates = [r for r in records if Path(r.path).suffix.lower() in {".zip", ".apk", ".jar"}][:32]
    for record in candidates:
        path = base / record.path
        try:
            result = inspect_zip_metadata(path)
            evidence.append(Evidence("package_format", result["format"], record.path,
                                     f'{result["entry_count"]} ZIP directory entries; metadata-only inspection', 3))
            if not result["complete"]:
                evidence.append(Evidence("analysis_warning", "zip64_not_parsed", record.path, result["warning"], 0))
                continue
            if result["unsafe_member_count"]:
                evidence.append(Evidence("archive_warning", "unsafe_member_paths", record.path,
                                         f'{result["unsafe_member_count"]} absolute or parent-traversal member names found', 0))
            if result["suspicious_ratio"]:
                evidence.append(Evidence("archive_warning", "high_compression_ratio", record.path,
                                         "At least one central-directory entry has an extreme declared compression ratio; no extraction was attempted", 0))
            names = [item["name"].lower().replace("\\", "/") for item in result["members"]]
            engine_markers = [
                ("unity", ("unityplayer.dll", "gameassembly.dll", "globalgamemanagers", "resources.assets")),
                ("unreal", ("content/paks/", ".utoc", ".ucas", "ue4game")),
                ("godot", ("project.godot", ".pck")),
                ("renpy", ("renpy/", "archive.rpa", "script.rpyc")),
            ]
            for engine, markers in engine_markers:
                match = next((name for name in names if any(m in name for m in markers)), None)
                if match:
                    evidence.append(Evidence("engine", engine, record.path,
                                             f"Engine marker found in ZIP central directory: {match}", 3))
        except (OSError, ValueError, struct.error) as exc:
            evidence.append(Evidence("analysis_warning", "archive_metadata_unavailable", record.path,
                                     f"{type(exc).__name__}: {exc}", 0))

    for record in records:
        path = base / record.path
        suffix = path.suffix.lower()
        if suffix == ".rpa":
            try:
                with path.open("rb") as stream:
                    header = stream.read(128)
            except OSError:
                continue
            line = header.split(b"\n", 1)[0]
            if line.startswith((b"RPA-2.0 ", b"RPA-3.0 ")):
                version = line.split(b" ", 1)[0].decode("ascii", errors="replace")
                evidence.append(Evidence("engine", "renpy", record.path, "Ren'Py archive header", 4))
                evidence.append(Evidence("package_format", version.lower(), record.path,
                                         "Ren'Py archive format marker; archive not unpacked", 4))
        elif suffix == ".wad":
            try:
                with path.open("rb") as stream:
                    magic = stream.read(4)
            except OSError:
                continue
            if magic in {b"IWAD", b"PWAD"}:
                evidence.append(Evidence("package_format", magic.decode("ascii").lower(), record.path,
                                         "Doom WAD container signature; no extraction performed", 3))
    return evidence
