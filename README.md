# Agentic Speech Data Augmentation

An enterprise-grade, prompt-driven speech data augmentation platform. This system utilizes a deterministic DSP pipeline orchestrated by an LLM planner to transform speech audio according to natural language intents.

## Architecture

The system operates across a robust 4-stage pipeline:

1. **Preflight & Profiling**: Uploads are strictly validated against limits (file size, duration, sample rate, channels, decompression bombs). The audio is mathematically profiled (SNR, RMS, Peak, etc.).
2. **Intent & Planning**: A Gemini-powered Intent Agent extracts semantic descriptors, and a Planner Agent securely maps those descriptors to a strictly-bounded deterministic DSP registry.
3. **Execution & QA**: A background job executes the validated, canonical DSP operations (e.g. Convolution, Noise Injection, EQ) via `scipy`/`librosa`/`pedalboard`. The augmented output is profiled and compared against deterministic bounds (e.g., Target SNR).
4. **Artifact Lineage**: All operations are idempotent, structurally logged, and fully tracked. Original inputs, final outputs, profiles, and reports are safely stored and isolated per-request with SHA-256 validation checksums.

## Quick Start

### 1. Environment Setup

Ensure you have Conda installed, then create and activate the environment:

```bash
conda create -n prism python=3.10
conda activate prism
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration

Set up your `.env` file (or rename the `.env` we generated):
```bash
GEMINI_API_KEY=your_api_key_here
```
You can also tweak resource limits in the `.env` file:
- `MAX_AUDIO_FILE_SIZE_MB` (default: 20)
- `MAX_AUDIO_DURATION_SECONDS` (default: 60)
- `MAX_BATCH_DURATION_SECONDS` (default: 600)

### 3. Run the Application

Start the FastAPI application:
```bash
uvicorn backend.main:app --reload
```

Then navigate to `http://localhost:8000` to access the Enterprise Audio Lab UI.

## Testing

This project features a comprehensive `pytest` regression suite that tests the State Machine, Validation Engine, Path Traversal protections, and End-to-End Idempotency logic.

Run tests via:
```bash
PYTHONPATH='.' pytest tests/
```

## Structure
- `/backend`: FastAPI application, DSP engine, Agent models, Config, and Orchestration logic.
- `/frontend`: Dark-themed enterprise audio lab SPA built with Vanilla JS, CSS, and WaveSurfer.js.
- `/tests`: Pytest regression suite.
- `/storage`: Data store mapping isolated artifacts by request ID.
