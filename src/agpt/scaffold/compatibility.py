from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath


def generate_compatibility_profile(destination: str | Path, executable: str) -> Path:
    if not executable.strip() or "\x00" in executable:
        raise ValueError("executable must be a non-empty relative path")
    normalized = executable.replace("\\", "/")
    relative = PurePosixPath(normalized)
    windows_path = PureWindowsPath(executable)
    if relative.is_absolute() or ".." in relative.parts or windows_path.is_absolute() or windows_path.drive:
        raise ValueError("executable must be a relative path inside the game directory")
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Destination is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    profile = {
        "schema_version": "1.0",
        "name": root.name,
        "runtime": {"preferred": "auto", "candidates": ["wine", "box64", "fex"], "launch_enabled": False},
        "game": {"executable": relative.as_posix(), "working_directory": "."},
        "graphics": {"api": "auto", "translation": "auto", "notes": "Select only after checking target GPU/driver support."},
        "input": {"profile": "touch-default", "controller": "optional"},
        "safety": {"execute_only_after_user_approval": True, "drm_or_anti_cheat_bypass": False},
        "limitations": ["This profile does not install or bundle a Windows runtime.", "Compatibility is not guaranteed.", "The game executable is not launched by AGPT."],
    }
    path = root / "compatibility.profile.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# AGPT Compatibility Profile\n\nThis is a declarative starter profile only. Install a compatible runtime separately, verify its license and device support, and launch the game manually after reviewing the configuration. AGPT v0.1.0 does not execute game binaries.\n",
        encoding="utf-8",
    )
    return root
