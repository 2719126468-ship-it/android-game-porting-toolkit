#!/usr/bin/env python3
"""Prepare a pinned C-Dogs SDL 2.5.0 checkout for the AGPT Android build."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source anchor in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_cdogs_source(source: Path) -> None:
    cmake_root = (source / "CMakeLists.txt").read_text(encoding="utf-8")
    if 'set(VERSION "2.5.0")' not in cmake_root:
        raise SystemExit("Refusing to patch an unexpected C-Dogs source version; expected 2.5.0")

    root_cmake = source / "CMakeLists.txt"
    replace_once(
        root_cmake,
        '\t\tadd_definitions(-Winline -Werror)\n\t\tset(EXTRA_LIBRARIES "m")',
        '\t\tif(ANDROID)\n\t\t\tadd_definitions(-Winline)\n\t\telse()\n'
        '\t\t\tadd_definitions(-Winline -Werror)\n\t\tendif()\n'
        '\t\tset(EXTRA_LIBRARIES "m")',
        "Android Clang warning policy",
    )

    main_c = source / "src" / "cdogs.c"
    replace_once(
        main_c,
        "#include <assert.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n#define SDL_MAIN_HANDLED\n#include <SDL.h>",
        "#include <assert.h>\n#include <errno.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n"
        "#if !defined(__ANDROID__)\n#define SDL_MAIN_HANDLED\n#endif\n"
        "#include <SDL.h>\n"
        "#if defined(__ANDROID__)\n#include <SDL_system.h>\n#include <unistd.h>\n#endif",
        "Android SDL entry-point header",
    )

    replace_once(
        main_c,
        "\tsrand((unsigned int)time(NULL));\n\tLogInit();\n\n\tPrintTitle();\n\n#ifdef __EMSCRIPTEN__",
        "\tsrand((unsigned int)time(NULL));\n\tLogInit();\n\n\tPrintTitle();\n\n"
        "#ifdef __ANDROID__\n"
        "\t/* SDLActivity extracts bundled game data into this private directory. */\n"
        "\tconst char *internalStoragePath = SDL_AndroidGetInternalStoragePath();\n"
        "\tif (internalStoragePath == NULL || chdir(internalStoragePath) != 0)\n"
        "\t{\n"
        "\t\tfprintf(stderr, \"Could not enter Android private storage: %s\\n\", strerror(errno));\n"
        "\t\tLogTerminate();\n"
        "\t\treturn EXIT_FAILURE;\n"
        "\t}\n"
        "\tif (SDL_setenv(\"XDG_CONFIG_HOME\", internalStoragePath, 1) != 0)\n"
        "\t{\n"
        "\t\tfprintf(stderr, \"Could not set Android config directory: %s\\n\", SDL_GetError());\n"
        "\t\tLogTerminate();\n"
        "\t\treturn EXIT_FAILURE;\n"
        "\t}\n"
        "#endif\n\n"
        "#ifdef __EMSCRIPTEN__",
        "Android app-private storage bootstrap",
    )

    replace_once(
        main_c,
        "#ifndef __EMSCRIPTEN__\n"
        "\tconst int sdlFlags = SDL_INIT_TIMER | SDL_INIT_AUDIO | SDL_INIT_VIDEO |\n"
        "\t\t\t\t\t\t SDL_INIT_HAPTIC | SDL_INIT_GAMECONTROLLER;\n"
        "#else\n"
        "\tconst int sdlFlags = SDL_INIT_AUDIO | SDL_INIT_VIDEO;\n"
        "#endif",
        "#if defined(__ANDROID__)\n"
        "\tconst int sdlFlags = SDL_INIT_TIMER | SDL_INIT_AUDIO | SDL_INIT_VIDEO |\n"
        "\t\t\t\t\t\t SDL_INIT_GAMECONTROLLER;\n"
        "#elif !defined(__EMSCRIPTEN__)\n"
        "\tconst int sdlFlags = SDL_INIT_TIMER | SDL_INIT_AUDIO | SDL_INIT_VIDEO |\n"
        "\t\t\t\t\t\t SDL_INIT_HAPTIC | SDL_INIT_GAMECONTROLLER;\n"
        "#else\n"
        "\tconst int sdlFlags = SDL_INIT_AUDIO | SDL_INIT_VIDEO;\n"
        "#endif",
        "Android SDL subsystem flags",
    )

    src_cmake = source / "src" / "CMakeLists.txt"
    replace_once(
        src_cmake,
        "add_executable(cdogs-sdl\n"
        "\t${CDOGS_SDL_SOURCES} ${CDOGS_SDL_HEADERS} ${CDOGS_SDL_EXTRA})",
        "if(ANDROID)\n"
        "\t# SDLActivity loads libmain.so and resolves the SDL_main symbol.\n"
        "\tadd_library(cdogs-sdl SHARED\n"
        "\t\t${CDOGS_SDL_SOURCES} ${CDOGS_SDL_HEADERS} ${CDOGS_SDL_EXTRA})\n"
        "\tset_target_properties(cdogs-sdl PROPERTIES OUTPUT_NAME main)\n"
        "else()\n"
        "\tadd_executable(cdogs-sdl\n"
        "\t\t${CDOGS_SDL_SOURCES} ${CDOGS_SDL_HEADERS} ${CDOGS_SDL_EXTRA})\n"
        "endif()",
        "Android SDL shared-library target",
    )


def copy_asset_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Required C-Dogs data directory is missing: {source}")
    shutil.copytree(source, destination, dirs_exist_ok=True)


def prepare_android_project(
    sdl_source: Path,
    cdogs_source: Path,
    output: Path,
    repository_root: Path,
) -> None:
    template = sdl_source / "android-project"
    if not (template / "app/src/main/java/org/libsdl/app/SDLActivity.java").is_file():
        raise SystemExit("Pinned SDL Android project template was not found")

    if output.exists():
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, output)

    app = output / "app"
    main = app / "src" / "main"
    assets = main / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    for folder in ("data", "dogfights", "doc", "graphics", "missions", "music", "sounds"):
        copy_asset_tree(cdogs_source / folder, assets / folder)

    licenses = assets / "licenses" / "cdogs-sdl"
    licenses.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "COPYING", "COPYING.txt", "LICENSE", "LICENSE.txt"):
        path = cdogs_source / name
        if path.is_file():
            shutil.copy2(path, licenses / name)
    for name in ("COPYING.GPL", "README_DATA.md", "README.md"):
        path = cdogs_source / "doc" / name
        if path.is_file():
            shutil.copy2(path, licenses / name)

    native_src = app / "jni" / "src"
    native_src.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repository_root / "examples/cdogs-android/CMakeLists.txt",
        native_src / "CMakeLists.txt",
    )
    shutil.copytree(
        repository_root / "examples/cdogs-android/cmake",
        native_src / "cmake",
        dirs_exist_ok=True,
    )

    java_dir = main / "java" / "com" / "agpt" / "cdogs"
    java_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repository_root / "examples/cdogs-android/CdogsActivity.java",
        java_dir / "CdogsActivity.java",
    )
    shutil.copy2(
        repository_root / "examples/cdogs-android/app.build.gradle",
        app / "build.gradle",
    )

    manifest = main / "AndroidManifest.xml"
    replace_once(
        manifest,
        'android:name="SDLActivity"',
        'android:name="com.agpt.cdogs.CdogsActivity"',
        "Android Activity manifest entry",
    )
    replace_once(
        manifest,
        'android:exported="true"',
        'android:exported="true"\n            android:screenOrientation="landscape"',
        "Android landscape orientation",
    )

    strings = main / "res" / "values" / "strings.xml"
    strings.write_text(
        '<resources>\n    <string name="app_name">C-Dogs SDL (AGPT)</string>\n</resources>\n',
        encoding="utf-8",
    )

    root_gradle = output / "build.gradle"
    gradle_text = root_gradle.read_text(encoding="utf-8").replace(
        "com.android.tools.build:gradle:8.1.1",
        "com.android.tools.build:gradle:8.6.1",
    )
    root_gradle.write_text(gradle_text, encoding="utf-8")

    wrapper = output / "gradle/wrapper/gradle-wrapper.properties"
    wrapper_text = wrapper.read_text(encoding="utf-8").replace(
        "gradle-8.1.1-bin.zip",
        "gradle-8.7-bin.zip",
    )
    wrapper.write_text(wrapper_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdogs-source", required=True, type=Path)
    parser.add_argument("--sdl-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[2]
    cdogs_source = args.cdogs_source.resolve(strict=True)
    sdl_source = args.sdl_source.resolve(strict=True)
    output = args.output.resolve()

    patch_cdogs_source(cdogs_source)
    prepare_android_project(sdl_source, cdogs_source, output, repository_root)
    print(f"Prepared C-Dogs SDL 2.5.0 Android project at {output}")


if __name__ == "__main__":
    main()
