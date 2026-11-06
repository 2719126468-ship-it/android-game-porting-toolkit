import json
import tempfile
import unittest
from pathlib import Path

from agpt.cli import main
from agpt.scaffold.compatibility import generate_compatibility_profile
from agpt.scaffold.native import generate_native_scaffold


class ScaffoldTests(unittest.TestCase):
    def test_native_scaffold_contains_android_and_cmake_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "native"
            generate_native_scaffold(dest, "com.example.demo")
            self.assertTrue((dest / "app/src/main/cpp/CMakeLists.txt").is_file())
            self.assertTrue((dest / "app/src/main/AndroidManifest.xml").is_file())
            self.assertIn("arm64-v8a", (dest / "app/build.gradle.kts").read_text())

    def test_jni_symbol_escapes_underscores(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "native"
            generate_native_scaffold(dest, "com.example_game.demo")
            source = next(dest.glob("app/src/main/cpp/native-lib.cpp")).read_text()
            self.assertIn("Java_com_example_1game_demo_MainActivity_nativeStatus", source)

    def test_invalid_package_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_native_scaffold(Path(tmp) / "bad", "not-valid")

    def test_compat_profile_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_compatibility_profile(Path(tmp) / "profile", "../outside.exe")

    def test_compat_profile_rejects_windows_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_compatibility_profile(Path(tmp) / "profile", r"..\\outside.exe")

    def test_compat_profile_does_not_enable_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "profile"
            generate_compatibility_profile(dest, "game.exe")
            data = json.loads((dest / "compatibility.profile.json").read_text())
            self.assertFalse(data["runtime"]["launch_enabled"])

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_init_and_analyze(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "game"
            game.mkdir()
            (game / "game.exe").write_bytes(b"not-a-real-executable")
            project = root / "project"
            self.assertEqual(main(["init", str(project), "--name", "Demo", "--source", str(game)]), 0)
            self.assertEqual(main(["analyze", str(project)]), 0)
            self.assertTrue((project / "analysis/analysis.json").is_file())


if __name__ == "__main__":
    unittest.main()
