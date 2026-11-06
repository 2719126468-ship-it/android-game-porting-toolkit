"""Shared, dependency-free data models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    kind: str
    architecture: str | None = None


@dataclass(frozen=True)
class Evidence:
    category: str
    value: str
    source: str
    detail: str
    weight: int = 1


@dataclass
class GameInventory:
    root: str
    scanned_files: int = 0
    skipped_symlinks: int = 0
    truncated: bool = False
    records: list[FileRecord] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteScore:
    route: str
    score: int
    reasons: tuple[str, ...]


@dataclass
class AnalysisReport:
    schema_version: str
    generated_at: str
    source_path: str
    detected_engines: list[dict[str, Any]]
    architectures: dict[str, int]
    file_summary: dict[str, int]
    evidence: list[dict[str, Any]]
    route_scores: list[dict[str, Any]]
    recommended_route: str
    confidence: str
    unknowns: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_path(path: Path) -> str:
    """Return a stable display path without requiring the target to exist."""
    try:
        return str(path.resolve())
    except OSError:
        return str(path.absolute())
