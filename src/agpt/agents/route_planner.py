from __future__ import annotations

from agpt.models import GameInventory, RouteScore
from agpt.planner import score_routes


class RoutePlannerAgent:
    """Turn observed evidence into a traceable route-fit recommendation."""

    name = "route-planner"

    def run(self, inventory: GameInventory) -> tuple[list[RouteScore], str, str]:
        return score_routes(inventory)
