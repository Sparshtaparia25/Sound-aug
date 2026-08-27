import os
import time
import json
import uuid
import shutil
import asyncio
import hashlib
import soundfile as sf
from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import config
from backend.agents.intent_agent import extract_intent
from backend.agents.planner_agent import plan_transformation
from backend.agents.orchestrator import orchestrate_planning
from backend.dsp.profiler import profile_audio
from backend.dsp.engine import process_audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured Logging
def log_event(req_id: str, stage: str, event: str, status: str, duration_ms: int = None, error_code: str = None, details: Any = None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": req_id,
        "stage": stage,
        "event": event,
        "status": status,
    }
    if duration_ms is not None:
        log_entry["duration_ms"] = duration_ms
    if error_code is not None:
        log_entry["error_code"] = error_code
    if details is not None:
        log_entry["details"] = details
        
    print(json.dumps(log_entry))
    
    # Also write to trace.json if request dir exists
    trace_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "trace.json")
    if os.path.exists(os.path.dirname(trace_path)):
        with open(trace_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

# In-memory job state (for MVP)
jobs: Dict[str, Dict[str, Any]] = {}

def get_sha256(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_request_dirs(req_id: str):
    base = os.path.join(config.STORAGE_ROOT, "requests", req_id)
    for subdir in ["input", "output", "profiles", "plans", "reports"]:
        os.makedirs(os.path.join(base, subdir), exist_ok=True)

@app.post("/api/plan")
async def create_plan(
    files: List[UploadFile] = File(...),
    prompt: str = Form(...)
):
    """Stage 1: Preflight, Profile, Intent, Plan Validation, Canonical Storage."""
    t_start = time.perf_counter()
    req_id = str(uuid.uuid4())
    create_request_dirs(req_id)
    
    log_event(req_id, "UPLOAD", "STARTED", "SUCCESS")
    
    jobs[req_id] = {
        "status": "RECEIVED",
        "progress": 0,
        "files": [],
        "manifest": {
            "request_id": req_id,
            "status": "PLANNING",
            "artifacts": {}
        }
    }
    
    if len(files) > config.MAX_BATCH_FILES:
        log_event(req_id, "UPLOAD", "FAILED", "ERROR", error_code="TOO_MANY_FILES")
        return JSONResponse(status_code=400, content={"error_code": "TOO_MANY_FILES", "message": f"Max {config.MAX_BATCH_FILES} allowed."})
        
    total_duration = 0.0
    saved_files = []
    
    try:
        # Preflight checks
        for file in files:
            # 1. Size & Ext
            file.file.seek(0, os.SEEK_END)
            size_bytes = file.file.tell()
            file.file.seek(0)
            
            if size_bytes > config.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"FILE_TOO_LARGE: {file.filename}")
                
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in [".wav", ".mp3", ".flac", ".m4a"]:
                raise ValueError(f"INVALID_FILE_TYPE: {file.filename}")
                
            input_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "input", file.filename)
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # 2. Header Probe (Decompression bomb & duration protection)
            try:
                info = sf.info(input_path)
            except Exception:
                raise ValueError(f"CORRUPT_AUDIO: {file.filename} is not valid audio.")
                
            if info.samplerate > config.MAX_SAMPLE_RATE:
                raise ValueError(f"UNSUPPORTED_SAMPLE_RATE: {info.samplerate}Hz > {config.MAX_SAMPLE_RATE}Hz")
            if info.channels > config.MAX_CHANNELS:
                raise ValueError(f"UNSUPPORTED_CHANNEL_COUNT: {info.channels} > {config.MAX_CHANNELS}")
            if info.duration > config.MAX_AUDIO_DURATION_SECONDS:
                raise ValueError(f"AUDIO_TOO_LONG: {file.filename} is {info.duration}s > {config.MAX_AUDIO_DURATION_SECONDS}s")
                
            total_duration += info.duration
            if total_duration > config.MAX_BATCH_DURATION_SECONDS:
                raise ValueError("MAX_BATCH_DURATION_EXCEEDED")
                
            file_sha = get_sha256(input_path)
            saved_files.append({
                "filename": file.filename,
                "path": input_path,
                "sha256": file_sha,
                "size_bytes": size_bytes,
                "duration": info.duration
            })
            
        jobs[req_id]["files"] = saved_files
        jobs[req_id]["manifest"]["input_files"] = [{"filename": f["filename"], "sha256": f["sha256"]} for f in saved_files]
        
        log_event(req_id, "UPLOAD", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_start)*1000))
        
        # Profiling
        t_prof = time.perf_counter()
        jobs[req_id]["status"] = "PROFILING"
        jobs[req_id]["progress"] = 10
        
        # Profile first file (homogeneous batch assumption)
        original_profile = profile_audio(saved_files[0]["path"])
        prof_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "profiles", "input.json")
        with open(prof_path, "w") as f:
            f.write(original_profile.model_dump_json(indent=2))
        jobs[req_id]["manifest"]["artifacts"]["input_profile"] = "profiles/input.json"
        
        log_event(req_id, "PROFILING", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_prof)*1000))
        
        # Intent Understanding
        t_int = time.perf_counter()
        jobs[req_id]["status"] = "UNDERSTANDING_INTENT"
        jobs[req_id]["progress"] = 30
        
        intent_response = extract_intent(prompt)
        if intent_response.is_ambiguous:
            jobs[req_id]["status"] = "NEEDS_CLARIFICATION"
            log_event(req_id, "INTENT", "FAILED", "ERROR", error_code="INTENT_AMBIGUOUS")
            return JSONResponse(content={
                "status": "NEEDS_CLARIFICATION",
                "request_id": req_id,
                "message": intent_response.ambiguity_details.reason,
                "suggested_options": intent_response.ambiguity_details.suggested_options
            })
            
        intent = intent_response.intent
        log_event(req_id, "INTENT", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_int)*1000))
        
        # Planning
        t_plan = time.perf_counter()
        jobs[req_id]["status"] = "PLANNING"
        jobs[req_id]["progress"] = 50
        
        plan, attempts = orchestrate_planning(intent, original_profile, plan_transformation, max_retries=config.MAX_PLAN_RETRIES)
        
        canonical_data = {
            "intent": intent.model_dump(),
            "plan": plan.model_dump(),
            "prompt": prompt,
            "attempts": attempts
        }
        plan_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "plans", "transformation_plan.json")
        with open(plan_path, "w") as f:
            json.dump(canonical_data, f, indent=2)
            
        jobs[req_id]["manifest"]["artifacts"]["transformation_plan"] = "plans/transformation_plan.json"
        
        log_event(req_id, "PLANNING", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_plan)*1000))
        
        jobs[req_id]["status"] = "PLAN_READY"
        jobs[req_id]["progress"] = 100
        jobs[req_id]["manifest"]["status"] = "PLAN_READY"
        
        with open(os.path.join(config.STORAGE_ROOT, "requests", req_id, "manifest.json"), "w") as f:
            json.dump(jobs[req_id]["manifest"], f, indent=2)
            
        return JSONResponse(content={
            "status": "PLAN_READY",
            "request_id": req_id,
            "input_profile": original_profile.model_dump(),
            "intent": canonical_data["intent"],
            "plan": canonical_data["plan"]
        })
        
    except ValueError as e:
        err_str = str(e)
        code = err_str.split(":")[0] if ":" in err_str else "VALIDATION_FAILED"
        log_event(req_id, "PREFLIGHT", "FAILED", "ERROR", error_code=code, details={"msg": err_str})
        jobs[req_id]["status"] = "PLAN_FAILED"
        return JSONResponse(status_code=400, content={"status": "PLAN_FAILED", "error_code": code, "message": err_str})
    except Exception as e:
        log_event(req_id, "PLANNING", "FAILED", "ERROR", error_code="INTERNAL_ERROR", details={"msg": str(e)})
        jobs[req_id]["status"] = "PLAN_FAILED"
        return JSONResponse(status_code=500, content={"status": "PLAN_FAILED", "error_code": "INTERNAL_ERROR", "message": str(e)})

