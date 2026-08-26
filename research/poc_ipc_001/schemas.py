"""Closed-world schema validators for POC-IPC-001 wire objects.

Implements the ADR-002 field tables exactly: unknown fields reject
recursively, exact-type integers, strict booleans for assertion results,
scalar-only expected/actual, hash format checks, and the Response
presence/null discipline with error.code == status.

Each validator returns (ok: bool, detail: str). detail is diagnostic only.
"""

from protocol import (
    MAX_ASSERTION_COUNT,
    MAX_INPUT_COUNT,
    MAX_OUTPUT_COUNT,
    MAX_STRING_BYTES,
    MAX_TIMEOUT_MS,
    MAX_WARNING_COUNT,
    PROTOCOL_VERSION,
    STATUS_SUCCESS,
    is_exact_int,
    is_strict_bool,
    valid_scalar,
    validate_hash_format,
    validate_request_id,
)


def _check_string(value, detail):
    if type(value) is not str:
        return False, f"{detail}: not a string"
    if len(value.encode("utf-8")) > MAX_STRING_BYTES:
        return False, f"{detail}: string exceeds MAX_STRING_BYTES"
    return True, ""


def _exact_keys(obj, required, where):
    """Closed-world check: the key set must match exactly."""
    if not isinstance(obj, dict):
        return False, f"{where}: not an object"
    keys = set(obj.keys())
    missing = set(required) - keys
    extra = keys - set(required)
    if missing:
        return False, f"{where}: missing fields {sorted(missing)}"
    if extra:
        return False, f"{where}: unknown fields {sorted(extra)}"
    return True, ""


# --------------------------------------------------------------------------
# Request
# --------------------------------------------------------------------------

REQUEST_REQUIRED = {"protocol_version", "request_id", "job_id", "operation", "parameters"}
REQUEST_OPTIONAL = {"timeout_ms"}
REQUEST_ALL = REQUEST_REQUIRED | REQUEST_OPTIONAL


def classify_protocol_version(value):
    """Normative mapping: wrong type -> INVALID_REQUEST; int != 1 -> UNSUPPORTED."""
    from errors import INVALID_REQUEST, UNSUPPORTED_PROTOCOL_VERSION

    if not is_exact_int(value):
        return False, INVALID_REQUEST, "protocol_version must be an exact integer"
    if value != PROTOCOL_VERSION:
        return (
            False,
            UNSUPPORTED_PROTOCOL_VERSION,
            f"protocol_version {value} is not supported (supported: {PROTOCOL_VERSION})",
        )
    return True, None, ""


def validate_request(obj):
    """Full closed-world Request validation.

    Returns (ok, error_code_or_None, detail). Identifier/field violations map
    to their own taxonomy codes per the normative table in ADR-002.
    """
    from errors import INVALID_JOB_ID, INVALID_OPERATION, INVALID_REQUEST
    from protocol import validate_job_id

    if not isinstance(obj, dict):
        return False, INVALID_REQUEST, "request is not an object"

    keys = set(obj.keys())
    unknown = keys - REQUEST_ALL
    if unknown:
        return False, INVALID_REQUEST, f"request: unknown fields {sorted(unknown)}"
    missing = REQUEST_REQUIRED - keys
    if missing:
        return False, INVALID_REQUEST, f"request: missing fields {sorted(missing)}"

    ok, code, detail = classify_protocol_version(obj["protocol_version"])
    if not ok:
        return False, code, detail

    if type(obj["request_id"]) is not str or not validate_request_id(obj["request_id"]):
        return False, INVALID_REQUEST, "request_id violates UUID v4 canonical form"

    if not validate_job_id(obj["job_id"]):
        return False, INVALID_JOB_ID, "job_id violates its contract"

    op = obj["operation"]
    ok, why = _check_string(op, "operation")
    if not ok:
        return False, INVALID_OPERATION, why

    params = obj["parameters"]
    if not isinstance(params, dict):
        return False, INVALID_REQUEST, "parameters must be an object"

    t = obj.get("timeout_ms")
    if t is not None:
        # Reject-out-of-range: full range check belongs to the wire contract.
        if not is_exact_int(t) or t < 1 or t > MAX_TIMEOUT_MS:
            return False, INVALID_REQUEST, "timeout_ms out of range or wrong type"

    # Per-operation parameter schemas live with the operation registry; the
    # generic validator stops here (byte size enforced on serialized form).
    return True, None, ""


