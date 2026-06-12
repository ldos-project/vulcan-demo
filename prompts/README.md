# Prompts

| File | Purpose |
|------|---------|
| [`EVICTION.md`](EVICTION.md) | The **LLM-facing prompt** for the constrained (libVulcan) track. `evolve.py` sends this verbatim each iteration, then splices the returned code into `evaluator.evaluate(cpp_source)` (which writes it to `LLMCode.h`, rebuilds, and scores byte hit rate on w106 @ 10%). |
| [`CREATE_EVOLVE.md`](CREATE_EVOLVE.md) | Bootstrap prompt for generating the evolution loop. |
| [`extensions/`](extensions/) | Independent ideas for improving the evolution loop. |

## Maintaining `EVICTION.md`

`EVICTION.md` is **pure prompt body** — every line is sent to the model, so keep
implementation/maintenance notes here, not in that file.

Internally this is wired as a libVulcan `rank_policy`
(`libcachesim/libvulcan/include/vulcan/rank.hpp`) with a fixed min-comparator and
`SampleSort` (5 candidates per eviction), set in
`libcachesim/libCacheSim/cache/eviction/cpp/VulcanEvolve.cpp`. The model never
needs that taxonomy — it only writes listener attachments + a `score_fn` lambda,
so the prompt body deliberately omits the "rank"/"value" framework terms.

The feature/listener list is derived from the auto-generated prompt. To
regenerate the canonical list if the C++ API changes:

```bash
PRINT_VULCAN_CACHE_PROMPT=1 build/run_algo.o traces/w106.oracleGeneral.bin.zst vulcanevolve 0.1
```
