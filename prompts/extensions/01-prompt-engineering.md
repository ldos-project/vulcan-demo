# Extension: Cross-Domain Prompt Engineering

## Idea

Prompt the LLM to think about caching through the lens of a different domain (finance, ecology, physics). Novel analogies may produce novel heuristics that pure "cache eviction" prompting never surfaces.

## Things to Try

- **Finance**: Cache = portfolio. Each object is a position. Eviction = stop-loss. Frequency = dividend yield, recency = momentum, size = capital allocation.
- **Ecology**: Objects compete for limited space like species in a niche. Frequency = fitness, bursty objects = invasive species.
- **Physics**: Objects have "energy" that decays over time. Access = heating, eviction = picking the coldest object. Size = thermal mass.
- **Scheduling**: Eviction = scheduling. Which "job" has the lowest expected future value? Shortest-remaining-processing-time analogy.

## Implementation

Modify `build_prompt()` in `evolve.py` to prepend a domain framing before describing the hook interface. Compare best scores achieved across different framings with the same iteration budget.

## Evaluation

- Best score achieved per domain framing
- Build success rate (do cross-domain prompts confuse the LLM into broken code?)
- Diversity of generated policies across framings
