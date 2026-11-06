from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agpt.models import GameInventory


class PortEngine(Protocol):
    name: str

    def describe(self, inventory: GameInventory) -> list[str]:
        """Return a proposed workflow; must not execute source game files."""


@dataclass(frozen=True)
class NativeEngine:
    name: str = "native"

    def describe(self, inventory: GameInventory) -> list[str]:
        return [
            "Confirm source-code or legally reusable engine availability.",
            "Resolve Android NDK, ABI, and graphics API requirements.",
            "Port platform-specific code and adapt input/audio/window handling.",
            "Build with CMake/NDK, then validate on a physical Android device.",
        ]


@dataclass(frozen=True)
class CompatibilityEngine:
    name: str = "compatibility"

    def describe(self, inventory: GameInventory) -> list[str]:
        return [
            "Confirm a compatible Wine/Box64/FEX runtime exists for the target device.",
            "Select a graphics translation path supported by the target GPU and driver.",
            "Create an isolated prefix and explicit per-game environment profile.",
            "Run only after user approval; record startup, rendering, input, audio, and save tests.",
        ]


@dataclass(frozen=True)
class HybridEngine:
    name: str = "hybrid"

    def describe(self, inventory: GameInventory) -> list[str]:
        return [
            "Map executable modules, shared libraries, and process boundaries.",
            "Identify legally replaceable modules with stable interfaces.",
            "Keep the original runtime for unsupported components and replace only validated modules.",
            "Test ABI, memory ownership, graphics, input, audio, and save interoperability.",
        ]
