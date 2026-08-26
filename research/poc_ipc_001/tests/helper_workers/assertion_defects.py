"""Adversarial helper: SUCCESS-shaped responses with assertion-level defects.

Mode from sentinel <job-root>/temp/helper_mode.txt:

    empty_assertions / passed_false / passed_int_one / passed_int_zero /
    nested_expected / float_actual
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

mode = (job_root / "temp" / "helper_mode.txt").read_text(encoding="ascii").strip()
raw = sys.stdin.buffer.read()
request = json.loads(raw.decode("utf-8"))
REQ_ID = request["request_id"]
JOB_ID = request["job_id"]
OPERATION = request["operation"]

ASSERTIONS = {
    "empty_assertions": [],
    "passed_false": [
        {"name": "probe", "expected": True, "actual": False, "passed": False}
    ],
    "passed_int_one": [
        {"name": "probe", "expected": True, "actual": True, "passed": 1}
    ],
    "passed_int_zero": [
        {"name": "probe", "expected": True, "actual": True, "passed": 0}
    ],
    "nested_expected": [
        {"name": "probe", "expected": {"deep": True}, "actual": True, "passed": True}
    ],
    "float_actual": [
        {"name": "probe", "expected": 3, "actual": 1.5, "passed": True}
    ],
}

response = {
    "protocol_version": 1,
    "request_id": REQ_ID,
    "job_id": JOB_ID,
    "operation": OPERATION,
    "status": "SUCCESS",
    "started_at_ms": 1,
    "finished_at_ms": 2,
    "worker_receipt": {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": "SUCCESS",
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "inputs": [],
        "outputs": [],
        "worker_assertions": ASSERTIONS[mode],
        "warnings": [],
    },
    "error": None,
}
sys.stdout.buffer.write(json.dumps(response).encode("utf-8"))
sys.stdout.buffer.flush()
