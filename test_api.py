#!/usr/bin/env python3
"""
Unit tests for the leaderboard API submission endpoint.

Tests validate:
- All 30 traces (10 traces × 3 sizes) are present
- No extra traces are present
- Submitter name is required
- Description is limited to 100 characters
"""

import pytest
import json
import tempfile
import os
from app import app, init_db

# Expected traces: 10 traces × 3 sizes = 30 scenarios
EXPECTED_TRACES = ["w86", "w87", "w89", "w90", "w93", "w94", "w99", "w103", "w105", "w106"]
EXPECTED_SIZES = ["1pct", "3pct", "10pct"]
EXPECTED_SCENARIOS = [f"{trace}_{size}" for trace in EXPECTED_TRACES for size in EXPECTED_SIZES]


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True

    # Override the DB_PATH in the app module
    import app as app_module
    original_db_path = app_module.DB_PATH
    app_module.DB_PATH = db_path

    # Initialize the test database
    init_db()

    # Seed with FIFO baseline (required for MRR calculation)
    import sqlite3
    db = sqlite3.connect(db_path)
    fifo_results = {scenario: {"byte_hit_rate": 0.5, "obj_hit_rate": 0.5} for scenario in EXPECTED_SCENARIOS}
    db.execute(
        """INSERT INTO submissions
           (submitter_name, group_name, heuristic_name, description, algo_type, submitted_at, results_json, mrr, mrr_obj, mean_obj_hr, mean_byte_hr)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("FIFO", "baseline", "FIFO", "FIFO baseline", "classical", "2024-01-01T00:00:00", json.dumps(fifo_results), 1.0, 1.0, 0.5, 0.5)
    )
    db.commit()
    db.close()

    # Load FIFO baselines in the app
    app_module.load_fifo_baselines()

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
    app_module.DB_PATH = original_db_path


def create_valid_submission():
    """Create a valid submission payload with all 30 scenarios."""
    return {
        "metadata": {
            "submitter_name": "Test User",
            "group_name": "Test Group",
            "heuristic_name": "Test Heuristic",
            "description": "A test submission",
            "algo_type": "vulcanevolve"
        },
        "results": {
            scenario: {
                "byte_hit_rate": 0.6,
                "obj_hit_rate": 0.6
            } for scenario in EXPECTED_SCENARIOS
        }
    }


def test_valid_submission(client):
    """Test that a valid submission with all 30 traces is accepted."""
    payload = create_valid_submission()
    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data
    assert "submitted_at" in data
    assert "mrr" in data
    assert data["mrr"] is not None


def test_missing_submitter_name(client):
    """Test that submission without submitter_name is rejected."""
    payload = create_valid_submission()
    del payload["metadata"]["submitter_name"]

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data
    assert "submitter_name" in data["error"]


def test_missing_heuristic_name(client):
    """Test that submission without heuristic_name is rejected."""
    payload = create_valid_submission()
    del payload["metadata"]["heuristic_name"]

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data
    assert "heuristic_name" in data["error"]


def test_empty_submitter_name(client):
    """Test that submission with empty submitter_name is rejected."""
    payload = create_valid_submission()
    payload["metadata"]["submitter_name"] = ""

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data


def test_description_length_limit(client):
    """Test that description longer than 100 characters is rejected."""
    payload = create_valid_submission()
    payload["metadata"]["description"] = "x" * 101  # 101 characters

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data
    assert "description" in data["error"].lower()
    assert "100" in data["error"]


def test_description_exactly_100_chars(client):
    """Test that description with exactly 100 characters is accepted."""
    payload = create_valid_submission()
    payload["metadata"]["description"] = "x" * 100  # Exactly 100 characters

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 201


def test_description_under_100_chars(client):
    """Test that description under 100 characters is accepted."""
    payload = create_valid_submission()
    payload["metadata"]["description"] = "x" * 99  # 99 characters

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 201


def test_missing_traces(client):
    """Test that submission with missing traces is rejected."""
    payload = create_valid_submission()
    # Remove 5 scenarios
    for i, scenario in enumerate(EXPECTED_SCENARIOS[:5]):
        del payload["results"][scenario]

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data
    assert "30" in data["error"]


def test_extra_traces(client):
    """Test that submission with extra traces is rejected."""
    payload = create_valid_submission()
    # Add extra scenarios
    payload["results"]["w999_1pct"] = {"byte_hit_rate": 0.6, "obj_hit_rate": 0.6}
    payload["results"]["w999_3pct"] = {"byte_hit_rate": 0.6, "obj_hit_rate": 0.6}

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data
    assert "30" in data["error"]


def test_exactly_30_traces(client):
    """Test that submission with exactly 30 traces is accepted."""
    payload = create_valid_submission()
    assert len(payload["results"]) == 30

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 201


def test_wrong_trace_names(client):
    """Test that submission with wrong trace names is rejected."""
    payload = create_valid_submission()
    # Replace a valid scenario with an invalid one
    del payload["results"]["w86_1pct"]
    payload["results"]["w999_1pct"] = {"byte_hit_rate": 0.6, "obj_hit_rate": 0.6}

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data


def test_wrong_size_names(client):
    """Test that submission with wrong size names is rejected."""
    payload = create_valid_submission()
    # Replace a valid scenario with an invalid size
    del payload["results"]["w86_1pct"]
    payload["results"]["w86_5pct"] = {"byte_hit_rate": 0.6, "obj_hit_rate": 0.6}

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422
    data = response.get_json()
    assert "error" in data


def test_all_required_scenarios_present(client):
    """Test that all 30 required scenarios are validated."""
    payload = create_valid_submission()

    # Verify we have all expected scenarios
    for trace in EXPECTED_TRACES:
        for size in EXPECTED_SIZES:
            scenario = f"{trace}_{size}"
            assert scenario in payload["results"], f"Missing scenario: {scenario}"

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 201


def test_no_results_field(client):
    """Test that submission without results field is rejected."""
    payload = create_valid_submission()
    del payload["results"]

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422


def test_no_metadata_field(client):
    """Test that submission without metadata field is rejected."""
    payload = create_valid_submission()
    del payload["metadata"]

    response = client.post('/api/submit',
                          data=json.dumps(payload),
                          content_type='application/json')

    assert response.status_code == 422


def test_empty_json(client):
    """Test that empty JSON payload is rejected."""
    response = client.post('/api/submit',
                          data=json.dumps({}),
                          content_type='application/json')

    # Empty JSON is technically valid JSON but missing required fields,
    # so it could be either 400 (bad request) or 422 (validation error)
    assert response.status_code in [400, 422]


def test_malformed_json(client):
    """Test that malformed JSON is rejected."""
    response = client.post('/api/submit',
                          data="not json",
                          content_type='application/json')

    assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
