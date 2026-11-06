from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agpt.adapters import ndkbuild
from agpt.analyzers.source_build import analyze_source_build
from agpt.models import FileRecord
from agpt.scanner import scan_game
from agpt.planner import score_routes


class SourceBuildProbeTests(unittest.TestCase):
    def test_cmake_sdl_source_identifies_native_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CMakeLists.txt").write_text(
                "find_package(SDL2 REQUIRED)\nfind_package(SDL2_image REQUIRED)\n"
                "find_package(SDL2_mixer REQUIRED)\nadd_executable(game src/main.c)\n"
            )
            (root / "src").mkdir()
            (root / "src" / "main.c").write_text("#include <SDL.h>\nint main(void){return 0;}\n")
            inventory = scan_game(root)
            routes, recommendation, confidence = score_routes(inventory)
            self.assertEqual(recommendation, "native")
            self.assertIn(confidence, {"medium", "medium-high"})
            deps = {e.value for e in inventory.evidence if e.category == "dependency"}
            self.assertTrue({"sdl2", "sdl2_image", "sdl2_mixer"}.issubset(deps))
            self.assertEqual(routes[0].route, "native")

    def test_android_mk_application_mk_and_abi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Android.mk").write_text(
                "LOCAL_SHARED_LIBRARIES := SDL2 SDL2_image SDL2_mixer\n"
            )
            (root / "Application.mk").write_text(
                "APP_ABI := armeabi-v7a arm64-v8a\nAPP_PLATFORM := android-21\n"
            )
            records = [
                FileRecord("Android.mk", 80, "configuration", None),
                FileRecord("Application.mk", 60, "configuration", None),
            ]
            evidence = analyze_source_build(root, records)
            self.assertIn("ndk-build", {e.value for e in evidence if e.category == "build_system"})
            self.assertIn("arm64-v8a", {e.value for e in evidence if e.category == "target_abi"})
            self.assertIn("sdl2_mixer", {e.value for e in evidence if e.category == "dependency"})

    def test_source_probe_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = []
            for i in range(520):
                path = root / f"src{i:04}.c"
                path.write_text("#include <SDL.h>\n")
                records.append(FileRecord(path.name, 18, "other", None))
            evidence = analyze_source_build(root, records)
            self.assertIn("source_probe_truncated", {e.value for e in evidence if e.category == "analysis_limit"})


class NdkBuildAdapterTests(unittest.TestCase):
    def _project(self, root: Path):
        ndk = root / "ndk"
        (ndk / "build" / "cmake").mkdir(parents=True)
        (ndk / "build" / "cmake" / "android.toolchain.cmake").write_text("# test")
        (ndk / "source.properties").write_text("Pkg.Revision = 21.4.7075529\n")
        launcher = ndk / ("ndk-build.cmd" if os.name == "nt" else "ndk-build")
        launcher.write_text("@echo off\r\nexit /b 0\r\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n")
        if os.name != "nt":
            launcher.chmod(0o755)
        source = root / "jni"
        source.mkdir()
        (source / "Android.mk").write_text("include $(call all-subdir-makefiles)\n")
        (source / "Application.mk").write_text("APP_ABI := arm64-v8a\n")
        return ndk, source

    def test_build_outputs_are_hashed_and_provenanced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk, source = self._project(root)
            build = root / "build"

            def fake_run(command, **kwargs):
                libs_arg = next(a for a in command if a.startswith("NDK_LIBS_OUT="))
                libs = Path(libs_arg.split("=", 1)[1])
                target = libs / "arm64-v8a" / "libmain.so"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"fake-native-library")
                kwargs["capture_output"]
                from subprocess import CompletedProcess
                return CompletedProcess(command, 0, "ok", "")

            with mock.patch.object(ndkbuild, "discover_ndk", return_value=ndk), \
                 mock.patch.object(ndkbuild.subprocess, "run", side_effect=fake_run):
                result = ndkbuild.build_native(source, build, timeout=30)
            self.assertEqual(result["status"], "ndk_make_native_library_build_success")
            self.assertEqual(result["abi"], "arm64-v8a")
            self.assertEqual(result["ndk_version"], "21.4.7075529")
            self.assertEqual(len(result["libraries"][0]["sha256"]), 64)
            self.assertTrue(Path(result["provenance_path"]).is_file())

    def test_failed_build_leaves_owned_workspace_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk, source = self._project(root)
            build = root / "build"
            from subprocess import CompletedProcess
            with mock.patch.object(ndkbuild, "discover_ndk", return_value=ndk), \
                 mock.patch.object(ndkbuild.subprocess, "run",
                                   return_value=CompletedProcess(["ndk-build"], 1, "", "fail")):
                with self.assertRaises(ndkbuild.NdkMakeError):
                    ndkbuild.build_native(source, build, timeout=30)
            marker = build / "agpt-ndkbuild-project.json"
            self.assertTrue(marker.is_file())
            self.assertEqual(json.loads(marker.read_text())["abi"], "arm64-v8a")

    def test_build_dir_cannot_be_inside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ndk, source = self._project(root)
            with mock.patch.object(ndkbuild, "discover_ndk", return_value=ndk):
                with self.assertRaises(ndkbuild.NdkMakeError):
                    ndkbuild.build_native(source, source / "build")


if __name__ == "__main__":
    unittest.main()
