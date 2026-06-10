# Extension: Multi-Objective Optimization

## Idea

The default loop optimizes only byte hit rate. Real caches also care about eviction speed and memory overhead. Evolve under multi-objective pressure.

## Objectives

- **Byte hit rate** (default): `1 - byte_miss_ratio`
- **Runtime**: wall-clock time of `process_trace()` — penalize slow policies
- **Memory**: size of the `data` structure — penalize bloated bookkeeping

## Implementation

Return multiple metrics from the evaluator, then combine into a single fitness:

```python
fitness = byte_hit_rate - 0.01 * runtime_sec
```

Or keep a Pareto front and show the LLM non-dominated solutions as inspiration.

## Evaluation

- Plot hit rate vs runtime tradeoff
- Do fast policies look structurally different from slow-but-accurate ones?
