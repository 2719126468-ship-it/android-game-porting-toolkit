# AGPT Orbit Snake — Android release sample

An original, asset-free C game built with SDL2. The same game logic is suitable for desktop SDL2 builds and Android NDK packaging.

## Android build used by CI

The release workflow checks out the official SDL2 source at `release-2.32.10`, generates an Android project from SDL's own `android-project` template, copies this game's C source, then builds with the Android NDK and Gradle.

The APK targets Android 8.1 (API 27) or newer and contains:
- `armeabi-v7a` (32-bit ARM)
- `arm64-v8a` (64-bit ARM)

The generated APK is uploaded as a GitHub Actions artifact on every CI build. A push of a tag named `orbit-snake-v*` also creates a GitHub Release with the APK and third-party notices.

## Controls

- Swipe anywhere on the game board to change direction.
- The on-screen directional pad at the bottom can also be tapped.
- Desktop builds support arrow keys or WASD.
- After a collision, tap the screen or press Space to restart.

## License

The game source in this directory is original AGPT code under the repository's MIT license. SDL2 is a separate dependency distributed under its zlib license; its original license is included in the packaged notices. No DungeonRush artwork, audio, fonts, or other third-party game assets are used.
