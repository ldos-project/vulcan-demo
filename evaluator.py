"""
C++ evaluator for the PolicySmith Vulcan demo.

`evaluate(cpp_source)` scores a Vulcan RANK evolve block (listeners + `score_fn`,
in the `initial_program.cpp` shape — no comparator/mechanism). Mechanism:

    write cpp_source -> libcachesim/.../include/LLMCode.h
    cmake --build build -j --target run_algo.o
    build/run_algo.o traces/w106.oracleGeneral.bin.zst vulcanevolve 0.1
    parse byte_hit_rate from the one-line JSON

Non-compiling / crashing code scores 0.0. Rebuild-in-place (no .so plugin).
"""
import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE_DIR = os.path.join(HERE, "traces")
BUILD_DIR = os.path.join(HERE, "build")
RUN_ALGO = os.path.join(BUILD_DIR, "run_algo.o")
LLMCODE_H = os.path.join(
    HERE, "libcachesim", "libCacheSim", "include", "LLMCode.h"
)

TRAIN_TRACES = ["w106"]
TEST_TRACES = ["w106", "w105", "w103"]
TRAIN_SIZES = [0.1]
TEST_SIZES = [0.01, 0.03, 0.1]
SIZE_LABELS = {0.01: "1pct", 0.03: "3pct", 0.1: "10pct"}

BUILD_TIMEOUT = 300   # seconds for the incremental rebuild
RUN_TIMEOUT = 120     # seconds per trace simulation


def _trace_path(trace_name: str) -> str:
    return os.path.join(TRACE_DIR, f"{trace_name}.oracleGeneral.bin.zst")


def _build() -> tuple[bool, str]:
    """Rebuild run_algo.o in place. Returns (ok, error_tail)."""
    try:
        proc = subprocess.run(
            ["cmake", "--build", BUILD_DIR, "-j", "--target", "run_algo.o"],
            cwd=HERE,
            capture_output=True,
            text=True,
            timeout=BUILD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        msg = "build timed out"
        print(f"[evaluator] {msg}")
        return False, msg
    if proc.returncode != 0:
        # Surface the last lines of the compiler error so the loop can feed
        # them back to the LLM on retry.
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        print(f"[evaluator] build failed:\n{tail}")
        return False, tail
    return True, ""


def _run(trace_name: str, cache_size: float) -> float:
    """Run one simulation; return byte hit rate, or 0.0 on crash/timeout."""
    trace_path = _trace_path(trace_name)
    if not os.path.exists(trace_path):
        print(f"[evaluator] missing trace: {trace_path}")
        return 0.0
    try:
        proc = subprocess.run(
            [RUN_ALGO, trace_path, "vulcanevolve", str(cache_size)],
            cwd=HERE,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print(f"[evaluator] run timed out on {trace_name}@{cache_size}")
        return 0.0
    if proc.returncode != 0:
        print(f"[evaluator] run crashed on {trace_name}@{cache_size} "
              f"(rc={proc.returncode})")
        return 0.0
    # run_algo prints exactly one JSON line; logging goes to stderr.
    for line in reversed(proc.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and "byte_hit_rate" in line:
            try:
                return float(json.loads(line)["byte_hit_rate"])
            except (ValueError, KeyError):
                break
    print(f"[evaluator] could not parse byte_hit_rate on {trace_name}@{cache_size}")
    return 0.0


def compile_check(cpp_source: str) -> tuple[bool, str]:
    """Write `cpp_source` to LLMCode.h and try to build. Returns (ok, error).

    Compilation IS validation for the C++ track — there is no cheap exec()
    check. The evolution loop uses the returned error to retry with the LLM.
    """
    with open(LLMCODE_H, "w") as f:
        f.write(cpp_source)
    return _build()


def evaluate(cpp_source: str, trace_name: str = "w106",
             cache_size: float = 0.1) -> float:
    """Compile `cpp_source` as the evolve block and return byte hit rate.

    Returns 0.0 if the code fails to compile or the simulation crashes.
    """
    with open(LLMCODE_H, "w") as f:
        f.write(cpp_source)
    ok, _ = _build()
    if not ok:
        return 0.0
    return _run(trace_name, cache_size)


def score(cpp_source: str) -> dict:
    """Train-set score: {trace_size: byte_hit_rate}. One build, many runs."""
    with open(LLMCODE_H, "w") as f:
        f.write(cpp_source)
    ok, _ = _build()
    if not ok:
        return {f"{t}_{SIZE_LABELS[s]}": 0.0
                for t in TRAIN_TRACES for s in TRAIN_SIZES}
    return {f"{t}_{SIZE_LABELS[s]}": _run(t, s)
            for t in TRAIN_TRACES for s in TRAIN_SIZES}


def score_full(cpp_source: str) -> dict:
    """Held-out score across the test traces/sizes. One build, many runs."""
    with open(LLMCODE_H, "w") as f:
        f.write(cpp_source)
    ok, _ = _build()
    if not ok:
        return {f"{t}_{SIZE_LABELS[s]}": 0.0
                for t in TEST_TRACES for s in TEST_SIZES}
    return {f"{t}_{SIZE_LABELS[s]}": _run(t, s)
            for t in TEST_TRACES for s in TEST_SIZES}
