# Extension: Embedding-Based Diversity Sampler

## Idea

Top-k example selection can cause the top programs to all be very similar leading to a local minima. Instead, use text embedding models (e.g. BERT style models) to embed each policy's code and select examples that are far apart in embedding space, ensuring the LLM sees structurally different approaches.

## How It Works

1. After each iteration, embed all successful policies (e.g., the LiteLLM API provided or a local embedding model)
2. When selecting parents: always include the best scorer, then greedily pick the most distant policy in embedding space from those already selected
3. Pass these diverse parents to `build_prompt()`

## Implementation Sketch

```python
import numpy as np

def cosine_distance(a, b):
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def sample_diverse_parents(population, embeddings, k=3):
    selected = [max(range(len(population)), key=lambda i: population[i]["score"])]
    for _ in range(k - 1):
        dists = [
            min(cosine_distance(embeddings[i], embeddings[j]) for j in selected)
            for i in range(len(population))
        ]
        selected.append(np.argmax(dists))
    return [population[i] for i in selected]
```

## Why This Might Work

- Top-k creates an echo chamber — the LLM sees the same logic N times and produces minor tweaks
- Diverse parents expose different algorithmic ideas (frequency-based, recency-based, size-aware, hybrid) in a single prompt

## Calling the embedding model
```
curl -X POST https://workshop.dwivedula.dev/v1/embeddings \
  -H "Authorization: Bearer sk-<<key-here>>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cohere-embed",
    "input": "Hello world"
  }'
```