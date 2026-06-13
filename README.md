# Leaderboard

0. Install Flask: `pip3 install flask`

1. Follow the setup steps in `master`'s README, then generate `baselines.ndjson` from the `master` checkout:
  ```bash
  for algo in fifo lru lfu arc s3-fifo clock sieve; do
    for trace in w86 w87 w89 w90 w93 w94 w99 w103 w105 w106; do
      for size in 0.01 0.03 0.1; do
        ./build/run_algo.o traces/$trace.oracleGeneral.bin.zst $algo $size >> baselines.ndjson
      done
    done
  done
  ```

2. `python3 seed_baselines.py --baselines /path/to/baselines.ndjson [--server http://leaderboard.dwivedula.dev]`

3. `python3 app.py`

## API

| Method | Path | |
|--------|------|-|
| `POST` | `/api/submit` | submit results |
| `GET`  | `/api/leaderboard` | `?sort=mrr&trace=w106&size=1pct` |
| `GET`  | `/api/submission/<id>` | full detail |
| `GET`  | `/` | dashboard |
