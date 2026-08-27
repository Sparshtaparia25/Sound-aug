import pytest
from fastapi.testclient import TestClient
import io
import os
import json
from backend.main import app, jobs
from backend.config import config

client = TestClient(app)

def create_dummy_wav(size_bytes: int = 100) -> bytes:
    """Creates a fake bytes object to simulate a file"""
    # For actual header probing to pass, we need a real wav header.
    # For now, we will test the size limit which happens before header probing.
    return b"0" * size_bytes

def test_upload_too_large():
    # Exceed 20MB limit
    large_size = (config.MAX_AUDIO_FILE_SIZE_MB + 1) * 1024 * 1024
    fake_file = io.BytesIO(create_dummy_wav(large_size))
    
    response = client.post(
        "/api/plan",
        data={"prompt": "test"},
        files={"files": ("large.wav", fake_file, "audio/wav")}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "FILE_TOO_LARGE"

def test_invalid_extension():
    fake_file = io.BytesIO(b"fake data")
    
    response = client.post(
        "/api/plan",
        data={"prompt": "test"},
        files={"files": ("bad_ext.txt", fake_file, "text/plain")}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_FILE_TYPE"

def test_idempotent_execution(monkeypatch):
    # Inject a fake job state
    req_id = "test-idempotent-123"
    jobs[req_id] = {"status": "PLAN_READY"}
    
    # Prevent the background task from running synchronously and crashing
    from backend import main
    monkeypatch.setattr(main, "execute_dsp_job", lambda req: None)
    
    # First execution should succeed and move to QUEUED
    res1 = client.post(f"/api/execute/{req_id}")
    assert res1.status_code == 200
    assert res1.json()["status"] == "QUEUED"
    
    # Second execution should reject because it's already QUEUED
    res2 = client.post(f"/api/execute/{req_id}")
    assert res2.status_code == 200
    assert res2.json()["status"] == "QUEUED"
    assert "already executing" in res2.json()["message"]

def test_execute_invalid_state():
    # Inject a fake job state
    req_id = "test-invalid-123"
    jobs[req_id] = {"status": "PLAN_FAILED"}
    
    res = client.post(f"/api/execute/{req_id}")
    assert res.status_code == 400
    assert res.json()["error_code"] == "INVALID_STATE"

def test_get_artifact_path_traversal():
    req_id = "test-traverse-123"
    res = client.get(f"/api/jobs/{req_id}/artifacts/input/..%2F..%2F..%2Fetc%2Fpasswd")
    
    assert res.status_code == 403
    assert res.json()["error_code"] == "FORBIDDEN"
