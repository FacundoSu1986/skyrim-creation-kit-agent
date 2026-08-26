"""INSPECT_SYNTHETIC_INPUT — the single read-only synthetic operation.

Contract (ADR-002 POC scope):
- parameters: {"input_name": <safe-name token>}
- reads workspace/jobs/<job_id>/input/<input_name> (trusted-side resolution)
- computes SHA-256 + byte length + synthetic magic check
- emits non-vacuous worker assertions
- writes nothing (read-only; outputs == [])
"""

import hashlib
import os
import re
from pathlib import Path

OPERATION_NAME = "INSPECT_SYNTHETIC_INPUT"

# The committed fixture starts with this magic marker.
SYNTHETIC_MAGIC = "POCIPC1"

PARAMETER_FIELDS = {"input_name"}


def validate_parameters(params):
    """Closed-world per-operation parameter schema. Returns (ok, detail)."""
    if not isinstance(params, dict):
        return False, "parameters must be an object"
    keys = set(params.keys())
    if keys != PARAMETER_FIELDS:
        return False, (
            f"{OPERATION_NAME} parameters: expected exactly {sorted(PARAMETER_FIELDS)}, "
            f"got {sorted(keys)}"
        )
    from protocol import validate_safe_name

    if not validate_safe_name(params["input_name"]):
        return False, "input_name violates safe-name contract"
    return True, ""


def make_assertion(name, expected, actual, passed, details=None):
    assertion = {
        "name": name,
        "expected": expected,
        "actual": actual,
        "passed": bool(passed),
    }
    if details is not None:
        assertion["details"] = details
    return assertion


def execute(job_dir, params):
    """Run the read-only inspection. Returns a receipt dict (no persistence).

    job_dir: trusted-side resolved Path for jobs/<job_id> (worker cwd).
    Raises OSError on unreadable input (caller maps to worker error).
    """
    import re
    from pathlib import Path

    input_name = params["input_name"]
    # Worker-side containment mirrors the orchestrator: resolve + re-contain.
    area = (Path(job_dir) / "input").resolve()
    target = (area / input_name).resolve()
    root = os.path.normcase(str(area))
    t = os.path.normcase(str(target))
    if not (t == root or t.startswith(root + os.sep)):
        raise PermissionError("resolved input escaped the input area")

    data = target.read_bytes()
    sha_hex = hashlib.sha256(data).hexdigest()
    length = len(data)
    magic_actual = data[: len(SYNTHETIC_MAGIC)].decode("ascii", errors="replace")

    assertions = [
        make_assertion(
            "input_readable",
            True,
            True,
            True,
        ),
        make_assertion(
            "magic_bytes_match_synthetic",
            SYNTHETIC_MAGIC,
            magic_actual,
            magic_actual == SYNTHETIC_MAGIC,
        ),
        make_assertion(
            "sha256_format_valid",
            True,
            bool(re.fullmatch(r"[0-9a-f]{64}", sha_hex)),
            bool(re.fullmatch(r"[0-9a-f]{64}", sha_hex)),
        ),
        make_assertion(
            "byte_length_gt_zero",
            True,
            length > 0,
            length > 0,
        ),
    ]

    receipt = {
        "protocol_version": 1,
        "request_id": None,      # filled by the worker entry (correlation)
        "job_id": None,          # filled by the worker entry
        "operation": OPERATION_NAME,
        "status": "SUCCESS",
        "started_at_ms": None,   # filled by the worker entry
        "finished_at_ms": None,  # filled by the worker entry
        "inputs": [{"path": f"input/{input_name}", "sha256": sha_hex}],
        "outputs": [],           # read-only operation: no candidate artifacts
        "worker_assertions": assertions,
        "warnings": [],
    }
    return receipt
