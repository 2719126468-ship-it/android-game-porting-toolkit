# Agent model

The initial pipeline uses deterministic agents rather than requiring a hosted LLM:

- `ScoutAgent` inventories a source directory using bounded, read-only scanning.
- `RoutePlannerAgent` scores native, compatibility, and hybrid strategies from explicit evidence.
- `AnalysisOrchestrator` composes scanning, optional trusted analyzer plugins, and report generation.
- `build_task_graph` creates a deterministic, plan-only task graph with dependency ordering, acceptance criteria, and approval requirements.

The classes are intentionally small so an AI planner can be added later without changing the project manifest or analysis report format. The current task planner never executes tasks. It does not edit game files, execute imported binaries, apply patches, install runtimes, or launch games.

Future LLM-powered agents must return structured proposals with cited evidence, bounded tool permissions, explicit time/token budgets, and human approval before destructive operations or executable launch. Build and gameplay verification must remain independent from the agent that authored code.
