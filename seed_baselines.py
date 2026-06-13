#!/usr/bin/env python3
"""
POST baselines.ndjson to the leaderboard server via /api/submit.
Run from anywhere after generating baselines.ndjson.

    python3 seed_baselines.py [--server http://leaderboard.dwivedula.dev]
"""
import os, sys, json, argparse, urllib.request, urllib.error

DEFAULT_SERVER = "http://leaderboard.dwivedula.dev"

SIZE_LABELS = {"0.01": "1pct", "0.03": "3pct", "0.1": "10pct"}

ALGO_DESCRIPTIONS = {
    "fifo":     "First-In First-Out — evict the oldest inserted object",
    "lru":      "Least Recently Used — evict the least recently accessed object",
    "lfu":      "Least Frequently Used — evict the object with lowest access count",
    "arc":      "Adaptive Replacement Cache — balances recency and frequency",
    "s3-fifo":  "S3-FIFO — small/main/ghost FIFO queues (OSDI 2023)",
    "clock":    "CLOCK — efficient LRU approximation with a reference bit",
    "sieve":    "SIEVE — simple and efficient eviction algorithm (NSDI 2024)",
}


def post(payload, server_url):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(f"{server_url}/api/submit", data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        print(f"  {payload['metadata']['heuristic_name']:12s}  MRR: {resp['mrr']:.4f}x  id={resp['id']}")
    except urllib.error.HTTPError as e:
        print(f"  {payload['metadata']['heuristic_name']:12s}  HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
    except Exception as e:
        print(f"  {payload['metadata']['heuristic_name']:12s}  failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--baselines", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines.ndjson"))
    args = parser.parse_args()

    if not os.path.exists(args.baselines):
        raise SystemExit(f"baselines.ndjson not found at {args.baselines} — generate it first (see README)")

    algos = {}
    with open(args.baselines) as f:
        for line in f:
            d     = json.loads(line)
            algo  = d["algo"]
            trace = os.path.basename(d["trace_name"]).split(".")[0]
            label = SIZE_LABELS.get(str(round(d["percent"], 2)))
            if not label:
                continue
            algos.setdefault(algo, {})[f"{trace}_{label}"] = {
                "obj_hit_rate":  round(d["obj_hit_rate"],  6),
                "byte_hit_rate": round(d["byte_hit_rate"], 6),
            }

    print(f"Submitting {len(algos)} baselines to {args.server} ...")
    for algo, results in algos.items():
        post({
            "metadata": {
                "submitter_name": "Baseline",
                "group_name":     "System",
                "heuristic_name": algo.upper(),
                "description":    ALGO_DESCRIPTIONS.get(algo, f"Classical: {algo}"),
                "algo_type":      "classical",
            },
            "results": results,
        }, args.server)


if __name__ == "__main__":
    main()
