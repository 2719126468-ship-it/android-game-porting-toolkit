cmake_minimum_required(VERSION 3.22)
project(agpt_cdogs_android LANGUAGES C)

if(NOT ANDROID)
    message(FATAL_ERROR "This CMake wrapper must be configured with the Android NDK toolchain")
endif()

foreach(required_var AGPT_CDOGS_SOURCE_DIR AGPT_SDL2_SOURCE_DIR AGPT_SDL2_MIXER_SOURCE_DIR)
    if(NOT DEFINED ${required_var} OR NOT IS_DIRECTORY "${${required_var}}")
        message(FATAL_ERROR "${required_var} must point to a checked-out source directory")
    endif()
endforeach()

set(SDL_SHARED ON CACHE BOOL "Build SDL2 shared library" FORCE)
set(SDL_STATIC OFF CACHE BOOL "Disable SDL2 static library" FORCE)
set(SDL_TEST OFF CACHE BOOL "Disable SDL2 tests" FORCE)
set(SDL2_DISABLE_SDL2MAIN ON CACHE BOOL "Use the SDL Android entry point" FORCE)
set(SDL_INSTALL OFF CACHE BOOL "Do not install SDL2 in the Android build" FORCE)
add_subdirectory("${AGPT_SDL2_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/agpt-sdl2")

set(SDL2MIXER_BUILD_SHARED_LIBS ON CACHE BOOL "Build SDL2_mixer shared library" FORCE)
set(SDL2MIXER_VENDORED ON CACHE BOOL "Use vendored SDL_mixer codecs" FORCE)
set(SDL2MIXER_DEPS_SHARED OFF CACHE BOOL "Link codec dependencies statically" FORCE)
set(SDL2MIXER_SAMPLES OFF CACHE BOOL "Disable SDL_mixer samples" FORCE)
set(SDL2MIXER_CMD OFF CACHE BOOL "Disable external music command support" FORCE)
set(SDL2MIXER_INSTALL OFF CACHE BOOL "Do not install SDL2_mixer" FORCE)
add_subdirectory("${AGPT_SDL2_MIXER_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/agpt-sdl2-mixer")

if(NOT TARGET SDL2_mixer::SDL2_mixer)
    add_library(SDL2_mixer::SDL2_mixer ALIAS SDL2_mixer)
endif()

list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
set(BUILD_EDITOR OFF CACHE BOOL "The desktop OpenGL editor is not part of Android" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "Do not build desktop-oriented tests for Android" FORCE)
set(USE_SHARED_ENET OFF CACHE BOOL "Use bundled ENet source" FORCE)
set(CDOGS_DATA_DIR "./" CACHE STRING "Game data extracted into app-private storage" FORCE)

add_subdirectory("${AGPT_CDOGS_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/cdogs")
