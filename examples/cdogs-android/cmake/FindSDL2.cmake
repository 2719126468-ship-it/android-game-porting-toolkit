# FindSDL2.cmake - target-aware SDL2 resolver for the pinned AGPT build.
if(TARGET SDL2::SDL2)
    set(SDL2_FOUND TRUE)
    set(SDL2_INCLUDE_DIRS
        "${AGPT_SDL2_SOURCE_DIR}/include"
        "${SDL2_BINARY_DIR}/include"
        "${SDL2_BINARY_DIR}/include/SDL2"
        "${SDL2_BINARY_DIR}/include-config-$<LOWER_CASE:$<CONFIG>>/SDL2")
    set(SDL2_LIBRARIES SDL2::SDL2)
else()
    set(SDL2_FOUND FALSE)
endif()
