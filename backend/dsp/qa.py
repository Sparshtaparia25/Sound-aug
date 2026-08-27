from typing import List, Dict, Any
from backend.agents.models import TransformationPlan, AudioProfile
from pydantic import BaseModel, Field

class QA_Result(BaseModel):
    operation: str
    passed: bool
    details: str

def validate_plan_execution(plan: TransformationPlan, pre_profile: AudioProfile, post_profile: AudioProfile, trace_metadata: List[Dict[str, Any]] = None) -> List[QA_Result]:
    results = []
    
    # Generic checks
    if post_profile.signal_quality.clipping_ratio > 0.01:
        results.append(QA_Result(operation="global", passed=False, details="Severe clipping detected in output."))
    
    for op in plan.operations:
        if op.operation == "rir_convolution":
            rt60_increase = post_profile.environment.reverberation_estimate > pre_profile.environment.reverberation_estimate
            results.append(QA_Result(
                operation=op.operation, 
                passed=rt60_increase, 
                details="Reverberation increased." if rt60_increase else "Reverberation did not increase as expected."
            ))
            
        elif op.operation == "noise_injection":
            target_snr = op.parameters.get("target_snr_db", 10.0)
            
            if trace_metadata:
                for trace in trace_metadata:
                    if trace["operation"] == "noise_injection":
                        exact_snr = trace["metadata"]["measured_injected_snr"]
                        exact_passed = abs(target_snr - exact_snr) <= 1.0
                        results.append(QA_Result(
                            operation=op.operation + "_exact",
                            passed=exact_passed,
                            details=f"Target SNR: {target_snr}, Exact Injected: {exact_snr:.2f}"
                        ))
            
            measured_snr = post_profile.noise.estimated_snr
            # tolerance of 2 dB for the profiler
            passed = abs(target_snr - measured_snr) <= 2.0
            results.append(QA_Result(
                operation=op.operation + "_profiler",
                passed=passed,
                details=f"Target SNR: {target_snr}, Profiler Measured: {measured_snr:.1f}"
            ))
            
        elif op.operation == "pitch_shift":
            semitones = op.parameters.get("semitones", 0.0)
            if pre_profile.prosody.f0 and post_profile.prosody.f0:
                expected_shift = 2 ** (semitones / 12.0)
                actual_shift = post_profile.prosody.f0.median / pre_profile.prosody.f0.median
                # 10% tolerance
                passed = abs(expected_shift - actual_shift) / expected_shift < 0.1
                results.append(QA_Result(
                    operation=op.operation,
                    passed=passed,
                    details=f"Target shift: {expected_shift:.2f}x, Actual: {actual_shift:.2f}x"
                ))
            else:
                results.append(QA_Result(
                    operation=op.operation,
                    passed=True,
                    details="F0 not reliably detected, skipping strict validation."
                ))
                
        elif op.operation == "loudness_normalization":
            target_lufs = op.parameters.get("target_lufs", -23.0)
            measured_lufs = post_profile.signal_quality.lufs or 0.0
            passed = abs(target_lufs - measured_lufs) <= 1.0
            results.append(QA_Result(
                operation=op.operation,
                passed=passed,
                details=f"Target LUFS: {target_lufs}, Measured: {measured_lufs:.1f}"
            ))
            
        elif op.operation == "source_separation":
            results.append(QA_Result(
                operation=op.operation,
                passed=True,
                details="Source separation applied. (Detailed SDR validation requires reference audio)."
            ))
            
        else:
            results.append(QA_Result(
                operation=op.operation,
                passed=True,
                details="Operation applied successfully."
            ))
            
    return results
