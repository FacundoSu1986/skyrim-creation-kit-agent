"""Adversarial helper for P0-2: emits a schema-valid error Response.

The orchestrator must accept this without touching response["worker_receipt"]
(which is null) and classify the session as the worker's reported status
(without raising an exception). Response-level correlation still applies:
modes that deliberately corrupt request_id or job_id must produce
RECEIPT_MISMATCH, not the worker's claimed status.

Mode from sentinel <job-root>/temp/helper_mode.txt:
    valid_error_workspace_violation
    valid_error_invalid_operation
    wrong_job_id
    wrong_request_id

Optional sentinel <job-root>/temp/helper_wrong_job.txt:
    present => swap job_id for a different one in the Response.
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
mode = (temp / "helper_mode.txt").read_text(encoding="ascii").strip()
raw = sys.stdin.buffer.read()
request = json.loads(raw.decode("utf-8"))
REQ_ID = request["request_id"]
JOB_ID = request["job_id"]
OPERATION = request["operation"]

WRONG_REQ_ID = "00000000-0000-4000-8000-000000000000"
WRONG_JOB_ID = "JOB-NOT-OURS"


def error_response(status):
    return {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": status,
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "worker_receipt": None,
        "error": {"code": status, "message": f"helper-mode {mode}"},
    }


if mode == "valid_error_workspace_violation":
    doc = error_response("WORKSPACE_VIOLATION")
elif mode == "valid_error_invalid_operation":
    doc = error_response("INVALID_OPERATION")
elif mode == "wrong_job_id":
    doc = error_response("WORKSPACE_VIOLATION")
    doc["job_id"] = WRONG_JOB_ID
elif mode == "wrong_request_id":
    doc = error_response("WORKSPACE_VIOLATION")
    doc["request_id"] = WRONG_REQ_ID
else:
    raise SystemExit(f"unknown mode {mode}")

sys.stdout.buffer.write(json.dumps(doc).encode("utf-8"))
sys.stdout.buffer.flush()
