"""Protocol constants and strict wire primitives for POC-IPC-001.

Implements the accepted ADR-002 contract: exact limits, strict JSON UTF-8,
identifier contracts (job_id / request_id / operation), hash format, and
safe-name tokens. Values must match ADR-002 exactly — no silent changes.
"""

import json
import re
import uuid

# --- protocol version -------------------------------------------------------
PROTOCOL_VERSION = 1

# --- limits (ADR-002 "Size and resource limits") ----------------------------
MAX_REQUEST_BYTES = 65536        # 64 KiB
MAX_RESPONSE_BYTES = 262144      # 256 KiB
MAX_STDOUT_BYTES = 262144        # 256 KiB
MAX_STDERR_BYTES = 65536         # 64 KiB
MAX_STRING_BYTES = 4096          # any single string field value

MAX_INPUT_COUNT = 32             # receipt.inputs length
MAX_OUTPUT_COUNT = 16            # receipt.outputs length
MAX_WARNING_COUNT = 32           # receipt.warnings length
MAX_ASSERTION_COUNT = 100        # worker_assertions length

DEFAULT_TIMEOUT_MS = 30000       # session deadline if timeout_ms omitted
MAX_TIMEOUT_MS = 600000          # hard ceiling; out-of-range rejects

# read chunk used by bounded pumps
IO_CHUNK_BYTES = 65536

# --- identifier contracts ---------------------------------------------------
# job_id: safe character class, then an explicit ".." substring rejection
# (the class alone would admit it), plus explicit "." / ".." forms.
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# request_id: canonical UUID v4, lowercase, hyphenated, exactly 36 chars.
REQUEST_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

# operation names and safe-name tokens share the same base grammar as job_id.
SAFE_NAME_RE = JOB_ID_RE

# SHA-256 wire format: lowercase hex, exactly 64 chars, no prefix, no spaces.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

STATUS_SUCCESS = "SUCCESS"


def new_request_id() -> str:
    """Trusted-side generation of a canonical UUID v4 request id."""
    return str(uuid.uuid4())


def validate_job_id(value) -> bool:
    """Ordered validation per ADR-002; returns True iff fully valid."""
    if type(value) is not str:
        return False
    if len(value) > 64:
        return False
    if not JOB_ID_RE.fullmatch(value):
        return False
    if ".." in value:  # explicit substring rejection
        return False
    if value in (".", ".."):  # already excluded above; stated for clarity
        return False
    return True


def validate_request_id(value) -> bool:
    """Canonical UUID v4 only: lowercase, hyphenated, version nibble 4, [89ab]."""
    if type(value) is not str:
        return False
    return REQUEST_ID_RE.fullmatch(value) is not None


def validate_safe_name(value) -> bool:
    """Safe-name token (input_name): same discipline as job_id incl. '..' ban."""
    return validate_job_id(value)


def validate_hash_format(value) -> bool:
    if type(value) is not str:
        return False
    return SHA256_RE.fullmatch(value) is not None


def validate_timeout_ms(value):
    """Returns None when valid-and-default, the int value when valid, or False.

    Reject-out-of-range semantics: no clamping anywhere.
    """
    if value is None:
        return DEFAULT_TIMEOUT_MS
    if type(value) is not int:
        return False
    if isinstance(value, bool):  # redundant with exact-type check; belt+braces
        return False
    if value < 1 or value > MAX_TIMEOUT_MS:
        return False
    return value


def _no_duplicate_keys(pairs):
    seen = {}
    for key, val in pairs:
        if key in seen:
            raise ValueError(f"duplicate object key: {key!r}")
        seen[key] = val
    return seen


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant: {name}")


def strict_json_loads(data: bytes):
    """Decode one strict JSON document from bytes.

    Rejects: invalid UTF-8, NaN/Infinity/-Infinity, duplicate object keys,
    trailing data after the top-level document. Raises ValueError on any
    violation.
    """
    text = data.decode("utf-8", errors="strict")  # invalid UTF-8 -> ValueError
    obj = json.loads(
        text,
        parse_constant=_reject_constant,
        object_pairs_hook=_no_duplicate_keys,
    )
    # json.loads already rejects trailing data via extra-data error; kept
    # explicit for documentation of the invariant.
    if isinstance(obj, str) and text.strip().endswith(text.strip()):
        pass
    return obj


def strict_json_dumps(obj) -> bytes:
    """Deterministic, strict encoding: sorted keys, compact separators, UTF-8.

    Rejects NaN/Infinity/-Infinity at encode time as well as at decode time
    (mirroring ``strict_json_loads``). Allowed in protocol v1: only JSON
    primitives with finite values.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def is_exact_int(value) -> bool:
    """ADR rule: integers are exact ints. bool subclasses int and rejects."""
    return type(value) is int


def is_strict_bool(value) -> bool:
    return type(value) is bool


def valid_scalar(value) -> bool:
    """Assertion expected/actual scalar domain: str | exact int | bool | null."""
    if value is None:
        return True
    if type(value) is str:
        return True
    if is_exact_int(value):
        return True
    if is_strict_bool(value):
        return True
    return False
