#!/usr/bin/env python3
"""
Leaderboard Flask app.

Routes:
  GET  /                    → dashboard (filterable)
  GET  /api/leaderboard     → JSON list of all submissions
  POST /api/submit          → accept evaluation results (requires source_code for Vulcan heuristics)
  GET  /api/submission/<id> → full detail for one submission
"""

import os, sys, json, sqlite3, math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template, g, session, redirect, url_for
from functools import wraps

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "leaderboard.db")

TRACES = ["w86", "w87", "w89", "w90", "w93", "w94", "w99", "w103", "w105", "w106"]
SIZES  = ["1pct", "3pct", "10pct"]

# Admin password - change this to your desired password
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bethechange99$")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-hello-help-78273827982r3yfighjgzdz")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            submitter_name  TEXT NOT NULL,
            group_name      TEXT,
            heuristic_name  TEXT NOT NULL,
            description     TEXT,
            algo_type       TEXT DEFAULT 'vulcanevolve',
            submitted_at    TEXT NOT NULL,
            results_json    TEXT NOT NULL,
            source_code     TEXT,
            mrr             REAL,
            mrr_obj         REAL,
            mean_obj_hr     REAL,
            mean_byte_hr    REAL
        )
    """)
    # Add mrr_obj column if it doesn't exist (migration)
    try:
        db.execute("ALTER TABLE submissions ADD COLUMN mrr_obj REAL")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Add source_code column if it doesn't exist (migration)
    try:
        db.execute("ALTER TABLE submissions ADD COLUMN source_code TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# FIFO baselines (loaded from DB at startup)
# ---------------------------------------------------------------------------

FIFO_BASELINES: dict = {}

def load_fifo_baselines():
    """Load FIFO baselines from the first submission (should be FIFO)."""
    global FIFO_BASELINES
    try:
        db = sqlite3.connect(DB_PATH)
        row = db.execute("SELECT results_json FROM submissions WHERE id=1").fetchone()
        db.close()
        if row:
            FIFO_BASELINES = json.loads(row[0])
            print(f"[leaderboard] Loaded FIFO baselines from DB (submission ID 1): {len(FIFO_BASELINES)} scenarios")
        else:
            print("[leaderboard] WARNING: No submission with ID=1 found for FIFO baselines")
    except Exception as e:
        print(f"[leaderboard] ERROR loading FIFO baselines: {e}")


# ---------------------------------------------------------------------------
# MRR computation (server-side)
# ---------------------------------------------------------------------------

def compute_mrr(results: dict, metric: str = "byte_hit_rate") -> float | None:
    """Mean ratio to FIFO across all scenario keys present in both dicts."""
    if not FIFO_BASELINES:
        return None
    ratios = []
    for key, data in results.items():
        fifo_data = FIFO_BASELINES.get(key, {})
        fifo_val = fifo_data.get(metric, 0.0) if isinstance(fifo_data, dict) else 0.0
        if fifo_val > 0:
            submission_val = data.get(metric, 0.0) if isinstance(data, dict) else 0.0
            ratios.append(submission_val / fifo_val)
    return sum(ratios) / len(ratios) if ratios else None


def recompute_all_mrr():
    """Recompute MRR (both byte and obj) for all submissions using current FIFO baselines."""
    if not FIFO_BASELINES:
        print("[leaderboard] Cannot recompute MRR: FIFO baselines not loaded")
        return

    db = sqlite3.connect(DB_PATH)
    rows = db.execute("SELECT id, results_json FROM submissions").fetchall()
    for row in rows:
        sub_id, results_json = row
        results = json.loads(results_json)
        mrr_byte = compute_mrr(results, "byte_hit_rate")
        mrr_obj = compute_mrr(results, "obj_hit_rate")
        db.execute("UPDATE submissions SET mrr=?, mrr_obj=? WHERE id=?", (mrr_byte, mrr_obj, sub_id))
    db.commit()
    db.close()
    print(f"[leaderboard] Recomputed MRR (byte & obj) for {len(rows)} submissions")


def compute_summary_stats(results: dict) -> tuple[float, float]:
    obj_vals  = [v["obj_hit_rate"]  for v in results.values() if v.get("obj_hit_rate",  0) > 0]
    byte_vals = [v["byte_hit_rate"] for v in results.values() if v.get("byte_hit_rate", 0) > 0]
    mean_obj  = sum(obj_vals)  / len(obj_vals)  if obj_vals  else 0.0
    mean_byte = sum(byte_vals) / len(byte_vals) if byte_vals else 0.0
    return round(mean_obj, 6), round(mean_byte, 6)


def convert_to_central(timestamp_str: str) -> str:
    """Convert ISO timestamp to Central time for display."""
    if not timestamp_str:
        return ""
    try:
        central_tz = ZoneInfo("America/Chicago")
        dt = datetime.fromisoformat(timestamp_str)
        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to Central
        dt_central = dt.astimezone(central_tz)
        return dt_central.isoformat()
    except Exception:
        return timestamp_str


# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.post("/api/submit")
def api_submit():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "no JSON body"}), 400

    meta    = data.get("metadata", {})
    results = data.get("results",  {})
    source_code = data.get("source_code", "")

    # Validate required fields
    for field in ("submitter_name", "heuristic_name"):
        if not meta.get(field):
            return jsonify({"error": f"missing metadata field: {field}"}), 422

    # Validate source_code for Vulcan heuristics (required)
    algo_type = meta.get("algo_type", "vulcanevolve")
    if algo_type == "vulcanevolve":
        if not source_code or not source_code.strip():
            return jsonify({"error": "source_code is required for Vulcan heuristics"}), 422

    # Validate description length (max 100 characters)
    description = meta.get("description", "")
    if len(description) > 100:
        return jsonify({"error": "description must be 100 characters or less"}), 422

    # Validate that exactly 30 scenarios are present (10 traces × 3 sizes)
    expected_scenarios = {f"{trace}_{size}" for trace in TRACES for size in SIZES}
    provided_scenarios = set(results.keys())

    if len(provided_scenarios) != 30:
        return jsonify({"error": f"must provide exactly 30 scenarios (10 traces × 3 sizes), got {len(provided_scenarios)}"}), 422

    if provided_scenarios != expected_scenarios:
        missing = expected_scenarios - provided_scenarios
        extra = provided_scenarios - expected_scenarios
        error_msg = []
        if missing:
            error_msg.append(f"missing scenarios: {sorted(missing)}")
        if extra:
            error_msg.append(f"unexpected scenarios: {sorted(extra)}")
        return jsonify({"error": "; ".join(error_msg)}), 422

    mrr_byte       = compute_mrr(results, "byte_hit_rate")
    mrr_obj        = compute_mrr(results, "obj_hit_rate")
    mean_obj, mean_byte = compute_summary_stats(results)
    # Store in Central Time (Chicago)
    central_tz = ZoneInfo("America/Chicago")
    submitted_at   = datetime.now(central_tz).isoformat()

    db = get_db()
    cur = db.execute(
        """INSERT INTO submissions
           (submitter_name, group_name, heuristic_name, description,
            algo_type, submitted_at, results_json, source_code, mrr, mrr_obj, mean_obj_hr, mean_byte_hr)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            meta.get("submitter_name"),
            meta.get("group_name", ""),
            meta.get("heuristic_name"),
            meta.get("description", ""),
            algo_type,
            submitted_at,
            json.dumps(results),
            source_code,
            mrr_byte,
            mrr_obj,
            mean_obj,
            mean_byte,
        ),
    )
    db.commit()
    return jsonify({
        "id":            cur.lastrowid,
        "submitted_at":  submitted_at,
        "mrr":           mrr_byte,
        "mrr_obj":       mrr_obj,
        "mean_obj_hr":   mean_obj,
        "mean_byte_hr":  mean_byte,
    }), 201


