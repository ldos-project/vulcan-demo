# Extension: Workload Generalization

## Idea

A policy evolved on one trace may overfit. Evolve policies that generalize across multiple workloads and cache sizes.

## Things to Try

Evaluate on all 7 traces at 10% size. Define fitness as worst-case or average across all 7 entries instead of just `w106_10pct`. How much extra runtime does this add? Can you make the evaluator multiprocessed? Does that help?

## Evaluation

- See if generalist policies work well for cache sizes not tested during evolution (e.g. 0.1%, 1%, 3%)
- Compare generalist vs specialist policies (e.g. idea 05: per-trace data analysis)
