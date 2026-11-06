import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from agpt.analyzers.binary import parse_pe_imports, parse_elf_needed
from agpt.analyzers.archives import inspect_zip_metadata
from agpt.scanner import scan_game

def synthetic_pe():
    buf = bytearray(0x500)
    buf[:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, 0x80)
    buf[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", buf, 0x84, 0x8664, 1, 1700000000, 0, 0, 0xF0, 0x2022)
    opt = 0x98
    struct.pack_into("<H", buf, opt, 0x20B)
    struct.pack_into("<I", buf, opt + 108, 16)
    struct.pack_into("<II", buf, opt + 112 + 8, 0x1000, 40)
    sec = opt + 0xF0
    buf[sec:sec+8] = b".rdata\0\0"
    struct.pack_into("<IIII", buf, sec+8, 0x200, 0x1000, 0x200, 0x200)
    struct.pack_into("<IIIII", buf, 0x200, 0, 0, 0, 0x1040, 0)
    buf[0x240:0x24D] = b"KERNEL32.dll\0"
    return bytes(buf)

def synthetic_elf():
    buf = bytearray(0x500)
    buf[:4] = b"\x7fELF"
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    struct.pack_into("<Q", buf, 32, 64)
    struct.pack_into("<HH", buf, 54, 56, 2)
    struct.pack_into("<IIQQQQQQ", buf, 64, 1, 4, 0, 0, 0, len(buf), len(buf), 0x1000)
    struct.pack_into("<IIQQQQQQ", buf, 120, 2, 4, 0x200, 0x200, 0, 64, 64, 8)
    entries = [(5, 0x300), (10, 32), (1, 0), (0, 0)]
    for i, entry in enumerate(entries):
        struct.pack_into("<qQ", buf, 0x200 + i*16, *entry)
    buf[0x300:0x30A] = b"libc.so.6\0"
    struct.pack_into("<H", buf, 18, 62)
    return bytes(buf)

class BinaryMetadataTests(unittest.TestCase):
    def test_pe_import_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.exe"
            p.write_bytes(synthetic_pe())
            result = parse_pe_imports(p)
            self.assertEqual(result["machine"], "x86_64")
            self.assertEqual(result["import_dlls"], ["KERNEL32.dll"])

    def test_scanner_emits_dependency_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.exe"
            p.write_bytes(synthetic_pe())
            inventory = scan_game(tmp)
            self.assertIn(("binary_dependency", "KERNEL32.dll"),
                          {(e.category, e.value) for e in inventory.evidence})

    def test_pe_malformed_rva_fails_closed(self):
        raw = bytearray(synthetic_pe())
        struct.pack_into("<I", raw, 0x98 + 112 + 8, 0x7FFFFFFF)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.exe"
            p.write_bytes(raw)
            with self.assertRaises(ValueError):
                parse_pe_imports(p)

    def test_elf_dt_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "libsample.so"
            p.write_bytes(synthetic_elf())
            result = parse_elf_needed(p)
            self.assertEqual(result["machine"], "x86_64")
            self.assertEqual(result["needed"], ["libc.so.6"])

    def test_elf_bad_program_header_table_fails(self):
        raw = bytearray(synthetic_elf())
        struct.pack_into("<Q", raw, 32, 0xFFFFFFFF)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.so"
            p.write_bytes(raw)
            with self.assertRaises(ValueError):
                parse_elf_needed(p)

class EngineAndArchiveTests(unittest.TestCase):
    def test_godot_pck_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "game.pck").write_bytes(b"GDPC" + struct.pack("<IIII", 4, 4, 3, 1) + b"\0"*64)
            inventory = scan_game(root)
            values = {(e.category, e.value) for e in inventory.evidence}
            self.assertIn(("engine_version", "4.3.1"), values)
            self.assertIn(("engine", "godot"), values)

    def test_unity_project_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = root / "ProjectSettings"
            settings.mkdir()
            (settings / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.18f1\n")
            inventory = scan_game(root)
            values = {(e.category, e.value) for e in inventory.evidence}
            self.assertIn(("engine_version", "2022.3.18f1"), values)

    def test_unreal_build_version_and_pak_footer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "Engine" / "Build"
            build.mkdir(parents=True)
            (build / "Build.version").write_text(json.dumps({
                "MajorVersion": 5, "MinorVersion": 3, "PatchVersion": 2, "Changelist": 123456
            }))
            content = bytearray(1024)
            content[-32:-28] = struct.pack("<I", 0x5A6F12E1)
            struct.pack_into("<I", content, -28, 11)
            paks = root / "Content" / "Paks"
            paks.mkdir(parents=True)
            (paks / "pakchunk0-Windows.pak").write_bytes(content)
            inventory = scan_game(root)
            values = {(e.category, e.value) for e in inventory.evidence}
            self.assertIn(("engine_version", "5.3.2"), values)
            self.assertIn(("package_format", "unreal_pak_v11"), values)

    def test_zip_directory_metadata_without_extracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "game.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("Game_Data/globalgamemanagers", b"fixture")
                z.writestr("UnityPlayer.dll", b"not executable")
                z.writestr("../unsafe.txt", b"metadata only")
            metadata = inspect_zip_metadata(archive)
            self.assertEqual(metadata["entry_count"], 3)
            self.assertEqual(metadata["unsafe_member_count"], 1)
            inventory = scan_game(root)
            self.assertIn(("engine", "unity"),
                          {(e.category, e.value) for e in inventory.evidence})

    def test_zip_windows_drive_path_is_unsafe(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "drive.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("C:/outside.txt", b"x")
            self.assertEqual(inspect_zip_metadata(archive)["unsafe_member_count"], 1)

    def test_known_engine_does_not_keep_unknown_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = root / "ProjectSettings"
            settings.mkdir()
            (settings / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.10f1")
            inventory = scan_game(root)
            engine_values = {e.value for e in inventory.evidence if e.category == "engine"}
            self.assertIn("unity", engine_values)
            self.assertNotIn("unknown", engine_values)

    def test_zip_entry_limit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "many.zip"
            with zipfile.ZipFile(archive, "w") as z:
                for number in range(10005):
                    z.writestr(f"{number}.txt", b"x")
            with self.assertRaises(ValueError):
                inspect_zip_metadata(archive)

    def test_rpa_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archive.rpa").write_bytes(b"RPA-3.0 0000000000000100 ABCD\nrest")
            inventory = scan_game(root)
            self.assertIn(("package_format", "rpa-3.0"),
                          {(e.category, e.value) for e in inventory.evidence})

if __name__ == "__main__":
    unittest.main()
