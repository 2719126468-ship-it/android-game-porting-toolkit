import json
import tempfile
import unittest
from pathlib import Path

from agpt.core.project import create_project, load_project
from agpt.planner import score_routes
from agpt.scanner import scan_game


class ProjectTests(unittest.TestCase):
    def test_create_and_load_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            project_dir = root / "project"
            create_project(project_dir, name="Test Game", source=source)
            manifest, location = load_project(project_dir)
            self.assertEqual(manifest["project_id"], "test-game")
            self.assertEqual(location, project_dir)
            self.assertTrue((project_dir / "analysis").is_dir())

    def test_non_latin_project_name_gets_stable_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            manifest = create_project(root / "project", name="测试游戏", source=source)
            self.assertTrue(manifest["project_id"].startswith("game-"))

    def test_existing_manifest_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            project = root / "project"
            create_project(project, name="Game", source=source)
            with self.assertRaises(FileExistsError):
                create_project(project, name="Game", source=source)

    def test_route_planner_returns_all_routes_and_bounded_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "UnityPlayer.dll").write_bytes(b"MZ")
            routes, recommended, confidence = score_routes(scan_game(root))
            self.assertEqual({route.route for route in routes}, {"native", "compatibility", "hybrid"})
            self.assertIn(recommended, {"native", "compatibility", "hybrid", "manual_review"})
            self.assertTrue(all(0 <= route.score <= 100 for route in routes))
            self.assertIn(confidence, {"low", "medium", "medium-high"})


if __name__ == "__main__":
    unittest.main()