def execute_dsp_job(req_id: str):
    """Background task to run DSP with idempotency checks and lineage."""
    t_job = time.perf_counter()
    try:
        log_event(req_id, "DSP_EXECUTION", "STARTED", "SUCCESS")
        jobs[req_id]["status"] = "AUGMENTING"
        jobs[req_id]["progress"] = 20
        
        plan_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "plans", "transformation_plan.json")
        with open(plan_path, "r") as f:
            canonical_data = json.load(f)
            
        from backend.agents.models import TransformationPlan
        plan = TransformationPlan.model_validate(canonical_data["plan"])
        
        out_files = []
        total_files = len(jobs[req_id]["files"])
        
        for i, file_info in enumerate(jobs[req_id]["files"]):
            in_path = file_info["path"]
            out_filename = f"aug_{file_info['filename']}"
            out_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "output", out_filename)
            
            t_dsp = time.perf_counter()
            process_audio(in_path, out_path, plan)
            log_event(req_id, "DSP_FILE", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_dsp)*1000), details={"file": out_filename})
            
            out_sha = get_sha256(out_path)
            out_files.append({
                "original_filename": file_info["filename"],
                "augmented_filename": out_filename,
                "original_uri": f"/api/jobs/{req_id}/artifacts/input/{file_info['filename']}",
                "augmented_uri": f"/api/jobs/{req_id}/artifacts/output/{out_filename}",
                "sha256": out_sha
            })
            jobs[req_id]["progress"] = 20 + int(40 * ((i + 1) / total_files))
            
        jobs[req_id]["manifest"]["output_files"] = [{"filename": f["augmented_filename"], "sha256": f["sha256"]} for f in out_files]
        
        # Profiling Output
        t_out_prof = time.perf_counter()
        jobs[req_id]["status"] = "PROFILING_OUTPUT"
        jobs[req_id]["progress"] = 70
        
        first_out_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "output", out_files[0]["augmented_filename"])
        new_profile = profile_audio(first_out_path)
        
        prof_out_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "profiles", "output.json")
        with open(prof_out_path, "w") as f:
            f.write(new_profile.model_dump_json(indent=2))
        jobs[req_id]["manifest"]["artifacts"]["output_profile"] = "profiles/output.json"
        
        log_event(req_id, "PROFILING_OUTPUT", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_out_prof)*1000))
        
        # QA
        t_qa = time.perf_counter()
        jobs[req_id]["status"] = "QUALITY_CHECK"
        jobs[req_id]["progress"] = 85
        
        qa_status = "PASS"
        qa_checks = []
        for op in plan.operations:
            if op.operation == "noise_injection":
                target_snr = op.parameters.get("target_snr_db", 10.0)
                actual_snr = new_profile.noise.estimated_snr
                if abs(actual_snr - target_snr) <= 1.5:
                    qa_checks.append(f"Noise SNR Target: {target_snr}dB, Actual: {actual_snr:.1f}dB. (PASS)")
                else:
                    qa_checks.append(f"Noise SNR Target: {target_snr}dB, Actual: {actual_snr:.1f}dB. (WARN)")
                    qa_status = "WARN" # Adjust based on strictness
                    
        qa_report = {
            "status": qa_status,
            "checks": qa_checks
        }
        qa_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "reports", "qa_report.json")
        with open(qa_path, "w") as f:
            json.dump(qa_report, f, indent=2)
        jobs[req_id]["manifest"]["artifacts"]["qa_report"] = "reports/qa_report.json"
        
        log_event(req_id, "QUALITY_CHECK", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_qa)*1000), details={"qa_status": qa_status})
        
        # Finalize
        in_prof_path = os.path.join(config.STORAGE_ROOT, "requests", req_id, "profiles", "input.json")
        with open(in_prof_path, "r") as f:
            input_profile_dict = json.load(f)
            
        jobs[req_id]["metadata"] = {
            "request_id": req_id,
            "prompt": canonical_data["prompt"],
            "intent": canonical_data["intent"],
            "input_profile": input_profile_dict,
            "transformation_plan": canonical_data["plan"],
            "output_profile": new_profile.model_dump(),
            "quality": qa_report,
            "files": out_files
        }
        
        jobs[req_id]["status"] = "COMPLETED"
        jobs[req_id]["progress"] = 100
        jobs[req_id]["manifest"]["status"] = "COMPLETED"
        
        with open(os.path.join(config.STORAGE_ROOT, "requests", req_id, "manifest.json"), "w") as f:
            json.dump(jobs[req_id]["manifest"], f, indent=2)
            
        log_event(req_id, "JOB", "COMPLETED", "SUCCESS", duration_ms=int((time.perf_counter()-t_job)*1000))
        
    except Exception as e:
        log_event(req_id, "DSP_EXECUTION", "FAILED", "ERROR", error_code="DSP_EXECUTION_FAILED", details={"msg": str(e)})
        jobs[req_id]["status"] = "PROCESSING_FAILED"
        jobs[req_id]["error_code"] = "DSP_EXECUTION_FAILED"

