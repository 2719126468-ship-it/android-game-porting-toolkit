from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agpt.adapters import ghidra, ndk


class GhidraAdapterTests(unittest.TestCase):
    def test_discover_explicit_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "analyzeHeadless"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            self.assertEqual(ghidra.discover_ghidra(executable), executable.resolve())

    def test_discover_install_dir_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "support" / "analyzeHeadless"
            executable.parent.mkdir()
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            with mock.patch.dict(os.environ, {"GHIDRA_INSTALL_DIR": tmp}, clear=False):
                self.assertEqual(ghidra.discover_ghidra(), executable.resolve())

    def test_input_must_be_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ghidra.AdapterError):
                ghidra.analyze_binary(Path(tmp) / "missing.exe", executable="not-used")

    def test_timeout_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "sample.bin"
            binary.write_bytes(b"sample")
            with self.assertRaises(ValueError):
                ghidra.analyze_binary(binary, executable="fake-ghidra", timeout=1)

    def test_success_exports_json_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "sample.exe"
            binary.write_bytes(b"safe test input")
            output = Path(tmp) / "result.json"
            summary = {"schema_version": "1.0", "program": {"name": "sample"},
                       "functions": [], "functions_truncated": False}

            def fake_run(command, **kwargs):
                index = command.index("-postScript")
                Path(command[index + 2]).write_text(json.dumps(summary), encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            fake_executable = Path(tmp) / "analyzeHeadless"
            fake_executable.write_text("mock executable", encoding="utf-8")
            with mock.patch.object(ghidra.subprocess, "run", side_effect=fake_run):
                result = ghidra.analyze_binary(binary, output=output, executable=fake_executable)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["analysis"]["program"]["name"], "sample")
            self.assertEqual(result.input_sha256, ghidra._sha256(binary))
            self.assertTrue(Path(result.log_path).is_file())

    def test_nonzero_process_exit_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "sample.exe"
            binary.write_bytes(b"input")
            failed = subprocess.CompletedProcess(["ghidra"], 3, "", "bad import")
            fake_executable = Path(tmp) / "analyzeHeadless"
            fake_executable.write_text("mock executable", encoding="utf-8")
            with mock.patch.object(ghidra.subprocess, "run", return_value=failed):
                with self.assertRaises(ghidra.AdapterError):
                    ghidra.analyze_binary(binary, executable=fake_executable)


class NdkAdapterTests(unittest.TestCase):
    def _ndk(self, root: Path) -> Path:
        path = root / "ndk"
        toolchain = path / "build" / "cmake" / "android.toolchain.cmake"
        toolchain.parent.mkdir(parents=True)
        toolchain.write_text("# fake toolchain")
        (path / "source.properties").write_text("Pkg.Revision = 26.3.11579264\n")
        return path

    def test_discover_ndk_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._ndk(Path(tmp))
            self.assertEqual(ndk.discover_ndk(path), path.resolve())

    def test_invalid_abi_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk_path = self._ndk(root)
            source = root / "source"
            source.mkdir()
            (source / "CMakeLists.txt").write_text("project(sample)")
            with self.assertRaises(ValueError):
                ndk.build_native(source, root / "build", ndk_dir=ndk_path,
                                 cmake="cmake", abi="mips")

    def test_build_records_library_hash_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk_path = self._ndk(root)
            source = root / "source"
            source.mkdir()
            (source / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.22)\nproject(sample)")
            cmake = root / "cmake"
            cmake.write_text("# fake cmake")
            build_dir = root / "build"

            def fake_run(command, *, timeout, log_path, stage):
                if stage == "build":
                    lib = build_dir / "libsample.so"
                    lib.parent.mkdir(parents=True, exist_ok=True)
                    lib.write_bytes(b"fake-elf-shared-library")
                log_path.write_text(f"mock {stage}")
            with mock.patch.object(ndk, "_run", side_effect=fake_run):
                result = ndk.build_native(source, build_dir, ndk_dir=ndk_path,
                                          cmake=cmake, timeout=30)
            self.assertEqual(len(result.libraries), 1)
            self.assertEqual(len(result.libraries[0]["sha256"]), 64)
            provenance = json.loads(Path(result.provenance_path).read_text())
            self.assertEqual(provenance["status"], "native_library_build_success")
            self.assertEqual(provenance["abi"], "arm64-v8a")

    def test_build_directory_cannot_be_inside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk_path = self._ndk(root)
            source = root / "source"
            source.mkdir()
            (source / "CMakeLists.txt").write_text("project(sample)")
            with self.assertRaises(ndk.NdkBuildError):
                ndk.build_native(source, source / "build", ndk_dir=ndk_path, cmake="cmake")


if __name__ == "__main__":
    unittest.main()
