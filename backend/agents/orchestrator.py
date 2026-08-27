import os
from typing import Tuple, Dict, Any, List
from backend.agents.models import TransformationPlan, TransformationOperation, Intent
from backend.agents.planner_agent import ValidationResult, ValidationErrorDetail
from backend.dsp.registry import REGISTRY, validate_operation

ASSET_DIR = "backend/dsp/assets"

class PlanNormalizer:
    @staticmethod
    def normalize(plan: TransformationPlan) -> TransformationPlan:
        # Fill safe defaults, normalize units, etc.
        if not plan.seed:
            plan.seed = 42
        return plan

class RegistryValidator:
    @staticmethod
    def validate(plan: TransformationPlan) -> ValidationResult:
        errors = []
        for op in plan.operations:
            # 1. Check operation exists
            if op.operation not in REGISTRY:
                errors.append(ValidationErrorDetail(
                    operation=op.operation,
                    reason=f"Operation '{op.operation}' is not registered."
                ))
                continue
                
            defn = REGISTRY[op.operation]
            
            # 2. Check profile
            if op.profile and defn.allowed_profiles and op.profile not in defn.allowed_profiles:
                errors.append(ValidationErrorDetail(
                    operation=op.operation,
                    parameter="profile",
                    value=op.profile,
                    reason=f"Profile '{op.profile}' not allowed. Allowed: {defn.allowed_profiles}"
                ))
                
            # 3. Asset validation
            if op.operation == "rir_convolution" and op.profile:
                if not os.path.exists(os.path.join(ASSET_DIR, "rir", op.profile)):
                    errors.append(ValidationErrorDetail(
                        operation=op.operation,
                        parameter="profile",
                        value=op.profile,
                        reason=f"Asset for profile '{op.profile}' not found in RIR directory."
                    ))
            elif op.operation == "noise_injection" and op.profile:
                if not os.path.exists(os.path.join(ASSET_DIR, "noise", op.profile)):
                    errors.append(ValidationErrorDetail(
                        operation=op.operation,
                        parameter="profile",
                        value=op.profile,
                        reason=f"Asset for profile '{op.profile}' not found in Noise directory."
                    ))

            # 4. Check required params
            for req in defn.required_parameters:
                if req not in op.parameters:
                    errors.append(ValidationErrorDetail(
                        operation=op.operation,
                        parameter=req,
                        reason=f"Missing required parameter '{req}'"
                    ))
                    
            # 5. Check bounds
            for param_name, param_val in op.parameters.items():
                if param_name in defn.parameter_bounds:
                    bounds = defn.parameter_bounds[param_name]
                    if not (bounds.min_val <= param_val <= bounds.max_val):
                        errors.append(ValidationErrorDetail(
                            operation=op.operation,
                            parameter=param_name,
                            value=param_val,
                            allowed_range=[bounds.min_val, bounds.max_val],
                            reason="Parameter outside registry bounds"
                        ))
                        
        return ValidationResult(valid=len(errors) == 0, errors=errors)

def orchestrate_planning(intent: Intent, profile: Any, plan_func, max_retries: int = 3) -> Tuple[TransformationPlan, int]:
    """Runs the planner in a loop until validation passes or max retries hit."""
    attempts = 0
    plan = None
    val_result = None
    
    while attempts < max_retries:
        attempts += 1
        
        # 1. Plan
        try:
            plan = plan_func(intent, profile, previous_plan=plan, validation_result=val_result)
        except Exception as e:
            # Type A - Transient LLM failure (simplified here as immediate failure for prototype,
            # but would have exponential backoff in prod).
            raise Exception(f"Planner Agent Failed: {str(e)}")
            
        # 2. Normalize
        plan = PlanNormalizer.normalize(plan)
        
        # 3. Validate
        val_result = RegistryValidator.validate(plan)
        
        if val_result.valid:
            return plan, attempts
            
    # Max retries hit
    raise ValueError(f"Planner failed to produce a valid plan after {max_retries} attempts. Last errors: {val_result.model_dump_json()}")
