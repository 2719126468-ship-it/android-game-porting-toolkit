from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agpt.models import AnalysisReport, GameInventory
from agpt.planner import score_routes


def build_report(inventory: GameInventory, plugin_results: list[dict[str, Any]] | None = None,
                 plugin_warnings: list[str] | None = None) -> AnalysisReport:
    routes, recommended, confidence = score_routes(inventory)
    engine_weights: Counter[str] = Counter()
    for item in inventory.evidence:
        if item.category == "engine" and item.value != "unknown":
            engine_weights[item.value] += item.weight
    total = sum(engine_weights.values())
    engines = [
        {"name": name, "evidence_weight": weight, "share": round(weight / total, 3) if total else 0.0}
        for name, weight in engine_weights.most_common()
    ]
    architectures = Counter(record.architecture for record in inventory.records if record.architecture)
    file_summary = Counter(record.kind for record in inventory.records)
    unknowns = [
        "Game engine and exact version are not guaranteed to be identified from filenames alone.",
        "Source-code availability and redistribution/modification rights were not checked.",
        "Runtime compatibility, GPU support, performance, and gameplay have not been tested.",
        "DRM, anti-cheat, online-service, and proprietary middleware dependencies are not assessed.",
    ]
    warnings = list(inventory.warnings)
    if inventory.truncated:
        warnings.append("File inventory reached its configured limit; analysis may be incomplete.")
    if plugin_warnings:
        warnings.extend(plugin_warnings)
    evidence = [
        {"category": item.category, "value": item.value, "source": item.source,
         "detail": item.detail, "weight": item.weight}
        for item in inventory.evidence
    ]
    if plugin_results:
        evidence.append({"category": "plugin_results", "value": "available", "source": "entry_points",
                         "detail": plugin_results, "weight": 0})
    return AnalysisReport(
        schema_version="1.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_path=inventory.root,
        detected_engines=engines,
        architectures=dict(architectures),
        file_summary=dict(file_summary),
        evidence=evidence,
        route_scores=[{"route": item.route, "score": item.score, "reasons": list(item.reasons)} for item in routes],
        recommended_route=recommended,
        confidence=confidence,
        unknowns=unknowns,
        warnings=warnings,
    )


def _markdown_cell(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\r", " ").replace("\n", " ").replace("`", "\\`")


def write_report(report: AnalysisReport, output_dir: str | Path) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "analysis.json"
    markdown_path = directory / "report.md"
    payload = report.to_dict()
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# AGPT Game Analysis", "", f"- **Source:** `{_markdown_cell(report.source_path)}`",
        f"- **Generated:** {report.generated_at}",
        f"- **Recommendation:** `{report.recommended_route}` ({report.confidence} confidence)",
        "", "## Route fit scores", "", "| Route | Score |", "|---|---:|",
    ]
    for item in report.route_scores:
        lines.append(f"| {item['route']} | {item['score']}/100 |")
    lines += ["", "## Detected engine hints", ""]
    if report.detected_engines:
        for engine in report.detected_engines:
            lines.append(f"- `{engine['name']}` — evidence weight {engine['evidence_weight']}")
    else:
        lines.append("- No known engine marker found.")
    lines += ["", "## Evidence", "", "| Category | Value | Source | Detail |", "|---|---|---|---|"]
    for evidence in report.evidence:
        detail = _markdown_cell(evidence["detail"])
        category = _markdown_cell(evidence["category"])
        value = _markdown_cell(evidence["value"])
        source = _markdown_cell(evidence["source"])
        lines.append(f"| {category} | `{value}` | `{source}` | {detail} |")
    lines += ["", "## Unknowns and limitations", ""]
    lines.extend(f"- {item}" for item in report.unknowns)
    if report.warnings:
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {item}" for item in report.warnings)
    lines += ["", "> Scores are heuristic fit indicators, not success probabilities or compatibility guarantees.", ""]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path
