# DungeonRush Android reference build validation

Date: 2026-11-06

## Scope

This is a reproducible packaging smoke test for the pinned upstream Android reference project. It verifies that the legacy Android project can be assembled with a pinned toolchain and that the resulting APK contains both requested ARM ABIs.

It is **not** an AGPT-generated port. The upstream Android port already existed; AGPT uses it as a real-world build-system and packaging reference.

## Source and workflow

- Upstream Android project: [imrunning/DungeonRush_Android](https://github.com/imrunning/DungeonRush_Android)
- Pinned upstream commit: `c3f673683d956abd80abf43fc3ad7e4066841466`
- AGPT workflow commit: `9ea7229c6179475bc789073feec352d88fd27f9c`
- Workflow run: [DungeonRush APK packaging smoke #7](https://github.com/2719126468-ship-it/android-game-porting-toolkit/actions/runs/42228472437)
- Main CI: [CI #25 — 12/12 jobs successful](https://github.com/2719126468-ship-it/android-game-porting-toolkit/actions/runs/42228472416)

## Pinned toolchain

| Component | Version |
|---|---|
| Android SDK platform | API 28 |
| Android Build Tools | 28.0.3 |
| Android NDK | r21e / 21.4.7075529 |
| Gradle wrapper | 5.6 |
| Android Gradle Plugin | 3.5.0 |
| Java for SDK command-line tools | 17 |
| Java for legacy Gradle | 8 |

The workflow writes the selected NDK path to the reference project's `local.properties`, checks it against `ANDROID_NDK_HOME`, and verifies that the expected `ndk-build` executable is present before Gradle starts.

## Build result

<badge>Success</badge> The `:app:assembleDebug` task and post-build APK validation both completed successfully.

| Item | Verified result |
|---|---|
| APK filename | `app-debug.apk` |
| APK size | 15,171,268 bytes (about 14.47 MiB) |
| SHA-256 | `b1f63934033fb6ec952826232957a676a6715d06a9036b8cb7a236d7b7d4869c` |
| Application ID | `org.libsdl.app` |
| Minimum Android API | 16 |
| ABIs | `arm64-v8a`, `armeabi-v7a` |
| Native libraries | 16 total; 8 per ABI |

The eight native libraries in each ABI are:

- `libSDL2.so`
- `libSDL2_image.so`
- `libSDL2_mixer.so`
- `libSDL2_net.so`
- `libSDL2_ttf.so`
- `libhidapi.so`
- `libmain.so`
- `libmpg123.so`

The APK manifest check confirmed package ID `org.libsdl.app`, min SDK 16, and both native ABIs.

The workflow uploaded only the validation report, badging output, and native-library listing as artifact `dungeonrush-apk-packaging-report` (artifact ID `13505699842`). [Open the report artifact](https://github.com/2719126468-ship-it/android-game-porting-toolkit/actions/runs/42228472437/artifacts/13505699842).

## What this does not prove

- No emulator or physical-device installation was performed.
- No game launch, touch/input, audio, save/load, rendering, or performance test was performed.
- The build does not prove that AGPT can automatically convert a desktop game into a playable Android game.
- The resulting APK was not published because the original game README identifies mixed asset licensing and explicitly warns that some audio, bitmap, and font rights are unknown.

The upstream project README describes the source code as GPL, but separately warns against reusing certain non-code assets. Keep the APK private unless the rights to every bundled asset are resolved.

## Next acceptance gate

1. Run an installation and launch test on a real Android device or emulator.
2. Confirm that the activity reaches the game rather than exiting or showing a black screen.
3. Test touch controls, orientation, audio, and save behavior.
4. Capture basic frame-time and memory observations.
5. Keep the Android reference-port result separate from future tests where AGPT itself produces the Android project or APK.
