# Evolving the entire cache eviction heuristic: in Python

## Instructions

1. Create a `python3` virtual environment: `python3 -m venv .venv`. 
2. Activate it: `source .venv/bin/activate`.
3. `pip3 install libcachesim` and then try to run `test_python_evaluator.py`. 
4. Download the traces used:

```bash
mkdir traces && cd traces
for file in w105 w87 w86 w93 w89 w103 w94 w90 w106 w99; do 
    wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/fast23_glcache/cloudphysics/$file.oracleGeneral.bin.zst; 
done
```