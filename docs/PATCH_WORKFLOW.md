# Human-approved patch workflow

AGPT patch proposals are review artifacts by default. Creating a proposal does not change the source game.

## 1. Prepare a proposal

Create a JSON specification containing a source-relative file path, its complete replacement text, and a rationale:

    {
      "file": "src/main.c",
      "replacement_text": "int main(void) { return 0; }\n",
      "rationale": "Example of a small, reviewable source change.",
      "evidence": ["The change is supported by the failing test."]
    }

Then generate the proposal:

    agpt patch propose ./projects/my-game ./patch-spec.json

The command prints a proposal ID and writes a JSON record under:

    ./projects/my-game/patches/proposals/<proposal-id>.json

Review the complete unified diff, rationale, evidence, target path, and before/after SHA-256 values. The original source remains unchanged at this stage.

## 2. Explicitly approve and apply

Only after reviewing the proposal, run:

    agpt patch apply ./projects/my-game <proposal-id> --approve

The approval flag is mandatory. Application is refused when the proposal ID does not match its target, rationale, and source hashes; when the source file has changed since proposal creation; when the replacement text does not match its recorded hash; or when the target is a symlink, binary, missing file, or unsafe path.

On success, AGPT replaces the target atomically using a temporary file in the same directory, preserves the original permission bits where supported, and records approval/application timestamps and status in the proposal JSON. A proposal can only be applied once.

## Boundaries

- Patch targets must be existing UTF-8 text files no larger than 1 MiB.
- A proposal is limited to a single file. It does not apply arbitrary shell commands or execute game code.
- The source path comes from the Port Project manifest; proposal paths are relative to that source root.
- The executor does not run compilers, CMake, Gradle, NDK, Ghidra, emulators, or the game.
- Keep a version-control commit or backup before approving changes. Build and gameplay validation remain separate steps.
