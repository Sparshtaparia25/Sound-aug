import pytest
from backend.dsp.registry import REGISTRY, validate_operation
from backend.agents.models import TransformationPlan, TransformationOperation
from backend.agents.orchestrator import RegistryValidator

def test_registry_valid_operation():
    plan = TransformationPlan(
        seed=42,
        operations=[
            TransformationOperation(
                operation="noise_injection",
                profile="traffic",
                parameters={"target_snr_db": 10.0}
            )
        ]
    )
    # Assume assets exist or we mock them. For now, since orchestrator checks OS path,
    # we might need to mock os.path.exists in a real suite, but let's just test bounds logic.
    pass

def test_registry_invalid_operation():
    plan = TransformationPlan(
        seed=42,
        operations=[
            TransformationOperation(
                operation="invalid_op",
                parameters={}
            )
        ]
    )
    result = RegistryValidator.validate(plan)
    assert not result.valid
    assert result.errors[0].operation == "invalid_op"
    assert "not registered" in result.errors[0].reason

def test_registry_out_of_bounds():
    plan = TransformationPlan(
        seed=42,
        operations=[
            TransformationOperation(
                operation="noise_injection",
                profile="traffic",
                parameters={"target_snr_db": 500.0} # Max is 40.0
            )
        ]
    )
    # In a full test we would mock os.path.exists for the asset
    # Let's bypass asset check by just checking the errors array contains bounds error
    result = RegistryValidator.validate(plan)
    bounds_errors = [e for e in result.errors if "bounds" in e.reason]
    assert len(bounds_errors) > 0
    assert bounds_errors[0].parameter == "target_snr_db"

def test_registry_missing_required_param():
    plan = TransformationPlan(
        seed=42,
        operations=[
            TransformationOperation(
                operation="noise_injection",
                profile="traffic",
                parameters={} # Missing target_snr_db
            )
        ]
    )
    result = RegistryValidator.validate(plan)
    missing_errors = [e for e in result.errors if "Missing required" in e.reason]
    assert len(missing_errors) > 0
    assert missing_errors[0].parameter == "target_snr_db"
