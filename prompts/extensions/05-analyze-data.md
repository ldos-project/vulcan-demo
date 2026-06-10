# Extension: Analyze the Data (LLM as Scientist)

## Idea

Let the LLM study the workload before writing a policy. Two approaches:

## Part 1: Static Analysis (inject into prompt)

Precompute trace statistics and include them in every prompt:

```
Workload: 337,644 unique objects, 3.2M requests
Object sizes: min=64B, median=4KB, max=2MB
Top 1% of objects account for ~45% of requests
23% of objects accessed exactly once
Cache size = 10% of working set (472MB)
```

Cheap to compute once. Gives the LLM concrete numbers to reason about. You could repeat this for each trace and hyperspecialize a policy per-trace.

## Part 2: LLM-Driven Analysis (multi-turn)

Before generating code, give the LLM a turn to ask questions:

1. Show basic stats
2. Ask: "What additional measurements would help you design a better policy?"
3. Compute what it asks for (e.g. by executing `np` or `pd` queries it gives you)
4. Repeat a couple of rounds
5. Then ask it to write a policy

This turns the LLM into a scientist doing EDA before forming a hypothesis.

## Implementation

You could probably add a `analyze_trace()` function that iterates over the trace reader and computes summary stats. Inject the output into `build_prompt()`. For Part 2, use the multi-turn capability of `LLM` — send stats, get questions, answer them, then request code.
