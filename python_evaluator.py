import os
import traceback
from libcachesim import PluginCache, TraceReader, TraceType, ReaderInitParam

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces")

TRAIN_TRACES = ["w106"]
TEST_TRACES = ["w100", "w101", "w102", "w103", "w104", "w105", "w106"]
TRAIN_SIZES = [0.1]
TEST_SIZES = [0.01, 0.03, 0.1]
SIZE_LABELS = {0.01: "1pct", 0.03: "3pct", 0.1: "10pct"}


def evaluate_heuristic(code: str, trace_name: str, cache_size: float) -> float:
    try:
        ns = {}
        exec(code, ns)
        init_hook = ns["init_hook"]
        hit_hook = ns["hit_hook"]
        miss_hook = ns["miss_hook"]
        eviction_hook = ns["eviction_hook"]
        remove_hook = ns["remove_hook"]
        free_hook = ns.get("free_hook", lambda data: None)
    except Exception as e:
        print(f"[evaluator] exec error: {e}")
        return 0.0

    trace_path = os.path.join(TRACE_DIR, f"{trace_name}.oracleGeneral.bin.zst")
    try:
        reader = TraceReader(
            trace_path,
            trace_type=TraceType.ORACLE_GENERAL_TRACE,
            reader_init_params=ReaderInitParam(ignore_obj_size=False),
        )
        cache = PluginCache(
            cache_size=cache_size,
            cache_init_hook=init_hook,
            cache_hit_hook=hit_hook,
            cache_miss_hook=miss_hook,
            cache_eviction_hook=eviction_hook,
            cache_remove_hook=remove_hook,
            cache_free_hook=free_hook,
            cache_name="Heuristic",
            reader=reader,
        )
        _, byte_miss_ratio = cache.process_trace(reader)
        return 1.0 - byte_miss_ratio
    except Exception as e:
        print(f"[evaluator] simulation error on {trace_name}@{cache_size}: {e}")
        traceback.print_exc()
        return 0.0


def score(code: str) -> dict:
    results = {}
    for trace in TRAIN_TRACES:
        for size in TRAIN_SIZES:
            key = f"{trace}_{SIZE_LABELS[size]}"
            results[key] = evaluate_heuristic(code, trace, size)
    return results


def score_full(code: str) -> dict:
    results = {}
    for trace in TEST_TRACES:
        for size in TEST_SIZES:
            key = f"{trace}_{SIZE_LABELS[size]}"
            results[key] = evaluate_heuristic(code, trace, size)
    return results
