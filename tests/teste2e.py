import os
import json
import logging
import traceback
from backend.dsp.engine import process_audio
from backend.agents.models import TransformationPlan, TransformationOperation

logging.basicConfig(level=logging.INFO)

# Define cases based on user prompt
cases = [
    {
        "name": "Make it sound like a large auditorium",
        "plan": TransformationPlan(
            seed=42,
            operations=[
                TransformationOperation(operation="rir_convolution", profile="auditorium", parameters={})
            ]
        )
    },
    {
        "name": "Add traffic noise at 10 dB SNR",
        "plan": TransformationPlan(
            seed=42,
            operations=[
                TransformationOperation(operation="noise_injection", profile="traffic", parameters={"target_snr_db": 10.0})
            ]
        )
    },
    {
        "name": "Make it sound like a large auditorium with crowd noise",
        "plan": TransformationPlan(
            seed=42,
            operations=[
                TransformationOperation(operation="rir_convolution", profile="auditorium", parameters={}),
                TransformationOperation(operation="noise_injection", profile="crowd", parameters={"target_snr_db": 15.0})
            ]
        )
    },
    {
        "name": "Fail case - missing noise profile",
        "plan": TransformationPlan(
            seed=42,
            operations=[
                TransformationOperation(operation="noise_injection", profile="invalid_noise_profile", parameters={"target_snr_db": 10.0})
            ]
        )
    }
]

input_path = "test_3min.mp3"

for i, case in enumerate(cases):
    print(f"\n--- Running Case {i+1}: {case['name']} ---")
    output_path = f"test_out_{i}.wav"
    try:
        process_audio(input_path, output_path, case['plan'])
        trace_path = output_path + ".trace.json"
        if os.path.exists(trace_path):
            with open(trace_path, 'r') as f:
                trace = json.load(f)
            print(f"SUCCESS. Trace:")
            print(json.dumps(trace, indent=2))
        else:
            print("SUCCESS but NO TRACE FOUND.")
    except Exception as e:
        print(f"FAILED (Error: {e})")
