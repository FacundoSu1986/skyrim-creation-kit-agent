"""Adversarial helper: schema-valid SUCCESS response with corrupted correlation.

Reads the REAL request from stdin, echoes its identifiers faithfully at both
levels (response + receipt), then corrupts EXACTLY ONE requested field at one
level — a resulting rejection proves the orchestrator checks that precise leg.

For level == "receipt", the response envelope is built from the *unmodified*
receipt first; only the embedded receipt copy is then corrupted. This
preserves the receipt-level correlation leg: the response keeps correct
identifiers, the embedded receipt is what fails, and the orchestrator must
specifically fail at the receipt-correlation loop (not the response loop).

Mode/leg from sentinel files in <job-root>/temp/:
    helper_mode.txt  : field name (request_id | job_id | operation)
    helper_level.txt : response | receipt
"""
import json
import sys
from pathlib import Path

args = sys.argv[1:]
job_root = None
for i, arg in enumerate(args):
    if arg == "--job-root":
        job_root = Path(args[i + 1])
        break
assert job_root is not None, "helper requires --job-root"

temp = job_root / "temp"
field = (temp / "helper_mode.txt").read_text(encoding="ascii").strip()
level_file = temp / "helper_level.txt"
level = level_file.read_text(encoding="ascii").strip() if level_file.exists() else "response"

raw = sys.stdin.buffer.read()
request = json.loads(raw.decode("utf-8"))

# Use SCHEMA-VALID but REQUEST-MISMATCH values so the test exercises the
# orchestrator's correlation gate (post-schema). A non-schema-valid value
# would be caught by validate_response / validate_receipt as
# INVALID_RESPONSE, never reaching correlation.
WRONG_REQUEST_ID = "ffffffff-ffff-4fff-bfff-ffffffffffff"
WRONG_JOB_ID = "JOB-CORRUPT-1234"
WRONG_OPERATION = "CORRUPTED_OP"
WRONG = {
    "request_id": WRONG_REQUEST_ID,
    "job_id": WRONG_JOB_ID,
    "operation": WRONG_OPERATION,
}[field]

receipt = {
    "protocol_version": 1,
    "request_id": request["request_id"],
    "job_id": request["job_id"],
    "operation": request["operation"],
    "status": "SUCCESS",
    "started_at_ms": 1,
    "finished_at_ms": 2,
    "inputs": [{"path": f"input/{request['parameters']['input_name']}",
                "sha256": "a" * 64}],
    "outputs": [],
    "worker_assertions": [
        {"name": "probe", "expected": True, "actual": True, "passed": True}
    ],
    "warnings": [],
}

# Build the response envelope from the *unmodified* receipt first so that
# response-level correlation holds for level == "receipt" tests. Only after
# the copy is made do we corrupt the embedded receipt — the orchestrator's
# response-correlation gate then passes and the receipt-correlation gate
# is the one that fires.
response = dict(receipt)
del response["worker_assertions"], response["warnings"], response["inputs"]
del response["outputs"]
response["status"] = "SUCCESS"
if level == "receipt":
    receipt[field] = WRONG
response["worker_receipt"] = receipt
response["error"] = None
if level == "response":
    response[field] = WRONG

sys.stdout.buffer.write(json.dumps(response).encode("utf-8"))
sys.stdout.buffer.flush()
