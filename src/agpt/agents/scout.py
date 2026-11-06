from __future__ import annotations

from agpt.models import GameInventory
from agpt.scanner import MAX_FILES, scan_game


class ScoutAgent:
    """Collect read-only evidence about a game directory."""

    name = "scout"

    def run(self, source_path: str, *, max_files: int = MAX_FILES) -> GameInventory:
        return scan_game(source_path, max_files=max_files)
