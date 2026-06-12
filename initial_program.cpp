/**
 * The seed policy (LRU): score each object by its most
 * recent access time; the cache evicts the smallest-scored (least-recently
 * accessed).
 *
 * This snippet does exactly two things:
 *   1. attach listeners to the features it reads
 *   2. define `score_fn` — that scores a SINGLE object in cache. 
 * These scores are used to rank eviction candidates and the object with 
 * the minimum numeric score is evicted.
 */

store_cfg.add_listeners(f_last_access, {vulcan::listeners::object::RollingWindow(1)});
auto score_fn = [&](const vulcan::feature_store &fs, int64_t obj_id) -> double {
  return static_cast<double>(fs.get_latest(f_last_access, obj_id));
};