@app.post("/api/execute/{request_id}")
async def execute_plan(request_id: str, background_tasks: BackgroundTasks):
    """Stage 2: Idempotent execution of approved canonical plan."""
    if request_id not in jobs:
        return JSONResponse(status_code=404, content={"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
        
    # Idempotency check
    current_status = jobs[request_id]["status"]
    if current_status in ["AUGMENTING", "PROFILING_OUTPUT", "QUALITY_CHECK", "QUEUED"]:
        return JSONResponse(content={"status": "QUEUED", "request_id": request_id, "message": "Job already executing."})
    elif current_status == "COMPLETED":
        return JSONResponse(content={"status": "COMPLETED", "request_id": request_id, "message": "Job already completed."})
    elif current_status != "PLAN_READY":
        return JSONResponse(status_code=400, content={"error_code": "INVALID_STATE", "message": f"Cannot execute in state {current_status}"})
        
    jobs[request_id]["status"] = "QUEUED"
    background_tasks.add_task(execute_dsp_job, request_id)
    return JSONResponse(content={"status": "QUEUED", "request_id": request_id})

@app.get("/api/jobs/{request_id}")
async def get_job_status(request_id: str):
    if request_id not in jobs:
        return JSONResponse(status_code=404, content={"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
    return JSONResponse(content=jobs[request_id])

@app.get("/api/jobs/{request_id}/artifacts/{artifact_type}/{filename:path}")
async def get_artifact(request_id: str, artifact_type: str, filename: str):
    if artifact_type not in ["input", "output", "profiles", "plans", "reports"]:
        return JSONResponse(status_code=400, content={"error_code": "INVALID_ARTIFACT_TYPE"})
        
    file_path = os.path.join(config.STORAGE_ROOT, "requests", request_id, artifact_type, filename)
    
    # Path traversal protection is inherently handled by os.path.join and restricting artifact_type,
    # but strictly checking normpath is safer:
    base = os.path.abspath(os.path.join(config.STORAGE_ROOT, "requests", request_id, artifact_type))
    target = os.path.abspath(file_path)
    if not target.startswith(base):
        return JSONResponse(status_code=403, content={"error_code": "FORBIDDEN", "message": "Path traversal detected."})
        
    if os.path.exists(file_path):
        media_type = "audio/wav" if artifact_type in ["input", "output"] else "application/json"
        return FileResponse(file_path, media_type=media_type)
        
    return JSONResponse(status_code=404, content={"error_code": "ARTIFACT_NOT_FOUND"})

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
