# Setup instructions
1. Clone submodules: `git submodule update --init --recursive`
2. Install build deps (CMake, GLib, zstd): `./libcachesim/scripts/install_dependency.sh`
3. Create and activate a venv: `python3 -m venv .venv && source .venv/bin/activate`
4. Install Python deps: `pip3 install openai` (then set your API key in `llm.py`)
5. Build the evaluator: `mkdir build && cmake ../ && cd build && make -j`
6. Download traces:
    ```bash
    mkdir traces && cd traces
    for file in w105 w87 w86 w93 w89 w103 w94 w90 w106 w99; do
        wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/fast23_glcache/cloudphysics/$file.oracleGeneral.bin.zst;
    done
    cd ..
    ```
7. Run: `python test_evaluator.py` then `python evolve.py`
