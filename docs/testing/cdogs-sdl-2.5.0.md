# Candidate real-game validation: C-Dogs SDL 2.5.0

## Selection

- Upstream: https://github.com/cxong/cdogs-sdl
- Pinned candidate: release tag 2.5.0
- Genre/runtime: 2D top-down action game, C, SDL2
- Code license: GPL-2.0-or-later, with BSD-2-Clause portions
- Game-data licenses: CC0, CC-BY, and CC-BY-SA; preserve each asset's attribution and license record
- Existing Android reference: https://github.com/knepe/cdogs-sdl-android

C-Dogs is a complete PC game with source code and game data, so it is a more meaningful integration target than a minimal rendering sample. The Android reference is useful for understanding touch controls and packaging history, but it is not a modern build template.

## Compatibility findings

The upstream 2.5.0 CMake project requires SDL2, SDL2_mixer, and Nanopb. The desktop campaign editor is enabled by default and also introduces an OpenGL dependency; an Android build should disable the editor. The game bundles ENet source unless configured to use a system copy.

The existing Android repository uses a legacy Ant/ndk-build workflow and old Android toolchain assumptions. Its historical build script should not be executed as-is: it is not a current NDK/Gradle recipe and contains a hard-coded release-signing path. Use it as a source of porting reference only; generate a new debug-signing Android wrapper under AGPT control.

## Verified source-level Android blockers

These are confirmed from the pinned 2.5.0 source tree, not guesses about the old Android fork:

1. **SDL entry point:** `src/cdogs.c` defines `SDL_MAIN_HANDLED` before including SDL and then declares a normal `main()`. The SDL Android activity expects the SDL application entry point in the native library. The Android build must make the SDL entry-point mapping explicit rather than blindly retaining the desktop-only define.
2. **Native packaging target:** `src/CMakeLists.txt` currently creates `cdogs-sdl` with `add_executable()`. An SDLActivity-based Android package needs the application code linked into the shared native library loaded by the activity (commonly `libmain.so`), while the regular desktop target must remain unchanged.
3. **Game data access:** `src/cdogs/utils.c` resolves game data from the process working directory and `CDOGS_DATA_DIR`; C-Dogs opens many assets through ordinary filesystem APIs. APK assets therefore need a first-run deployment strategy into app-private storage, followed by a controlled working-directory/data-root setup before game initialization.
4. **Config/save location:** `src/cdogs/files.c` derives the config path from `XDG_CONFIG_HOME`, `CDOGS_CONFIG_DIR`, or the home directory and creates the directory tree. Android must direct this to the app's private files area; it must not write game state into shared external storage by default.
5. **Rendering:** `src/cdogs/window_context.c` requests an accelerated SDL renderer with target-texture support. This needs a real device check, plus a documented fallback/error path if the Android renderer cannot provide the required capability.
6. **Touch controls:** the core input model includes keyboard and joystick handling. A mobile UI needs an explicit touch-to-game-input bridge; merely packaging SDL does not create usable on-screen controls.

These points define the initial Android adapter patch set. Each patch should be isolated and reviewable, and must preserve the upstream desktop build.

## Proposed Android integration

1. Pin and analyze the upstream C-Dogs 2.5.0 source tree. Preserve the upstream license files and asset-level attribution.
2. Build the engine for arm64-v8a first, then add armeabi-v7a when dependencies and test coverage are ready.
3. Integrate current SDL2 and SDL2_mixer Android builds, Nanopb, and the bundled ENet code using a modern Android Gradle/NDK project. Disable the desktop editor.
4. Provide an SDL Android entry-point wrapper and a writable per-app configuration/save directory. Keep game data read-only in packaged assets unless the upstream data model requires otherwise.
5. Add an on-screen touch overlay for movement, fire, weapon switching, pause, and menu navigation. Preserve physical keyboard/controller input.
6. Build a debug APK in GitHub Actions; attach the APK, license notices, dependency versions, ABI manifest, hashes, and build report as a CI artifact.
7. Validate install, first launch, menu navigation, mission start, touch input, audio, save/config persistence, and sustained rendering on Android hardware before calling it playable.

## Acceptance criteria

- The APK is produced from the pinned upstream source and the AGPT-owned Android wrapper, not copied from another publisher's build.
- Both code and bundled assets have their required license notices and attribution.
- The package contains the requested ARM ABI, has a documented minimum Android API, and passes manifest/signature checks.
- The game reaches an actual playable mission; a successful compile or APK package alone is not a gameplay pass.
- No DRM, paid game assets, proprietary source, anti-cheat bypass, or third-party signing keys are included.

## Scope warning

This is the first representative SDL2/native-source port target. It does not establish compatibility with Unity, Unreal, Godot, DirectX-only games, .NET games, or arbitrary Windows executables. Those require separate engine/runtime adapters and independent test fixtures.
