"""Trusted worker entry point for POC-IPC-001.

One-shot process: reads exactly one strict JSON Request from stdin, executes
the allowlisted synthetic operation, emits one strict JSON Response on stdout,
exits 0 (protocol-clean termination; application-level failures travel in
response.status). Nonzero exit only on real crashes.

The worker treats its own output as untrusted bytes destined for validation —
it never writes receipts/, reports/, or logs/ directly.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import errors  # noqa: E402
import protocol  # noqa: E402
import schemas  # noqa: E402
import synthetic_operation  # noqa: E402

OPERATIONS = {
    synthetic_operation.OPERATION_NAME: synthetic_operation,
}


def _fail_response(request_like, code, message, started_ms):
    rid = request_like.get("request_id") if isinstance(request_like, dict) else None
    jid = request_like.get("job_id") if isinstance(request_like, dict) else None
    op = request_like.get("operation") if isinstance(request_like, dict) else None
    return {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "request_id": rid if isinstance(rid, str) else "",
        "job_id": jid if isinstance(jid, str) else "",
        "operation": op if isinstance(op, str) else "",
        "status": code,
        "started_at_ms": started_ms,
        "finished_at_ms": int(time.time() * 1000),
        "worker_receipt": None,
        "error": {"code": code, "message": message[: protocol.MAX_STRING_BYTES]},
    }


def _read_bounded_stdin():
    """Read at most MAX_REQUEST_BYTES+1 bytes from stdin until EOF."""
    chunks = []
    total = 0
    while True:
        chunk = sys.stdin.buffer.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > protocol.MAX_REQUEST_BYTES:
            return None  # oversize for the worker as well
        chunks.append(chunk)
    return b"".join(chunks)


def main() -> int:
    started_ms = int(time.time() * 1000)
    raw = _read_bounded_stdin()
    if raw is None:
        response = _fail_response(
            {}, errors.REQUEST_LIMIT_EXCEEDED, "request exceeds MAX_REQUEST_BYTES", started_ms
        )
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    # 1. Strict decode + closed-world schema validation.
    try:
        request = protocol.strict_json_loads(raw)
    except ValueError as exc:
        response = _fail_response({}, errors.INVALID_REQUEST, f"strict JSON: {exc}", started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    ok, code, detail = schemas.validate_request(request)
    if not ok:
        response = _fail_response(request, code, detail[:512], started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    operation = OPERATIONS.get(request["operation"])
    if operation is None:
        response = _fail_response(
            request, errors.INVALID_OPERATION, "operation not implemented by this worker",
            started_ms,
        )
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    ok, detail = operation.validate_parameters(request["parameters"])
    if not ok:
        response = _fail_response(request, errors.INVALID_REQUEST, detail[:512], started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    job_root = None
    for index, arg in enumerate(sys.argv[:-1]):
        if arg == "--job-root":
            job_root = Path(sys.argv[index + 1])
            break
    if job_root is None or not Path(job_root).is_absolute():
        response = _fail_response(
            request, errors.INTERNAL_ERROR, "worker invoked without trusted --job-root",
            started_ms,
        )
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    # 2. Execute the read-only synthetic operation.
    try:
        receipt = operation.execute(job_root, request["parameters"])
    except PermissionError as exc:
        response = _fail_response(request, errors.WORKSPACE_VIOLATION, str(exc)[:512], started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0
    except FileNotFoundError as exc:
        response = _fail_response(request, errors.WORKSPACE_VIOLATION, str(exc)[:512], started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0
    except Exception as exc:  # noqa: BLE001 — single worker boundary, fail-closed
        response = _fail_response(request, errors.INTERNAL_ERROR, repr(exc)[:512], started_ms)
        sys.stdout.buffer.write(protocol.strict_json_dumps(response))
        return 0

    receipt["protocol_version"] = protocol.PROTOCOL_VERSION
    receipt["request_id"] = request["request_id"]
    receipt["job_id"] = request["job_id"]
    receipt["operation"] = request["operation"]
    receipt["status"] = "SUCCESS"
    receipt["finished_at_ms"] = int(time.time() * 1000)
    receipt["started_at_ms"] = started_ms

    response = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "request_id": request["request_id"],
        "job_id": request["job_id"],
        "operation": request["operation"],
        "status": "SUCCESS",
        "started_at_ms": started_ms,
        "finished_at_ms": receipt["finished_at_ms"],
        "worker_receipt": receipt,
        "error": None,
    }

    sys.stdout.buffer.write(protocol.strict_json_dumps(response))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
