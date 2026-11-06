from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agpt.agents.scout import ScoutAgent
from agpt.agents.task_graph import build_task_graph
from agpt import __version__
from agpt.adapters.doctor import doctor_dict
from agpt.core.project import create_project, load_project
from agpt.core.orchestrator import AnalysisOrchestrator
from agpt.scaffold.compatibility import generate_compatibility_profile
from agpt.scaffold.native import generate_native_scaffold


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agpt", description="AI-assisted PC-to-Android game porting toolkit")
    parser.add_argument("--version", action="version", version=f"AGPT {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a Port Project manifest")
    init.add_argument("project_dir")
    init.add_argument("--name", required=True)
    init.add_argument("--source", required=True, help="existing game directory; referenced in place")
    init.add_argument("--route", choices=["auto", "native", "compatibility", "hybrid"], default="auto")
    init.add_argument("--min-sdk", type=int, default=26)

    analyze = sub.add_parser("analyze", help="inspect the source directory for an existing Port Project")
    analyze.add_argument("project_dir")
    analyze.add_argument("--plugins", action="store_true", help="load installed trusted analyzer plugins")
    analyze.add_argument("--max-files", type=int, default=100_000)

    plan = sub.add_parser("plan", help="create a plan-only, approval-gated port task graph")
    plan.add_argument("project_dir")
    plan.add_argument("--route", choices=["auto", "native", "compatibility", "hybrid"], default=None,
                      help="override the project route preference")
    plan.add_argument("--output", help="optional task graph JSON output path")
    plan.add_argument("--max-files", type=int, default=100_000)

    inspect = sub.add_parser("inspect", help="inspect a game directory without creating a project")
    inspect.add_argument("game_dir")
    inspect.add_argument("--output", help="optional JSON report path")
    inspect.add_argument("--max-files", type=int, default=100_000)

    doctor = sub.add_parser("doctor", help="check optional local toolchain components")
    doctor.add_argument("--json", action="store_true", help="emit JSON")

    scaffold = sub.add_parser("scaffold", help="generate a starter workspace")
    scaffold_sub = scaffold.add_subparsers(dest="scaffold_type", required=True)
    native = scaffold_sub.add_parser("native", help="generate an Android NDK/CMake starter")
    native.add_argument("destination")
    native.add_argument("--package-id", required=True)
    compat = scaffold_sub.add_parser("compatibility", help="generate a compatibility profile only")
    compat.add_argument("destination")
    compat.add_argument("--executable", required=True)
    return parser


def _print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _run_analysis(source: str, output_dir: str | Path, max_files: int, plugins: bool = False) -> dict:
    result = AnalysisOrchestrator().run(source, output_dir, max_files=max_files, enable_plugins=plugins)
    return {"report": result.report.to_dict(), "json_path": str(result.json_path),
            "markdown_path": str(result.markdown_path), "plugin_count": result.plugin_count}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if getattr(args, "max_files", 1) < 1:
        print("agpt: error: --max-files must be at least 1", file=sys.stderr)
        return 2
    try:
        if args.command == "init":
            manifest = create_project(args.project_dir, name=args.name, source=args.source,
                                      preferred_route=args.route, min_sdk=args.min_sdk)
            _print_json({"created": True, "project_dir": str(Path(args.project_dir).resolve()), "manifest": manifest})
            return 0
        if args.command == "analyze":
            manifest, project_root = load_project(args.project_dir)
            result = _run_analysis(manifest["source_path"], project_root / "analysis", args.max_files, args.plugins)
            _print_json({"success": True, "project_id": manifest["project_id"],
                         "json_path": result["json_path"], "markdown_path": result["markdown_path"],
                         "recommended_route": result["report"]["recommended_route"],
                         "confidence": result["report"]["confidence"]})
            return 0
        if args.command == "plan":
            manifest, project_root = load_project(args.project_dir)
            inventory = ScoutAgent().run(manifest["source_path"], max_files=args.max_files)
            task_plan = build_task_graph(
                inventory,
                project_id=manifest["project_id"],
                preferred_route=manifest.get("preferred_route", "auto"),
                route_override=args.route,
            )
            output_path = (
                Path(args.output).expanduser()
                if args.output
                else project_root / "plans" / "port-task-graph.json"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(task_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _print_json({
                "success": True,
                "project_id": manifest["project_id"],
                "selected_route": task_plan["selected_route"],
                "recommended_route": task_plan["recommended_route"],
                "route_confidence": task_plan["route_confidence"],
                "task_count": len(task_plan["tasks"]),
                "approval_required_count": sum(
                    1 for task in task_plan["tasks"] if task["approval_required"]
                ),
                "execution_enabled": False,
                "plan_path": str(output_path.resolve()),
            })
            return 0
        if args.command == "inspect":
            output = Path(args.output) if args.output else Path.cwd() / "agpt-inspection"
            result = _run_analysis(args.game_dir, output, args.max_files)
            _print_json({"success": True, "json_path": result["json_path"],
                         "markdown_path": result["markdown_path"],
                         "recommended_route": result["report"]["recommended_route"],
                         "confidence": result["report"]["confidence"]})
            return 0
        if args.command == "doctor":
            data = doctor_dict()
            if args.json:
                _print_json(data)
            else:
                print("AGPT toolchain diagnostics")
                for tool in data["tools"]:
                    state = "FOUND" if tool["available"] else "not found"
                    location = f" — {tool['path']}" if tool["path"] else ""
                    print(f"[{state:9}] {tool['name']}{location} ({tool['required_for']})")
                print(data["note"])
            return 0
        if args.command == "scaffold" and args.scaffold_type == "native":
            path = generate_native_scaffold(args.destination, args.package_id)
            print(f"Native starter generated: {path.resolve()}")
            return 0
        if args.command == "scaffold" and args.scaffold_type == "compatibility":
            path = generate_compatibility_profile(args.destination, args.executable)
            print(f"Compatibility profile generated (no game was launched): {path.resolve()}")
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agpt: error: {exc}", file=sys.stderr)
        return 2
    print("agpt: unsupported command", file=sys.stderr)
    return 2