# --------------------------------------------------------------------------
# Error / InputRef / OutputRef / Assertion / Receipt
# --------------------------------------------------------------------------

ERROR_FIELDS = {"code", "message"}
INPUT_REF_FIELDS = {"path", "sha256"}
OUTPUT_REF_FIELDS = {"path", "sha256"}
ASSERTION_REQUIRED = {"name", "expected", "actual", "passed"}
ASSERTION_OPTIONAL = {"details"}
ASSERTION_ALL = ASSERTION_REQUIRED | ASSERTION_OPTIONAL


def validate_error_object(obj):
    ok, why = _exact_keys(obj, ERROR_FIELDS, "error")
    if not ok:
        return False, why
    ok, why = _check_string(obj["code"], "error.code")
    if not ok:
        return False, why
    ok, why = _check_string(obj["message"], "error.message")
    if not ok:
        return False, why
    return True, ""


def validate_input_ref(obj):
    ok, why = _exact_keys(obj, INPUT_REF_FIELDS, "InputRef")
    if not ok:
        return False, why
    ok, why = _check_string(obj["path"], "InputRef.path")
    if not ok:
        return False, why
    if not validate_hash_format(obj["sha256"]):
        return False, "InputRef.sha256 violates wire hash format"
    return True, ""


def validate_output_ref(obj):
    ok, why = _exact_keys(obj, OUTPUT_REF_FIELDS, "OutputRef")
    if not ok:
        return False, why
    ok, why = _check_string(obj["path"], "OutputRef.path")
    if not ok:
        return False, why
    if not validate_hash_format(obj["sha256"]):
        return False, "OutputRef.sha256 violates wire hash format"
    return True, ""


def validate_assertion(obj):
    if not isinstance(obj, dict):
        return False, "Assertion: not an object"
    keys = set(obj.keys())
    unknown = keys - ASSERTION_ALL
    if unknown:
        return False, f"Assertion: unknown fields {sorted(unknown)}"
    missing = ASSERTION_REQUIRED - keys
    if missing:
        return False, f"Assertion: missing fields {sorted(missing)}"
    ok, why = _check_string(obj["name"], "Assertion.name")
    if not ok:
        return False, why
    if not valid_scalar(obj["expected"]):
        return False, "Assertion.expected: scalar domain violated"
    if not valid_scalar(obj["actual"]):
        return False, "Assertion.actual: scalar domain violated"
    if not is_strict_bool(obj["passed"]):
        return False, "Assertion.passed: strict boolean required"
    if "details" in obj:
        ok, why = _check_string(obj["details"], "Assertion.details")
        if not ok:
            return False, why
    return True, ""


RECEIPT_FIELDS = {
    "protocol_version",
    "request_id",
    "job_id",
    "operation",
    "status",
    "started_at_ms",
    "finished_at_ms",
    "inputs",
    "outputs",
    "worker_assertions",
    "warnings",
}


