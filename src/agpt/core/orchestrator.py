from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agpt.agents.route_planner import RoutePlannerAgent
from agpt.agents.scout import ScoutAgent
from agpt.analyzers.plugins import run_plugins
from agpt.core.report import build_report, write_report
from agpt.models import AnalysisReport


@dataclass(frozen=True)
class AnalysisRun:
    report: AnalysisReport
    json_path: Path
    markdown_path: Path
    plugin_count: int


class AnalysisOrchestrator:
    """Deterministic v0.1 pipeline; LLM agents are intentionally not required."""

    def __init__(self) -> None:
        self.scout = ScoutAgent()
        self.route_planner = RoutePlannerAgent()

    def run(self, source_path: str, output_dir: str | Path, *, max_files: int = 100_000,
            enable_plugins: bool = False) -> AnalysisRun:
        inventory = self.scout.run(source_path, max_files=max_files)
        plugin_results, plugin_warnings = run_plugins(inventory) if enable_plugins else ([], [])
        report = build_report(inventory, plugin_results, plugin_warnings)
        json_path, markdown_path = write_report(report, output_dir)
        return AnalysisRun(report, json_path, markdown_path, len(plugin_results))
