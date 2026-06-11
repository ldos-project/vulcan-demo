/**
 * run_algo — single-policy cache simulator for the PolicySmith Vulcan demo.
 *
 * Runs ONE eviction algorithm (selected by name, e.g. "lru" or "vulcanevolve")
 * over a trace and prints a one-line JSON result with the byte hit rate.
 *
 * Object size ALWAYS matters: the cache is sized as a fraction of the trace's
 * byte footprint and the headline metric is byte hit rate.
 *
 * Usage:
 *   run_algo.o <trace_path> <algo> <percent>      # percent in (0,1)
 * Example:
 *   run_algo.o w106.oracleGeneral.bin.zst vulcanevolve 0.1
 */
#include "util.h"
// create_cache(): maps an algorithm name -> cache_t* (includes "vulcanevolve").
#include "../libcachesim/libCacheSim/bin/cachesim/cache_init.h"

int main(int argc, char *argv[]) {
  assert(argc == 4 && "./run_algo.o <trace_path> <algo> <percent>");
  const char *trace_path = argv[1];
  const char *algo = argv[2];
  double cache_percentage = std::stod(std::string(argv[3]));

  reader_t *reader = get_reader(trace_path);

  // Cache size = fraction of the trace's byte footprint (object size always counts).
  uint64_t cache_size = cache_percentage * calculate_trace_footprint(reader);

  // consider_obj_metadata = false: VulcanEvolve asserts on metadata accounting.
  cache_t *cache = create_cache(trace_path, algo, cache_size, /*params=*/nullptr,
                                /*consider_obj_metadata=*/false);

  auto start = std::chrono::high_resolution_clock::now();
  cache_stat_t *result = simulate_with_multi_caches(
      reader, &cache, 1, nullptr, 0.0, 0,
      static_cast<int>(std::thread::hardware_concurrency()), false, false);
  auto end = std::chrono::high_resolution_clock::now();
  double duration_sec = std::chrono::duration<double>(end - start).count();

  double miss_ratio      = (double)result[0].n_miss      / (double)result[0].n_req;
  double byte_miss_ratio = (double)result[0].n_miss_byte / (double)result[0].n_req_byte;

  printf(
      "{\"cache_name\":\"%s\",\"algo\":\"%s\",\"trace_name\":\"%s\","
      "\"cache_size\":%lu,\"percent\":%lf,\"n_miss\":%lu,\"n_req\":%ld,"
      "\"obj_hit_rate\":%.6f,\"byte_hit_rate\":%.6f,\"runtime_seconds\":%.6f}\n",
      result[0].cache_name, algo, trace_path, result[0].cache_size,
      cache_percentage, result[0].n_miss, result[0].n_req,
      1.0 - miss_ratio, 1.0 - byte_miss_ratio, duration_sec);

  free(result);
  cache->cache_free(cache);
  close_trace(reader);
}