def validate_receipt(obj):
    ok, why = _exact_keys(obj, RECEIPT_FIELDS, "receipt")
    if not ok:
        return False, why
    if obj["protocol_version"] != PROTOCOL_VERSION or not is_exact_int(
        obj["protocol_version"]
    ):
        return False, "receipt.protocol_version: exact integer 1 required"
    for field in ("started_at_ms", "finished_at_ms"):
        if not is_exact_int(obj[field]):
            return False, f"receipt.{field}: exact integer required"
    ok, why = _check_string(obj["status"], "receipt.status")
    if not ok:
        return False, why

    inputs = obj["inputs"]
    if not isinstance(inputs, list):
        return False, "receipt.inputs: must be an array"
    if len(inputs) > MAX_INPUT_COUNT:
        return False, f"receipt.inputs exceeds MAX_INPUT_COUNT ({MAX_INPUT_COUNT})"
    for ref in inputs:
        ok, why = validate_input_ref(ref)
        if not ok:
            return False, why

    outputs = obj["outputs"]
    if not isinstance(outputs, list):
        return False, "receipt.outputs: must be an array"
    if len(outputs) > MAX_OUTPUT_COUNT:
        return False, f"receipt.outputs exceeds MAX_OUTPUT_COUNT ({MAX_OUTPUT_COUNT})"
    for ref in outputs:
        ok, why = validate_output_ref(ref)
        if not ok:
            return False, why

    assertions = obj["worker_assertions"]
    if not isinstance(assertions, list):
        return False, "receipt.worker_assertions: must be an array"
    if len(assertions) > MAX_ASSERTION_COUNT:
        return False, (
            f"receipt.worker_assertions exceeds MAX_ASSERTION_COUNT "
            f"({MAX_ASSERTION_COUNT})"
        )
    for assertion in assertions:
        ok, why = validate_assertion(assertion)
        if not ok:
            return False, why

    warnings = obj["warnings"]
    if not isinstance(warnings, list):
        return False, "receipt.warnings: must be an array"
    if len(warnings) > MAX_WARNING_COUNT:
        return False, (
            f"receipt.warnings exceeds MAX_WARNING_COUNT ({MAX_WARNING_COUNT})"
        )
    for item in warnings:
        ok, why = _check_string(item, "receipt.warnings[]")
        if not ok:
            return False, why

    return True, ""


# --------------------------------------------------------------------------
# Response
# --------------------------------------------------------------------------

RESPONSE_FIELDS = {
    "protocol_version",
    "request_id",
    "job_id",
    "operation",
    "status",
    "started_at_ms",
    "finished_at_ms",
    "worker_receipt",
    "error",
}


def _known_status(status: str) -> bool:
    from errors import ALL_CODES

    return status == STATUS_SUCCESS or status in ALL_CODES


def validate_response(obj):
    """Full closed-world Response validation incl. presence/null discipline."""
    from errors import INVALID_RESPONSE

    if not isinstance(obj, dict):
        return False, "response is not an object"
    ok, why = _exact_keys(obj, RESPONSE_FIELDS, "response")
    if not ok:
        return False, why

    if not is_exact_int(obj["protocol_version"]):
        return False, "response.protocol_version: exact integer required"
    if obj["protocol_version"] != PROTOCOL_VERSION:
        return False, "response.protocol_version unsupported"

    for field in ("started_at_ms", "finished_at_ms"):
        if not is_exact_int(obj[field]):
            return False, f"response.{field}: exact integer required"

    status = obj["status"]
    ok, why = _check_string(status, "response.status")
    if not ok:
        return False, why
    if not _known_status(status):
        return False, f"response.status unknown vocabulary: {status!r}"

    receipt = obj["worker_receipt"]
    error = obj["error"]

    if status == STATUS_SUCCESS:
        if error is not None:
            return False, "response.error must be null on SUCCESS"
        if receipt is None:
            return False, "response.worker_receipt missing on SUCCESS"
        ok, why = validate_receipt(receipt)
        if not ok:
            return False, f"receipt invalid: {why}"
        if receipt["status"] != STATUS_SUCCESS:
            return False, "receipt.status must be SUCCESS when response SUCCESS"
    else:
        if receipt is not None:
            return False, "response.worker_receipt must be null on failure"
        if error is None:
            return False, "response.error missing on failure"
        ok, why = validate_error_object(error)
        if not ok:
            return False, why
        if error["code"] != status:
            return False, (
                f"error.code ({error['code']!r}) must equal status ({status!r})"
            )

    return True, ""
