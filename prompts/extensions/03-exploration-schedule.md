# Extension: Exploration Schedule

## Idea

Schedule exploration vs exploitation over iterations: high temperature + random parents early, low temperature + top-k parents late. Mirrors simulated annealing.

## Schedule

| Phase | Iterations | Parent selection | LLM temperature |
|-------|-----------|-----------------|-----------------|
| Explore | early | Random from all successful | 1.0–1.2 |
| Transition | middle | Weighted by score (softmax) | 0.7–0.9 |
| Exploit | late | Top 2–3 only | 0.3–0.5 |

## Implementation

Compute `progress = iteration / total_iters` and map to a temperature (e.g. 1.1 → 0.8 → 0.4). Pass to `llm.send(prompt, temperature=t)`. Adjust parent selection similarly.
