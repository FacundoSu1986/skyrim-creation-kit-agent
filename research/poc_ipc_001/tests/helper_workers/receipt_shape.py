"""Adversarial helper: SUCCESS-shaped responses with receipt-level defects.

Mode from sentinel <job-root>/temp/helper_mode.txt:

    missing_receipt / null_error_on_success / failed_receipt /
    unknown_receipt_field / bad_sha_upper / bad_sha_short / bad_sha_prefix /
    bad_sha_whitespace / output_outside_candidates / error_code_mismatch /
    too_many_inputs / too_many_outputs / too_many_warnings /
    too_many_assertions
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

GOOD_SHA = "a" * 64


def receipt(**overrides):
    base = {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": "SUCCESS",
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "inputs": [{"path": "input/fixture.txt", "sha256": GOOD_SHA}],
        "outputs": [],
        "worker_assertions": [
            {"name": "probe", "expected": True, "actual": True, "passed": True}
        ],
        "warnings": [],
    }
    base.update(overrides)
    return base


def response(status="SUCCESS", wr=None, err=None):
    return {
        "protocol_version": 1,
        "request_id": REQ_ID,
        "job_id": JOB_ID,
        "operation": OPERATION,
        "status": status,
        "started_at_ms": 1,
        "finished_at_ms": 2,
        "worker_receipt": wr,
        "error": err,
    }


if mode == "missing_receipt":
    doc = response("SUCCESS", None, None)
    del doc["worker_receipt"]
elif mode == "null_error_on_success":
    doc = response("SUCCESS", receipt(), None)
    del doc["error"]
elif mode == "failed_receipt":
    doc = response("SUCCESS", receipt(status="FAILED"), None)
elif mode == "unknown_receipt_field":
    r = receipt()
    r["sneaky"] = 1
    doc = response("SUCCESS", r, None)
elif mode in ("bad_sha_upper", "bad_sha_short", "bad_sha_prefix",
              "bad_sha_whitespace"):
    sha = {
        "bad_sha_upper": GOOD_SHA.upper(),
        "bad_sha_short": "a" * 63,
        "bad_sha_prefix": "sha256:" + GOOD_SHA,
        "bad_sha_whitespace": GOOD_SHA + " ",
    }[mode]
    doc = response("SUCCESS",
                   receipt(inputs=[{"path": "input/fixture.txt", "sha256": sha}]),
                   None)
elif mode == "output_outside_candidates":
    doc = response(
        "SUCCESS",
        receipt(outputs=[{"path": "logs/sneaky.txt", "sha256": GOOD_SHA}]),
        None,
    )
elif mode == "too_many_inputs":
    doc = response(
        "SUCCESS",
        receipt(inputs=[{"path": f"input/f{i}.txt", "sha256": GOOD_SHA}
                        for i in range(33)]),
        None,
    )
elif mode == "too_many_outputs":
    doc = response(
        "SUCCESS",
        receipt(outputs=[{"path": f"candidates/c{i}.txt", "sha256": GOOD_SHA}
                         for i in range(17)]),
        None,
    )
elif mode == "too_many_warnings":
    doc = response("SUCCESS", receipt(warnings=[f"w{i}" for i in range(33)]), None)
elif mode == "too_many_assertions":
    doc = response(
        "SUCCESS",
        receipt(worker_assertions=[
            {"name": f"a{i}", "expected": True, "actual": True, "passed": True}
            for i in range(101)
        ]),
        None,
    )
elif mode == "error_code_mismatch":
    doc = response(
        "PROCESS_FAILED", None,
        {"code": "INVALID_RESPONSE", "message": "mismatch probe"},
    )
elif mode == "nonempty_outputs_readonly":
    # Read-only operation, but the receipt claims a non-empty outputs list.
    # The orchestrator must reject this with WORKSPACE_VIOLATION because
    # the truthfulness invariant is exactly outputs == [] for read-only.
    doc = response(
        "SUCCESS",
        receipt(outputs=[{"path": "candidates/forged.txt", "sha256": GOOD_SHA}]),
        None,
    )
elif mode == "extra_input_ref":
    # Receipt claims the one expected input PLUS an extra fabricated ref.
    # The truthfulness invariant is exactly len(inputs) == 1 and a single
    # match against the orchestrator-provisioned SHA.
    doc = response(
        "SUCCESS",
        receipt(inputs=[
            {"path": "input/fixture.txt", "sha256": GOOD_SHA},
            {"path": "input/forged.txt", "sha256": GOOD_SHA},
        ]),
        None,
    )
elif mode == "missing_input_ref":
    # The receipt has no inputs at all. Truthfulness requires exactly one.
    doc = response("SUCCESS", receipt(inputs=[]), None)
elif mode == "wrong_input_path":
    # The receipt names an input that is not the one the orchestrator
    # provisioned. The path token is workspace-relative-canonical and
    # well-formed, so the schema accepts it; the orchestrator must
    # reject it as a workspace-truthfulness violation.
    doc = response(
        "SUCCESS",
        receipt(inputs=[{"path": "input/other.txt", "sha256": GOOD_SHA}]),
        None,
    )
elif mode == "wrong_input_sha":
    # The receipt names the right path but a forged sha256. The schema
    # accepts the hash (it is a valid 64-char lowercase hex), but the
    # orchestrator's trusted recomputation rejects it.
    doc = response(
        "SUCCESS",
        receipt(inputs=[{"path": "input/fixture.txt", "sha256": "b" * 64}]),
        None,
    )
else:
    raise SystemExit(f"unknown mode {mode}")

sys.stdout.buffer.write(json.dumps(doc).encode("utf-8"))
sys.stdout.buffer.flush()
