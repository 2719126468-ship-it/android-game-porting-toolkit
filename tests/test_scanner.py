import struct
import tempfile
import unittest
from pathlib import Path

from agpt.scanner import scan_game


def make_pe(machine=0x8664):
    data = bytearray(256)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x84, machine)
    data[0x90:0x90 + 12] = b"d3d11.dll\0\0\0"
    return bytes(data)


def make_elf(machine=183):
    data = bytearray(64)
    data[:4] = b"\x7fELF"
    data[4] = 2
    data[5] = 1
    struct.pack_into("<H", data, 18, machine)
    return bytes(data)


class ScannerTests(unittest.TestCase):
    def test_detects_pe_and_architecture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game.exe"
            path.write_bytes(make_pe())
            result = scan_game(tmp)
            self.assertEqual(result.records[0].kind, "windows_binary")
            self.assertEqual(result.records[0].architecture, "x86_64")

    def test_detects_elf_arm64(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "libgame.so").write_bytes(make_elf())
            result = scan_game(tmp)
            self.assertEqual(result.records[0].kind, "elf_binary")
            self.assertEqual(result.records[0].architecture, "arm64")

    def test_engine_hints_from_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "UnityPlayer.dll").write_bytes(make_pe())
            (root / "Game_Data").mkdir()
            (root / "Game_Data" / "globalgamemanagers").write_bytes(b"fixture")
            result = scan_game(root)
            self.assertIn("unity", {e.value for e in result.evidence if e.category == "engine"})

    def test_symlink_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "actual.txt").write_text("hello")
            try:
                (root / "linked.txt").symlink_to(root / "actual.txt")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            result = scan_game(root)
            self.assertEqual(result.scanned_files, 1)
            self.assertEqual(result.skipped_symlinks, 1)

    def test_scan_limit_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a.txt", "b.txt", "c.txt"):
                (root / name).write_text(name)
            result = scan_game(root, max_files=2)
            self.assertTrue(result.truncated)
            self.assertEqual(result.scanned_files, 2)

    def test_zero_file_limit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scan_game(tmp, max_files=0)

    def test_nonexistent_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            scan_game("/path/that/does/not/exist/agpt")


if __name__ == "__main__":
    unittest.main()
