cmake_minimum_required(VERSION 3.16)
project(agpt_orbit_snake LANGUAGES C)

find_package(SDL2 CONFIG REQUIRED)
add_executable(orbit-snake src/main.c)
target_link_libraries(orbit-snake PRIVATE SDL2::SDL2)
