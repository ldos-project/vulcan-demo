You are designing a **cache eviction policy**. When the cache is full and a new
object must be inserted, the system scores a small **random sample of 5** cached
objects with your `score_fn` and **evicts the one with the lowest score**. Your
job is to write a scoring function that keeps the *valuable* objects (high score)
and sheds the rest, maximizing **byte hit rate**.

You write **exactly two things** and nothing else:

1. **Listener attachments** — for every feature you read in `score_fn`, attach a
   listener to it on **`store_cfg`** (the store config). A feature with no
   listener collects no data, and querying it is a runtime error (→ score 0.0).
2. **`score_fn`** — a stateless lambda scoring a *single* cached object. It
   **must be named exactly `score_fn`**; the harness wires it up by that name, so
   do not call `set_scoring_fn`, `set_comparator`, or `set_sorting_function`
   yourself.
   ```cpp
   auto score_fn = [&](const vulcan::feature_store &fs, int64_t obj_id) -> double {
       // ... read features via fs.get_*(...) ...
       return <score>;   // higher = keep, lower = evict
   };
   ```

The harness owns all eviction wiring: lowest score is evicted, and a random
subset of 5 objects is sampled per eviction. Do **not** write any cache hooks,
comparators, or sorting functions.

### Features

Per-object (queried with `obj_id`):
- `f_size` (i64) — object size in bytes
- `f_insertion_time` (i64) — logical time the object was inserted
- `f_last_access` (i64) — logical time of the object's most recent access
- `f_count` (i64) — number of accesses since insertion

Global (queried without `obj_id`):
- `f_ghost` (i64) — stream of recently evicted object IDs. Typical use: attach
  `global::RollingCount(n)` and call `fs.contains(f_ghost, obj_id)` to detect
  objects that were evicted and re-admitted (a strong "keep me" signal).
- `f_curr_time` (i64) — current logical time (request sequence number)

### Listeners and their query functions

Attach with `store_cfg.add_listeners(f_feature, {listener1, listener2, ...});`.
Global features take `vulcan::listeners::global::*`; per-object features take
`vulcan::listeners::object::*`.

Notes that prevent silent bugs and runtime errors (→ score 0.0):
- Percentile arguments `p` are in **[0, 1]** (e.g. `0.9`, not `90`).
- `EWMA` queries must use an alpha you attached — querying an unattached alpha is
  a runtime error. Alphas are matched to 3 decimal places.
- i64 query results are integers — **cast to `double` before dividing**
  (`(double)a / b`), or near-zero ratios truncate to 0.

**Per-object listeners** (queries take `obj_id`):
- `RollingWindow(int n)` — last n updates in order →
  `fs.get_latest(f, obj_id)`, `fs.get_kth_recent(f, obj_id, k)`,
  `fs.get_avg(f, obj_id)`, `fs.get_all(f, obj_id)`
- `EWMA({alpha, ...})` — one EWMA per alpha (higher alpha = faster adaptation) →
  `fs.get_ewma(f, obj_id, alpha)`
- `RollingPercentile(int n)` → `fs.get_percentile(f, obj_id, p)`
- `Average()` → `fs.get_avg(f, obj_id)`
- `MinMax()` → `fs.get_max(f, obj_id)`, `fs.get_min(f, obj_id)`
- `PopulationPercentile()` — tracks every object's latest value;
  `fs.get_percentile(f, p)` (**note: no `obj_id`**, `p` in [0,1]) returns the
  p-th percentile *value across all cached objects*. To rank an object, compare
  its own value against it, e.g.
  `fs.get_latest(f_size, obj_id) > fs.get_percentile(f_size, 0.9)`.
- `RollingCount(int n)` → `fs.get_count(f, obj_id, val)`, `fs.contains(f, obj_id, val)`

**Global listeners** (queries take no `obj_id`):
- `RollingWindow(int n)` → `fs.get_latest(f)`, `fs.get_kth_recent(f, k)`,
  `fs.get_avg(f)`, `fs.get_all(f)`
- `EWMA({alpha, ...})` → `fs.get_ewma(f, alpha)`
- `RollingPercentile(int n)` → `fs.get_percentile(f, p)`
- `Average()` → `fs.get_avg(f)`
- `MinMax()` → `fs.get_max(f)`, `fs.get_min(f)`
- `RollingCount(int n)` → `fs.get_count(f, val)`, `fs.contains(f, val)`

### Seed (LRU) — the shape your answer must take

```cpp
store_cfg.add_listeners(f_last_access, {vulcan::listeners::object::RollingWindow(1)});
auto score_fn = [&](const vulcan::feature_store &fs, int64_t obj_id) -> double {
  return static_cast<double>(fs.get_latest(f_last_access, obj_id));
};
```

This is LRU: score = most-recent access time, evict the lowest (least-recently
used). Improve on it — combine recency, frequency, size, and the global signals.
Return your answer as a single C++ code block with the listeners followed by
`score_fn`, and nothing else.
