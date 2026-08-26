"""Adversarial helper: emits deliberately malformed/invalid stream output.

Mode is read from the sentinel file <job-root>/temp/helper_mode.txt written by
the test harness (helpers receive the same argv as the trusted worker).

    invalid_json / nan / infinity / duplicate_keys / trailing /
    invalid_utf8 / empty / unknown_field / unknown_nested
"""
import os
import sys
from pathlib import Path

args = sys.argv[1:]
job_root = None
for i, arg in enumerate(args):
    if arg == "--job-root":
        job_root = Path(args[i + 1])
        break
assert job_root is not None, "helper requires --job-root like the real worker"

mode_file = job_root / "temp" / "helper_mode.txt"
mode = mode_file.read_text(encoding="ascii").strip()

sys.stdin.buffer.read()

PAYLOADS = {
    "invalid_json": b'{"this is": not json',
    "nan": b'{"protocol_version":1,"request_id":"x","status":"SUCCESS","score":NaN}',
    "infinity": b'{"protocol_version":Infinity,"status":"SUCCESS"}',
    "duplicate_keys": (
        b'{"protocol_version":1,"protocol_version":2,"status":"SUCCESS"}'
    ),
    "trailing": b'{"a":1} {"b":2}',
    "invalid_utf8": b'\xff\xfe{"broken":true}',
    "empty": b"",
}

if mode == "unknown_field":
    payload = (
        b'{"protocol_version":1,"request_id":"r","job_id":"j","operation":"o",'
        b'"status":"PROCESS_FAILED","started_at_ms":1,"finished_at_ms":1,'
        b'"worker_receipt":null,'
        b'"error":{"code":"PROCESS_FAILED","message":"m"},'
        b'"sneaky_extra_field":true}'
    )
elif mode == "unknown_nested":
    payload = (
        b'{"protocol_version":1,"request_id":"r","job_id":"j","operation":"o",'
        b'"status":"PROCESS_FAILED","started_at_ms":1,"finished_at_ms":1,'
        b'"worker_receipt":{"protocol_version":1,"hidden_field":1},'
        b'"error":null}'
    )
else:
    payload = PAYLOADS[mode]

if payload:
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()
os._exit(0)
