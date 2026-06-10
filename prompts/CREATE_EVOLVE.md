# Create a file called `evolve.py`

Create `evolve.py` in this directory: an LLM-driven evolution loop for cache eviction policies.

## Existing modules (just import them)

- `llm.py` — `LLM` class. Call `llm.send(msg)` → returns `{"code": str, "full_response": str}`. Each instance maintains conversation history. Use `llm.reset()` to clear. Create a new `LLM()` per iteration.
- `evaluator.py` — `score(code: str)` → Dict `{"w106_10pct": float}` (obj hit rate, higher=better). Returns 0.0 on broken code.

## What the LLM must produce

A Python snippet with 5 functions: `init_hook(params)`, `hit_hook(data, req)`, `miss_hook(data, req)`, `eviction_hook(data, req)` → obj_id to evict, `remove_hook(data, obj_id)`. Available on `req`: `.obj_id`, `.obj_size`. Do NOT expose `.next_access_vtime` to the LLM (it's oracle info — defeats the purpose). You can provide the `initial_program.py` as the seed / initial program if needed. Only stdlib allowed.

The LLM prompt must stress that `eviction_hook` must return an obj_id present in `data` and also remove it from `data`.

## What to build

1. **`build_prompt(top_programs=None)`** — returns the LLM prompt string. Describes the hook interface, the goal (maximize byte hit rate), and optionally includes top-K `(code, score)` pairs as inspiration for improvement.

2. **`run_evolution(n_iters=5, samples_per_iter=2, n_retries=2)`** — the loop:
   - Each sample: new `LLM()`, build prompt (with top-K from population if any), generate code
   - Validate with `exec()` + check hooks exist; on failure, send error back to LLM and retry
   - Evaluate with `score(code)`; store `{code, score, iter}` in a list
   - Print progress per sample, best-so-far per iteration
   - Save final population to `results.json`

3. **`if __name__ == "__main__"` block** that runs it.

Keep it under ~100 lines total.