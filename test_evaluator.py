from evaluator import score

with open("initial_program.py", "r") as f:
    LRU_CODE = f.read()

print("=== Train evaluator (LRU) ===")
result = score(LRU_CODE)
for k, v in result.items():
    print(f"  {k}: {v:.4f}")
assert 0.3 < result["w106_10pct"] < 0.9, f"unexpected: {result}"

print("\n=== Broken code (should return 0.0) ===")
broken = score("this is not valid python {{{")
print(f"  {broken}")
assert broken["w106_10pct"] == 0.0

print("\nAll tests passed.")