cmake_minimum_required(VERSION 3.12)
project(PolicySmithVulcanDemo)

# libcachesim (with its libvulcan submodule + the VulcanEvolve RANK policy) is
# vendored as a git submodule at ./libcachesim and built as a subproject.
set(LIBCACHE_SIM_DIR "${CMAKE_SOURCE_DIR}/libcachesim")
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${LIBCACHE_SIM_DIR}/cmake/Modules/")

set(CMAKE_BUILD_TYPE Debug)

find_package(GLib "2.40" REQUIRED)
include_directories(${GLib_INCLUDE_DIRS})

find_package(ZSTD)
include_directories(${ZSTD_INCLUDE_DIR})
if ("${ZSTD_LIBRARIES}" STREQUAL "")
    message(FATAL_ERROR "zstd not found")
endif()

include_directories(${LIBCACHE_SIM_DIR}/libCacheSim/include)
add_subdirectory(libcachesim)

# Single-policy runner: run_algo.o <trace> <algo> <percent>
add_executable(run_algo.o src/run_algo.cpp)
target_link_libraries(run_algo.o libCacheSim m ${GLib_LIBRARY} ${ZSTD_LIBRARIES})
