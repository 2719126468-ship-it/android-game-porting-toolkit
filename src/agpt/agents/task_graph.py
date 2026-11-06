"""Deterministic, plan-only task graph generation for Android game ports."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agpt.models import GameInventory
from agpt.planner import score_routes

_VALID_ROUTES = {"auto", "native", "compatibility", "hybrid"}
_APPROVAL_CAPABILITIES = {
    "human_confirmation",
    "write_project_files",
    "execute_build",
    "package_apk",
    "execute_runtime",
    "install_on_device",
    "launch_game",
    "device_interaction",
    "network_access",
}


def _task(
    task_id: str,
    title: str,
    description: str,
    phase: str,
    depends_on: tuple[str, ...],
    capabilities: tuple[str, ...],
    acceptance: tuple[str, ...],
) -> dict[str, Any]:
    """Create a task declaration; proposed capabilities are never granted here."""
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "phase": phase,
        "depends_on": list(depends_on),
        "required_capabilities": list(capabilities),
        "approval_required": any(item in _APPROVAL_CAPABILITIES for item in capabilities),
        "status": "planned",
        "acceptance_criteria": list(acceptance),
    }


def _validate_graph(tasks: list[dict[str, Any]]) -> None:
    """Reject duplicate IDs, missing dependencies, and cycles."""
    by_id = {task["id"]: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("Task graph contains duplicate task IDs")
    completed: set[str] = set()
    for task in tasks:
        for dependency in task["depends_on"]:
            if dependency not in by_id:
                raise ValueError(f"Task {task['id']} has unknown dependency: {dependency}")
            if dependency not in completed:
                raise ValueError(
                    f"Task graph is not topologically ordered: {task['id']} depends on {dependency}"
                )
        completed.add(task["id"])


def _route_tasks(route: str) -> list[dict[str, Any]]:
    if route == "native":
        return [
            _task(
                "inspect-native-build",
                "Inspect native source and build configuration",
                "Review available C/C++ source, engine boundaries, Android build files, "
                "dependencies, and target ABI/API evidence. Do not execute build scripts.",
                "reconnaissance",
                ("approve-route-selection",),
                ("read_source", "read_build_metadata"),
                ("Source availability and build entry points are documented.",),
            ),
            _task(
                "prepare-android-project",
                "Prepare an Android project proposal",
                "Generate or propose Android project files only after the user approves the "
                "target package, minimum API, ABI list, and source changes.",
                "project-preparation",
                ("inspect-native-build", "confirm-source-rights", "confirm-target-device"),
                ("write_project_files",),
                ("All generated files are confined to the AGPT project workspace.",),
            ),
            _task(
                "build-native-libraries",
                "Build native libraries with the Android NDK",
                "Run the selected build system in an isolated, bounded worker after explicit "
                "approval. Record toolchain versions, logs, ABI/API, and output hashes.",
                "build",
                ("prepare-android-project",),
                ("execute_build",),
                ("Every requested ABI produces validated native libraries and provenance.",),
            ),
            _task(
                "package-apk",
                "Assemble and inspect the APK",
                "Package only after native outputs and asset licensing checks pass. Verify "
                "manifest, minimum API, ABI coverage, package ID, and artifact hashes.",
                "packaging",
                ("build-native-libraries",),
                ("package_apk", "write_project_files"),
                ("APK manifest and requested ABI contents pass automated checks.",),
            ),
            _task(
                "install-and-launch",
                "Install and launch on a test device",
                "Install the APK and launch the game only after an explicit device-operation "
                "approval. Preserve install and launch logs.",
                "device-validation",
                ("package-apk",),
                ("install_on_device", "launch_game"),
                ("The app installs and reaches its expected first playable screen.",),
            ),
            _task(
                "gameplay-smoke-test",
                "Run gameplay smoke tests",
                "Manually verify rendering, touch/controller input, orientation, audio, "
                "save/load, stability, and basic performance on a supported device.",
                "gameplay-validation",
                ("install-and-launch",),
                ("device_interaction",),
                ("The test report records pass/fail results and reproducible observations.",),
            ),
        ]
    if route == "compatibility":
        return [
            _task(
                "inspect-compatibility-dependencies",
                "Inspect executable and runtime dependencies",
                "Review executable architecture, imported libraries, graphics APIs, and "
                "required runtime components without launching the game.",
                "reconnaissance",
                ("approve-route-selection",),
                ("read_source", "read_binary_metadata"),
                ("Known dependencies, architecture, and unresolved requirements are listed.",),
            ),
            _task(
                "select-compatibility-runtime",
                "Select a compatibility runtime",
                "Compare candidate runtimes against the detected APIs and target-device "
                "capabilities; selection remains a human decision.",
                "runtime-planning",
                ("inspect-compatibility-dependencies", "confirm-target-device"),
                ("human_confirmation",),
                ("A runtime and its limitations are explicitly approved by the user.",),
            ),
            _task(
                "prepare-compatibility-profile",
                "Prepare a compatibility profile",
                "Write a non-launching profile in the project workspace after approval. "
                "Do not download, install, or start a runtime automatically.",
                "project-preparation",
                ("select-compatibility-runtime", "confirm-source-rights"),
                ("write_project_files",),
                ("The profile records executable path, runtime choice, and disabled-by-default launch.",),
            ),
            _task(
                "launch-compatibility-runtime",
                "Launch under the selected runtime",
                "Execute the selected game/runtime only after explicit approval, with bounded "
                "resources and an isolated environment.",
                "device-validation",
                ("prepare-compatibility-profile",),
                ("execute_runtime", "launch_game"),
                ("The game reaches a usable screen and the launch log is retained.",),
            ),
            _task(
                "compatibility-gameplay-test",
                "Validate compatibility gameplay",
                "Check input, graphics, audio, saves, stability, and performance; record "
                "regressions and runtime-specific workarounds.",
                "gameplay-validation",
                ("launch-compatibility-runtime",),
                ("device_interaction",),
                ("A reproducible compatibility test report is recorded.",),
            ),
        ]
    if route == "hybrid":
        return [
            _task(
                "map-hybrid-module-boundaries",
                "Map native and compatibility module boundaries",
                "Identify components that can remain in the original runtime and components "
                "that may need Android-native replacements. This is analysis only.",
                "reconnaissance",
                ("approve-route-selection",),
                ("read_source", "read_build_metadata", "read_binary_metadata"),
                ("Each proposed boundary is tied to source or binary evidence and unknowns.",),
            ),
            _task(
                "review-hybrid-replacement-plan",
                "Review the module replacement proposal",
                "Present module boundaries, dependencies, risks, and test criteria for "
                "human approval before any implementation work.",
                "route-review",
                ("map-hybrid-module-boundaries", "confirm-source-rights"),
                ("human_confirmation",),
                ("The user approves, rejects, or revises each proposed replacement boundary.",),
            ),
            _task(
                "prepare-hybrid-workspace",
                "Prepare the hybrid integration workspace",
                "Create isolated project scaffolding and integration interfaces only after "
                "approval; leave original game files untouched.",
                "project-preparation",
                ("review-hybrid-replacement-plan", "confirm-target-device"),
                ("write_project_files",),
                ("The workspace is separate from the source tree and documents interface contracts.",),
            ),
            _task(
                "build-and-integrate-hybrid-modules",
                "Build and integrate approved modules",
                "Build approved Android-native components and integrate them with the "
                "compatibility side in a bounded, isolated worker.",
                "build",
                ("prepare-hybrid-workspace",),
                ("execute_build", "write_project_files"),
                ("Each module passes its own tests and integration checks.",),
            ),
            _task(
                "package-hybrid-apk",
                "Package and inspect the hybrid APK",
                "Assemble and inspect the package after all module checks and asset-rights "
                "checks pass.",
                "packaging",
                ("build-and-integrate-hybrid-modules",),
                ("package_apk", "write_project_files"),
                ("Manifest, ABI coverage, module inventory, and artifact hashes pass checks.",),
            ),
            _task(
                "validate-hybrid-gameplay",
                "Validate integrated hybrid gameplay",
                "Install and test the integrated app after explicit device approval; verify "
                "module hand-offs, input, graphics, audio, saves, and stability.",
                "gameplay-validation",
                ("package-hybrid-apk",),
                ("install_on_device", "launch_game", "device_interaction"),
                ("End-to-end tests pass and integration failures are documented.",),
            ),
        ]
    return []


def build_task_graph(
    inventory: GameInventory,
    *,
    project_id: str,
    preferred_route: str = "auto",
    route_override: str | None = None,
) -> dict[str, Any]:
    """Build a plan-only, dependency-ordered task graph from observed evidence.

    No task is executed and no capability is granted by generating this document.
    A user-selected route may override the heuristic recommendation, but the
    recommendation and confidence are retained in the plan.
    """
    if preferred_route not in _VALID_ROUTES:
        raise ValueError(f"Unsupported preferred route: {preferred_route}")
    if route_override is not None and route_override not in _VALID_ROUTES:
        raise ValueError(f"Unsupported route override: {route_override}")
    route_scores, recommendation, confidence = score_routes(inventory)
    requested = route_override if route_override not in {None, "auto"} else preferred_route
    selected_route = recommendation if requested == "auto" else requested

    tasks = [
        _task(
            "review-analysis-evidence",
            "Review analysis evidence and unknowns",
            "Inspect the scan report, detected engines, dependencies, architectures, and "
            "confidence gaps before choosing implementation work.",
            "preflight",
            (),
            ("read_source", "read_build_metadata", "read_binary_metadata"),
            ("Evidence and unresolved assumptions are understood by the reviewer.",),
        ),
        _task(
            "inspect-local-toolchain",
            "Inspect local toolchain availability",
            "Check installed SDK/NDK, compiler, runtime, and analysis-tool versions. "
            "This task reports availability only and does not install or update tools.",
            "preflight",
            (),
            ("inspect_local_toolchain",),
            ("Required and optional tools are listed with versions and missing components.",),
        ),
        _task(
            "confirm-source-rights",
            "Confirm source and asset authorization",
            "The project owner confirms the right to inspect, modify, build, and package "
            "the source code and every bundled asset.",
            "approval-gates",
            ("review-analysis-evidence",),
            ("human_confirmation",),
            ("Authorization scope and any excluded assets are recorded.",),
        ),
        _task(
            "confirm-target-device",
            "Confirm Android target requirements",
            "Review the project's target API and ABI settings against the intended devices; "
            "confirm any required changes before scaffolding or building.",
            "approval-gates",
            ("inspect-local-toolchain",),
            ("human_confirmation",),
            ("Minimum API, target API, ABI list, and test device are explicitly selected.",),
        ),
    ]

    if selected_route == "manual_review":
        tasks.append(
            _task(
                "choose-port-route",
                "Choose a porting route after manual review",
                "The evidence does not support a sufficiently confident automatic route choice. "
                "Compare native, compatibility, and hybrid options and select one manually.",
                "route-review",
                (
                    "review-analysis-evidence",
                    "inspect-local-toolchain",
                    "confirm-source-rights",
                    "confirm-target-device",
                ),
                ("human_confirmation",),
                ("A route is explicitly selected and its trade-offs are documented.",),
            )
        )
    else:
        tasks.append(
            _task(
                "approve-route-selection",
                "Review and approve the proposed route",
                f"Review the proposed {selected_route} route, heuristic score, evidence, "
                "and unresolved risks before implementation tasks are considered.",
                "route-review",
                (
                    "review-analysis-evidence",
                    "inspect-local-toolchain",
                    "confirm-source-rights",
                    "confirm-target-device",
                ),
                ("human_confirmation",),
                ("The selected route and known limitations are explicitly approved.",),
            )
        )
        tasks.extend(_route_tasks(selected_route))

    _validate_graph(tasks)
    warnings = list(inventory.warnings)
    if confidence == "low" and requested != "auto":
        warnings.append(
            "The selected route overrides a low-confidence heuristic recommendation; "
            "review evidence and risks before implementation."
        )
    if inventory.truncated:
        warnings.append("The inventory was truncated; task planning may omit relevant files.")

    return {
        "schema_version": "1.0",
        "plan_type": "agpt-port-task-graph",
        "project_id": project_id,
        "source_path": inventory.root,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preferred_route": preferred_route,
        "route_override": route_override,
        "selected_route": selected_route,
        "recommended_route": recommendation,
        "route_confidence": confidence,
        "route_scores": [
            {"route": item.route, "score": item.score, "reasons": list(item.reasons)}
            for item in route_scores
        ],
        "execution_enabled": False,
        "tasks": tasks,
        "warnings": warnings,
        "safety": {
            "plan_only": True,
            "task_executor_available": False,
            "capabilities_are_proposals_not_grants": True,
            "source_mutation_authorized": False,
            "game_execution_authorized": False,
            "approval_required_capabilities": sorted(_APPROVAL_CAPABILITIES),
            "note": (
                "Generating this plan does not run tools, edit source files, install software, "
                "launch the game, or authorize any proposed capability."
            ),
        },
    }
