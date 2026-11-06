from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agpt.agents.task_graph import build_task_graph
from agpt.cli import main
from agpt.models import GameInventory


class TaskGraphTests(unittest.TestCase):
    def test_low_confidence_auto_plan_stops_at_manual_route_decision(self):
        inventory = GameInventory(root="/games/empty")
        plan = build_task_graph(inventory, project_id="empty-game")
        self.assertEqual(plan["selected_route"], "manual_review")
        self.assertFalse(plan["execution_enabled"])
        task_ids = {task["id"] for task in plan["tasks"]}
        self.assertIn("choose-port-route", task_ids)
        self.assertNotIn("build-native-libraries", task_ids)
        self.assertNotIn("launch-compatibility-runtime", task_ids)

    def test_explicit_native_route_builds_approval_gated_task_graph(self):
        inventory = GameInventory(root="/games/sdl-game")
        plan = build_task_graph(
            inventory, project_id="sdl-game", route_override="native"
        )
        self.assertEqual(plan["selected_route"], "native")
        self.assertIn("build-native-libraries", {task["id"] for task in plan["tasks"]})
        for task in plan["tasks"]:
            if set(task["required_capabilities"]) & {
                "write_project_files", "execute_build", "package_apk",
                "install_on_device", "launch_game", "device_interaction",
            }:
                self.assertTrue(task["approval_required"], task["id"])
        self.assertTrue(plan["safety"]["capabilities_are_proposals_not_grants"])
        self.assertFalse(plan["safety"]["source_mutation_authorized"])
        self.assertFalse(plan["safety"]["game_execution_authorized"])

    def test_graph_dependencies_are_known_and_topologically_ordered(self):
        plan = build_task_graph(
            GameInventory(root="/games/native"), project_id="native", route_override="native"
        )
        seen = set()
        for task in plan["tasks"]:
            self.assertTrue(set(task["depends_on"]).issubset(seen), task["id"])
            seen.add(task["id"])

    def test_compatibility_and_hybrid_task_graphs_are_topologically_ordered(self):
        for route in ("compatibility", "hybrid"):
            with self.subTest(route=route):
                plan = build_task_graph(
                    GameInventory(root=f"/games/{route}"),
                    project_id=route,
                    route_override=route,
                )
                seen = set()
                for task in plan["tasks"]:
                    self.assertTrue(set(task["depends_on"]).issubset(seen), task["id"])
                    seen.add(task["id"])
                self.assertTrue(plan["safety"]["plan_only"])

    def test_explicit_route_override_is_recorded_when_confidence_is_low(self):
        plan = build_task_graph(
            GameInventory(root="/games/unknown"),
            project_id="unknown",
            route_override="compatibility",
        )
        self.assertEqual(plan["selected_route"], "compatibility")
        self.assertEqual(plan["recommended_route"], "manual_review")
        self.assertTrue(any("overrides a low-confidence" in warning for warning in plan["warnings"]))

    def test_invalid_route_is_rejected(self):
        with self.assertRaises(ValueError):
            build_task_graph(GameInventory(root="/games/x"), project_id="x", route_override="unsafe")

    def test_cli_plan_writes_json_without_running_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            project = root / "project"
            self.assertEqual(
                main(["init", str(project), "--name", "Demo", "--source", str(source)]),
                0,
            )
            self.assertEqual(main(["plan", str(project)]), 0)
            path = project / "plans" / "port-task-graph.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(data["execution_enabled"])
            self.assertEqual(data["plan_type"], "agpt-port-task-graph")
            self.assertEqual(main(["plan", str(project)]), 2)
            self.assertEqual(main(["plan", str(project), "--force"]), 0)

    def test_cli_plan_refuses_output_inside_source_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            project = root / "project"
            self.assertEqual(
                main(["init", str(project), "--name", "Demo", "--source", str(source)]),
                0,
            )
            output = source / "must-not-write.json"
            self.assertEqual(
                main(["plan", str(project), "--output", str(output)]),
                2,
            )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
