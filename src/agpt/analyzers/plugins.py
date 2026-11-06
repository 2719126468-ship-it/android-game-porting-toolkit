"""Opt-in entry-point plugin discovery."""
from __future__ import annotations

import json
from importlib.metadata import entry_points
from typing import Any

from agpt.models import GameInventory


def run_plugins(inventory: GameInventory) -> tuple[list[dict[str, Any]], list[str]]:
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        points = entry_points()
        selected = points.select(group="agpt.analyzers") if hasattr(points, "select") else points.get("agpt.analyzers", [])
    except Exception as exc:  # noqa: BLE001 - plugin metadata is external
        return results, [f"Could not enumerate analyzer plugins: {type(exc).__name__}: {exc}"]

    for point in selected:
        try:
            factory = point.load()
            plugin = factory() if isinstance(factory, type) else factory
            raw = plugin.analyze(inventory)
            # Validate serialization and isolate arbitrary plugin exceptions.
            normalized = json.loads(json.dumps(raw, ensure_ascii=False))
            results.append({"plugin": point.name, "result": normalized})
        except Exception as exc:  # noqa: BLE001 - third-party plugin boundary
            warnings.append(f"Analyzer plugin '{point.name}' failed: {type(exc).__name__}: {exc}")
    return results, warnings