@app.get("/api/leaderboard")
def api_leaderboard():
    """
    Query params:
      sort     = mrr | mrr_obj | mean_byte_hr | mean_obj_hr          (default: mrr)
      trace    = w106 (filter to only scenarios for that trace)
      size     = 1pct | 3pct | 10pct
      metric   = byte_hit_rate | obj_hit_rate               (for per-cell sort)
      limit    = int (default 100)
    """
    sort_by  = request.args.get("sort", "mrr")
    trace_f  = request.args.get("trace")
    size_f   = request.args.get("size")
    limit    = min(int(request.args.get("limit", 100)), 500)

    valid_sorts = {"mrr", "mrr_obj", "mean_byte_hr", "mean_obj_hr", "submitted_at"}
    if sort_by not in valid_sorts:
        sort_by = "mrr"

    order_dir = "DESC" if sort_by != "submitted_at" else "DESC"
    rows = get_db().execute(
        f"SELECT * FROM submissions ORDER BY {sort_by} {order_dir} LIMIT ?", (limit,)
    ).fetchall()

    out = []
    for row in rows:
        results = json.loads(row["results_json"])

        # optional trace / size filter: compute filtered mean byte_hit_rate
        if trace_f or size_f:
            filtered = {
                k: v for k, v in results.items()
                if (not trace_f or k.startswith(trace_f))
                and (not size_f or k.endswith(size_f))
            }
            byte_vals = [v["byte_hit_rate"] for v in filtered.values() if v.get("byte_hit_rate", 0) > 0]
            obj_vals  = [v["obj_hit_rate"]  for v in filtered.values() if v.get("obj_hit_rate",  0) > 0]
            display_byte = sum(byte_vals)/len(byte_vals) if byte_vals else 0
            display_obj  = sum(obj_vals) /len(obj_vals)  if obj_vals  else 0
        else:
            display_byte = row["mean_byte_hr"]
            display_obj  = row["mean_obj_hr"]
            filtered     = results

        out.append({
            "id":             row["id"],
            "submitter_name": row["submitter_name"],
            "group_name":     row["group_name"],
            "heuristic_name": row["heuristic_name"],
            "description":    row["description"],
            "algo_type":      row["algo_type"],
            "submitted_at":   convert_to_central(row["submitted_at"]),
            "mrr":            row["mrr"],
            "mrr_obj":        row["mrr_obj"],
            "mean_byte_hr":   display_byte,
            "mean_obj_hr":    display_obj,
            "scenario_results": filtered,
        })

    return jsonify(out)


