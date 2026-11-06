from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_NAME = "agpt.project.json"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        # Keep Chinese/non-Latin project names usable while generating a stable filesystem ID.
        slug = "game-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return slug[:64].rstrip("-")


def create_project(project_dir: str | Path, *, name: str, source: str | Path,
                   preferred_route: str = "auto", min_sdk: int = 26) -> dict[str, Any]:
    if min_sdk < 23:
        raise ValueError("min_sdk must be 23 or higher")
    if preferred_route not in {"auto", "native", "compatibility", "hybrid"}:
        raise ValueError(f"Unsupported route: {preferred_route}")
    source_path = Path(source).expanduser()
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source game directory not found: {source_path}")
    target_dir = Path(project_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / MANIFEST_NAME
    if manifest_path.exists():
        raise FileExistsError(f"Project manifest already exists: {manifest_path}")

    manifest = {
        "schema_version": "1.0",
        "project_id": slugify(name),
        "name": name,
        "source_path": str(source_path.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preferred_route": preferred_route,
        "target": {"platform": "android", "architectures": ["arm64-v8a"], "min_sdk": min_sdk},
        "notes": "Source game files are referenced in place and are not copied into this project.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target_dir / "analysis").mkdir(exist_ok=True)
    (target_dir / "patches").mkdir(exist_ok=True)
    (target_dir / "reports").mkdir(exist_ok=True)
    return manifest


def load_project(project_dir: str | Path) -> tuple[dict[str, Any], Path]:
    path = Path(project_dir).expanduser() / MANIFEST_NAME
    if not path.is_file():
        raise FileNotFoundError(f"AGPT project manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "project_id", "name", "source_path", "target", "preferred_route"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Project manifest missing required fields: {', '.join(sorted(missing))}")
    if data["schema_version"] != "1.0":
        raise ValueError(f"Unsupported manifest schema: {data['schema_version']}")
    return data, path.parent
