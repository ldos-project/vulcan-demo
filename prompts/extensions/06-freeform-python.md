# Extension: Free-Form Python Policies

## Idea

The main demo constrains the LLM to the Vulcan RANK interface — it writes only a `score_fn` plus listener attachments. Drop the guardrails: let it evolve a full free-form Python eviction policy - since the policies are no longer constrained and have no checker/DSL within which they are expressed, human review of synthesized code is more important. 

Starter code for this is available in the `python-demo` branch: here the LLM is responsible for writing an entire cache eviction policy (including state management, init, free, etc) as a bunch of `python` functions; the starter code uses `libcachesim-python` to run synthesized policies.

## Evaluation
- how performant (i.e. in terms of throughput) are LLM-generated heuristics?
- what sorts of bugs (if any) do they introduce?