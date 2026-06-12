"""
Tests for the C++ evaluator.

  - The seed LRU evolve block should score close to the `lru` byte hit rate on
    w106 @ 10% (seed ~0.757, lru ~0.760).
  - Non-compiling C++ should score 0.0.

Run from the final_demo/ directory (after a working `cmake -B build`):
    source ~/VULCAN/.venv/bin/activate && python test_evaluator.py
"""
from evaluator import evaluate

with open("initial_program.cpp", "r") as f:
    SEED_LRU = f.read()

print("=== Seed LRU evolve block ===")
seed = evaluate(SEED_LRU)
print(f"  w106_10pct: {seed:.4f}  (expect ~0.757; lru baseline 0.760)")
assert 0.70 < seed < 0.80, f"seed out of expected range: {seed}"

print("\n=== Non-compiling C++ (should return 0.0) ===")
broken = evaluate("this is not valid c++ {{{ ;;;")
print(f"  byte_hit_rate: {broken}")
assert broken == 0.0, f"broken code should score 0.0, got {broken}"

print("\nAll tests passed.")