@app.get("/api/submission/<int:sub_id>")
def api_submission_detail(sub_id: int):
    row = get_db().execute(
        "SELECT * FROM submissions WHERE id=?", (sub_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        **dict(row),
        "submitted_at": convert_to_central(row["submitted_at"]),
        "results": json.loads(row["results_json"]),
    })


@app.get("/api/fifo_baselines")
def api_fifo_baselines():
    return jsonify(FIFO_BASELINES)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/")
def dashboard():
    return render_template(
        "index.html",
        traces=TRACES,
        sizes=SIZES,
    )


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        if session.get('admin_authenticated'):
            return redirect(url_for('admin_dashboard'))
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Login</title>
            <style>
                :root {
                    --bg: #0f1117;
                    --surface: #1a1d27;
                    --border: #2e3248;
                    --accent: #6c63ff;
                    --text: #e2e4f0;
                    --text2: #8b8fa8;
                    --danger: #ff6b6b;
                }
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body {
                    background: var(--bg);
                    color: var(--text);
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                .login-box {
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    padding: 2rem;
                    width: 100%;
                    max-width: 400px;
                }
                h1 { font-size: 1.4rem; margin-bottom: 1.5rem; color: var(--accent); text-align: center; }
                .form-group { margin-bottom: 1rem; }
                .form-group label { display: block; margin-bottom: 4px; font-size: 0.85rem; color: var(--text2); }
                .form-group input {
                    width: 100%;
                    background: var(--bg);
                    color: var(--text);
                    border: 1px solid var(--border);
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 0.9rem;
                }
                .form-group input:focus { outline: 2px solid var(--accent); }
                .btn {
                    width: 100%;
                    padding: 10px;
                    border-radius: 5px;
                    border: none;
                    background: var(--accent);
                    color: #fff;
                    font-size: 0.9rem;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 0.5rem;
                }
                .btn:hover { filter: brightness(1.15); }
                .error {
                    background: rgba(255, 107, 107, 0.15);
                    border: 1px solid var(--danger);
                    color: var(--danger);
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 1rem;
                    font-size: 0.85rem;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h1>🔒 Admin Login</h1>
                <form method="POST">
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" name="password" required autofocus/>
                    </div>
                    <button type="submit" class="btn">Login</button>
                </form>
            </div>
        </body>
        </html>
        '''

    # POST request - validate password
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin_authenticated'] = True
        return redirect(url_for('admin_dashboard'))

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            :root {
                --bg: #0f1117;
                --surface: #1a1d27;
                --border: #2e3248;
                --accent: #6c63ff;
                --text: #e2e4f0;
                --text2: #8b8fa8;
                --danger: #ff6b6b;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                background: var(--bg);
                color: var(--text);
                font-family: 'Segoe UI', system-ui, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }
            .login-box {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                padding: 2rem;
                width: 100%;
                max-width: 400px;
            }
            h1 { font-size: 1.4rem; margin-bottom: 1.5rem; color: var(--accent); text-align: center; }
            .form-group { margin-bottom: 1rem; }
            .form-group label { display: block; margin-bottom: 4px; font-size: 0.85rem; color: var(--text2); }
            .form-group input {
                width: 100%;
                background: var(--bg);
                color: var(--text);
                border: 1px solid var(--border);
                border-radius: 5px;
                padding: 10px;
                font-size: 0.9rem;
            }
            .form-group input:focus { outline: 2px solid var(--accent); }
            .btn {
                width: 100%;
                padding: 10px;
                border-radius: 5px;
                border: none;
                background: var(--accent);
                color: #fff;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                margin-top: 0.5rem;
            }
            .btn:hover { filter: brightness(1.15); }
            .error {
                background: rgba(255, 107, 107, 0.15);
                border: 1px solid var(--danger);
                color: var(--danger);
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 1rem;
                font-size: 0.85rem;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔒 Admin Login</h1>
            <div class="error">Invalid password</div>
            <form method="POST">
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required autofocus/>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''


@app.get("/admin")
@require_admin
def admin_dashboard():
    return render_template("admin.html")


@app.post("/api/admin/logout")
def admin_logout():
    session.pop('admin_authenticated', None)
    return jsonify({"success": True})


@app.put("/api/admin/submission/<int:sub_id>")
@require_admin
def admin_update_submission(sub_id: int):
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "no JSON body"}), 400

    db = get_db()

    # Check if submission exists
    existing = db.execute("SELECT id FROM submissions WHERE id=?", (sub_id,)).fetchone()
    if not existing:
        return jsonify({"error": "submission not found"}), 404

    # Update the submission
    db.execute(
        """UPDATE submissions SET
           submitter_name = ?,
           group_name = ?,
           heuristic_name = ?,
           description = ?,
           algo_type = ?,
           source_code = ?
           WHERE id = ?""",
        (
            data.get("submitter_name", ""),
            data.get("group_name", ""),
            data.get("heuristic_name", ""),
            data.get("description", ""),
            data.get("algo_type", "vulcanevolve"),
            data.get("source_code", ""),
            sub_id,
        )
    )
    db.commit()

    return jsonify({"success": True, "id": sub_id})


@app.delete("/api/admin/submissions")
@require_admin
def admin_delete_submissions():
    data = request.get_json(force=True)
    if not data or "ids" not in data:
        return jsonify({"error": "missing 'ids' field"}), 400

    ids = data["ids"]
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids must be a non-empty list"}), 400

    db = get_db()
    placeholders = ",".join("?" * len(ids))
    db.execute(f"DELETE FROM submissions WHERE id IN ({placeholders})", ids)
    db.commit()

    return jsonify({"success": True, "deleted": len(ids)})


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    load_fifo_baselines()
    recompute_all_mrr()
    port = int(os.environ.get("PORT", 4000))
    app.run(host="0.0.0.0", port=port, debug=True)
