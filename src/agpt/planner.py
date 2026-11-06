"""Explainable route-fit scoring. Scores are triage heuristics, not probabilities."""
from __future__ import annotations

from collections import Counter

from agpt.models import GameInventory, RouteScore


def score_routes(inventory: GameInventory) -> tuple[list[RouteScore], str, str]:
    scores = {"native": 30, "compatibility": 30, "hybrid": 20}
    reasons: dict[str, list[str]] = {key: ["Neutral baseline; no project-specific evidence applied."] for key in scores}

    engines = {item.value for item in inventory.evidence if item.category == "engine"}
    apis = {item.value for item in inventory.evidence if item.category == "graphics_or_input_api"}
    source_languages = {item.value for item in inventory.evidence if item.category == "source_language"}
    build_systems = {item.value for item in inventory.evidence if item.category == "build_system"}
    kinds = Counter(record.kind for record in inventory.records)
    architectures = Counter(record.architecture for record in inventory.records if record.architecture)

    if kinds["windows_binary"]:
        scores["compatibility"] += 25
        reasons["compatibility"].append("PE/Windows binaries were detected; a Windows compatibility path is worth testing.")
        scores["hybrid"] += 10
        reasons["hybrid"].append("Windows binaries are present; module-level replacement may be possible after dependency analysis.")
    if "sdl" in engines:
        scores["native"] += 30
        reasons["native"].append("SDL library marker found; a native Android build path may be feasible if compatible source/engine code is available.")
    if source_languages.intersection({"c", "c++"}) and build_systems.intersection({"cmake", "ndk-build", "make"}):
        scores["native"] += 15
        reasons["native"].append("C/C++ source and a native build configuration were found; test an Android NDK build before considering source-port feasibility established.")
    if "ndk-build" in build_systems or "android-gradle" in build_systems:
        scores["native"] += 10
        reasons["native"].append("An Android-native build project is already present; validate its NDK/ABI/toolchain configuration and touch/input path.")
    if "godot" in engines:
        scores["native"] += 15
        reasons["native"].append("Godot package/runtime marker found; investigate engine version, export templates, and source availability.")
        scores["compatibility"] += 8
        reasons["compatibility"].append("A Windows executable may also be testable through a compatibility runtime.")
    if "renpy" in engines:
        scores["native"] += 20
        reasons["native"].append("Ren'Py data/runtime marker found; evaluate the engine's Android distribution workflow.")
    if "rpg_maker" in engines:
        scores["native"] += 18
        reasons["native"].append("RPG Maker data/runtime marker found; a compatible player/reimplementation may avoid general-purpose emulation.")
    if "unity" in engines:
        scores["compatibility"] += 15
        reasons["compatibility"].append("Unity Windows build marker found; running the original build is a practical first compatibility experiment.")
        scores["hybrid"] += 8
        reasons["hybrid"].append("Unity runtime and data are present; native replacement is version- and license-dependent.")
    if "unreal" in engines:
        scores["compatibility"] += 18
        reasons["compatibility"].append("Unreal package/runtime marker found; compatibility is a useful first experiment, subject to graphics requirements.")
        scores["hybrid"] += 8
        reasons["hybrid"].append("Unreal modules may have replaceable boundaries, but a full native port generally needs source and build access.")
    if "directx12" in apis or "directx11" in apis:
        scores["compatibility"] += 12
        reasons["compatibility"].append("DirectX 11/12 string marker found; verify the translation layer and target GPU driver before selecting a runtime.")
    if "directx9" in apis:
        scores["compatibility"] += 8
        reasons["compatibility"].append("DirectX 9 marker found; legacy graphics translation may be less demanding, but still requires device testing.")
    if "vulkan" in apis or "opengl" in apis:
        scores["native"] += 10
        reasons["native"].append("Vulkan/OpenGL marker found; confirm source access and Android API compatibility before a native port.")
    if architectures.get("x86") or architectures.get("x86_64"):
        scores["compatibility"] += 5
        reasons["compatibility"].append("x86-family executable architecture detected; compatibility translation is one possible route on ARM64 Android.")

    if inventory.truncated:
        for key in scores:
            reasons[key].append("Inventory was truncated at the configured file limit; results may be incomplete.")

    bounded = [RouteScore(key, max(0, min(100, value)), tuple(reasons[key])) for key, value in scores.items()]
    bounded.sort(key=lambda item: (-item.score, item.route))
    top = bounded[0]
    gap = top.score - bounded[1].score
    confidence = "low" if top.score < 45 or gap < 8 or "unknown" in engines else "medium"
    if top.score >= 70 and gap >= 15 and "unknown" not in engines:
        confidence = "medium-high"
    # A close score or unknown engine is not enough evidence to select a route.
    recommendation = "manual_review" if confidence == "low" else top.route
    return bounded, recommendation, confidence
