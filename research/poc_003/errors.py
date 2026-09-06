"""ETEC outcome codes for POC-003.

Source of truth: ADR-004 section "Error taxonomy partition".

ADR-004 E8 states that the ADR-002 taxonomy is *partitioned, not inherited
wholesale*: nine codes are transport- or receipt-bound and therefore
"must not be declared as part of an ETEC profile's outcome set". They are
listed here as NOT_APPLICABLE so that a test can assert the profile never
emits them. A code that cannot fire is worse than an absent code: in a
fail-closed taxonomy it reads as a handled failure mode and inflates
apparent coverage without adding any.
"""

from __future__ import annotations

# --- Inherited from ADR-002 and applicable under ETEC -----------------------
PROCESS_TIMEOUT = "PROCESS_TIMEOUT"
PROCESS_FAILED = "PROCESS_FAILED"
OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
WORKSPACE_VIOLATION = "WORKSPACE_VIOLATION"
POLICY_VIOLATION = "POLICY_VIOLATION"
INTERNAL_ERROR = "INTERNAL_ERROR"

# --- ETEC-specific, introduced by ADR-004 ----------------------------------
PRE_EXISTING_OUTPUT_PRESENT = "PRE_EXISTING_OUTPUT_PRESENT"
EXPECTED_OUTPUT_MISSING = "EXPECTED_OUTPUT_MISSING"
OUTPUT_HASH_MISMATCH = "OUTPUT_HASH_MISMATCH"
INPUT_HASH_MISMATCH = "INPUT_HASH_MISMATCH"
UNEXPECTED_OUTPUT_PRESENT = "UNEXPECTED_OUTPUT_PRESENT"
TOOL_DIAGNOSTICS_REJECTED = "TOOL_DIAGNOSTICS_REJECTED"
DETERMINISM_MISMATCH = "DETERMINISM_MISMATCH"
EXECUTABLE_HASH_MISMATCH = "EXECUTABLE_HASH_MISMATCH"
DESCENDANT_PROCESS_SURVIVED = "DESCENDANT_PROCESS_SURVIVED"

INHERITED: frozenset[str] = frozenset(
    {
        PROCESS_TIMEOUT,
        PROCESS_FAILED,
        OUTPUT_LIMIT_EXCEEDED,
        WORKSPACE_VIOLATION,
        POLICY_VIOLATION,
        INTERNAL_ERROR,
    }
)

ETEC_SPECIFIC: frozenset[str] = frozenset(
    {
        PRE_EXISTING_OUTPUT_PRESENT,
        EXPECTED_OUTPUT_MISSING,
        OUTPUT_HASH_MISMATCH,
        INPUT_HASH_MISMATCH,
        UNEXPECTED_OUTPUT_PRESENT,
        TOOL_DIAGNOSTICS_REJECTED,
        DETERMINISM_MISMATCH,
        EXECUTABLE_HASH_MISMATCH,
        DESCENDANT_PROCESS_SURVIVED,
    }
)

#: Nine ADR-002 codes that are structurally unreachable without a wire
#: transport or a worker receipt. Declared here only so the profile can be
#: asserted *never* to produce them.
NOT_APPLICABLE: frozenset[str] = frozenset(
    {
        "INVALID_REQUEST",
        "REQUEST_LIMIT_EXCEEDED",
        "UNSUPPORTED_PROTOCOL_VERSION",
        "INVALID_JOB_ID",
        "INVALID_OPERATION",
        "PIPE_WRITE_FAILED",
        "INVALID_RESPONSE",
        "RECEIPT_MISMATCH",
        "ASSERTION_FAILED",
    }
)

DECLARED_OUTCOME_SET: frozenset[str] = INHERITED | ETEC_SPECIFIC


class EtecFailure(Exception):
    """A fail-closed outcome. Carries the ADR-004 code and a detail string."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in DECLARED_OUTCOME_SET:
            raise ValueError(f"outcome code not declared by this profile: {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}
