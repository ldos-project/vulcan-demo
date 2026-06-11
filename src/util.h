#include "../libcachesim/libCacheSim/include/libCacheSim.h"

#include <thread>
#include <string>
#include <unordered_set>

// Byte footprint of the trace = sum of unique object sizes (the working set).
long calculate_trace_footprint(reader_t *reader) {
    reset_reader(reader);
    long footprint = 0;
    long long n_req = 0;
    request_t req;
    std::unordered_set<uint64_t> unique_objects;

    while (read_trace(reader, &req) == 0) {
        n_req++;
        if (unique_objects.insert(req.obj_id).second) {
            footprint += req.obj_size;
            assert(req.obj_size > 0);
        }
    }
    reset_reader(reader);
    fprintf(stderr, "Trace footprint: %.3f MB (%.3fM objects) over %lld requests\n",
            footprint / (1024.0 * 1024.0), unique_objects.size() / 1000000.0, n_req);
    return footprint;
}

bool ends_with(const char *str, const char *suffix) {
    size_t len_str = strlen(str);
    size_t len_suffix = strlen(suffix);
    return len_str >= len_suffix && strcmp(str + len_str - len_suffix, suffix) == 0;
}

// Object size always matters, so the reader keeps obj_size as recorded.
reader_t *get_reader(const char *trace_path) {
    reader_init_param_t init_params = default_reader_init_params();
    if (ends_with(trace_path, ".csv")) return open_trace(trace_path, CSV_TRACE, &init_params);
    else if (ends_with(trace_path, ".zst")) return open_trace(trace_path, ORACLE_GENERAL_TRACE, &init_params);
    else {
        fprintf(stderr, "Unsupported trace format: %s\n", trace_path);
        assert(false);
    }
}
