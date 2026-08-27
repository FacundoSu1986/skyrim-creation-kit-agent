"""Adversarial helper: process-level faults.

Mode from sentinel <job-root>/temp/helper_mode.txt:

    nonzero_plausible_success : fully valid SUCCESS JSON, then exit code 3
    zero_exit_invalid         : invalid JSON with exit 0
    crash_after_read          : hard abort (nonzero) with no output
"""
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
job_root = None
for i, arg in enumerate(args):
    if arg == "--job-root":
        job_root = Path(args[i + 1])
        break
assert job_root is not None, "helper requires --job-root"

mode = (job_root / "temp" / "helper_mode.txt").read_text(encoding="ascii").strip()
raw = sys.stdin.buffer.read()
request = json.loads(raw.decode("utf-8"))
REQ_ID = request["request_id"]
JOB_ID = request["job_id"]
OPERATION = request["operation"]


if mode == "nonzero_plausible_success":
    # Construct a fully schema-valid Receipt + Response that reflects the
    # *real* request identifiers, then exit 3. The orchestrator must still
    # classify this as PROCESS_FAILED — a plausible-looking SUCCESS payload
    # must never override a nonzero exit. The test must not be passing merely
    # because the JSON was schema-invalid to begin with.
    receipt = {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": "SUCCESS",
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "inputs": [],
        "outputs": [],
        "worker_assertions": [
            {"name": "always_true", "expected": True, "actual": True, "passed": True}
        ],
        "warnings": [],
    }
    response = {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": "SUCCESS",
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "worker_receipt": receipt,
        "error": None,
    }
    sys.stdout.buffer.write(json.dumps(response).encode("utf-8"))
    sys.stdout.buffer.flush()
    os._exit(3)
elif mode == "zero_exit_invalid":
    sys.stdout.buffer.write(b'{"half":')
    sys.stdout.buffer.flush()
    os._exit(0)
else:
    os.abort()
