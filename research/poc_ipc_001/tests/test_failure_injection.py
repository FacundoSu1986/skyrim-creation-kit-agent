"""Failure-injection matrix over REAL subprocesses (no mocks of Popen).

Every case spawns an actual worker/helper process and asserts the exact
taxonomy code the orchestrator must produce. This is the acceptance surface
defined by ADR-002. Modes travel through sentinel files in the job temp dir
(explicit readiness channel; no sleeps-as-synchronization).
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _harness as h  # noqa: E402
import errors  # noqa: E402

SHORT_DEADLINE_MS = 1200


class InjectionTestCase(unittest.TestCase):
    """Runs a helper script through the REAL orchestrator machinery."""

    def setUp(self):
        self.ws, self.params = h.make_workspace()

    def run_helper(self, script_name, mode=None, timeout_ms=None,
                   extra_sentinel=None):
        from orchestrator import IPCOrchestrator

        if mode is not None:
            self.ws.job_temp().mkdir(parents=True, exist_ok=True)
            (self.ws.job_temp() / "helper_mode.txt").write_text(mode)
        if extra_sentinel:
            for name, value in extra_sentinel.items():
                (self.ws.job_temp() / name).write_text(value)

        orch = IPCOrchestrator(
            python_executable=sys.executable,
            worker_entry=h.helper(script_name),
            trusted_jobs_root=self.ws.trusted_root,
            registry=self.orch_registry(),
        )
        call = {
            "job_id": self.ws.job_dir.name,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": dict(self.params),
        }
        if timeout_ms is not None:
            call["timeout_ms"] = timeout_ms
        started = time.monotonic()
        result = orch.execute(call)
        result.wall_elapsed = time.monotonic() - started
        return result

    @staticmethod
    def orch_registry():
        from orchestrator import CapabilityRegistry

        return CapabilityRegistry()


class StdinInjectionTests(InjectionTestCase):
    def test_worker_never_reads_stdin_times_out_fail_closed(self):
        result = self.run_helper("never_read_stdin.py", timeout_ms=SHORT_DEADLINE_MS)
        self.assertEqual(result.outcome_code, errors.PROCESS_TIMEOUT)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.ok)
        self.assertIsNone(result.response)
        # Orchestrator returned promptly after the deadline; never hung.
        self.assertLess(result.wall_elapsed, SHORT_DEADLINE_MS / 1000 + 6.0)

    def test_threads_do_not_survive_stdin_timeout_session(self):
        result = self.run_helper("never_read_stdin.py", timeout_ms=SHORT_DEADLINE_MS)
        self.assertEqual(result.leaked_threads, 0,
                         "pumps/writer must exit via deadline polling")

    def test_worker_reads_stdin_too_slowly(self):
        result = self.run_helper("slow_read_stdin.py", timeout_ms=SHORT_DEADLINE_MS)
        self.assertIn(result.outcome_code,
                      (errors.PROCESS_TIMEOUT, errors.PIPE_WRITE_FAILED))
        self.assertFalse(result.ok)

    def test_child_closes_stdin_immediately_fail_closed(self):
        # Protocol-v1 requests are far smaller than the OS pipe buffer, so an
        # immediate-close collapses deterministically to INVALID_RESPONSE
        # (empty stdout, clean exit): the parent's single write succeeds into
        # the buffer before the child dies, so no BrokenPipe is observable.
        # PIPE_WRITE_FAILED stays implemented for observed mid-delivery
        # breakage. Both outcomes are fail-closed; neither hangs.
        result = self.run_helper("close_stdin.py")
        self.assertIn(result.outcome_code,
                      (errors.PIPE_WRITE_FAILED, errors.INVALID_RESPONSE))
        self.assertFalse(result.ok)
        self.assertLess(result.wall_elapsed, 5.0)


class StreamFloodingTests(InjectionTestCase):
    def test_stdout_flooding_hits_cap_and_fails_closed(self):
        result = self.run_helper("spam_stdout.py", timeout_ms=8000)
        self.assertEqual(result.outcome_code, errors.OUTPUT_LIMIT_EXCEEDED)
        self.assertTrue(result.output_limit_hit)
        from protocol import MAX_STDOUT_BYTES

        self.assertLessEqual(len(result.stdout_bytes),
                             MAX_STDOUT_BYTES + protocol_chunk())

    def test_stderr_flooding_hits_cap_and_fails_closed(self):
        result = self.run_helper("spam_stderr.py", timeout_ms=8000)
        self.assertEqual(result.outcome_code, errors.OUTPUT_LIMIT_EXCEEDED)


def protocol_chunk():
    from protocol import IO_CHUNK_BYTES

    return IO_CHUNK_BYTES


class StreamMalformationTests(InjectionTestCase):
    def assert_invalid_response(self, mode):
        result = self.run_helper("malformed_json.py", mode=mode, timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE,
                         f"mode={mode}: {result.reason[:140]}")
        self.assertFalse(result.ok)

    def test_malformed_json_rejected(self):
        self.assert_invalid_response("invalid_json")

    def test_nan_literal_rejected(self):
        self.assert_invalid_response("nan")

    def test_infinity_literal_rejected(self):
        self.assert_invalid_response("infinity")

    def test_duplicate_json_keys_rejected(self):
        self.assert_invalid_response("duplicate_keys")

    def test_trailing_json_data_rejected(self):
        self.assert_invalid_response("trailing")

    def test_invalid_utf8_rejected(self):
        self.assert_invalid_response("invalid_utf8")

    def test_empty_stdout_zero_exit_rejected(self):
        self.assert_invalid_response("empty")

    def test_unknown_response_field_rejected(self):
        self.assert_invalid_response("unknown_field")

    def test_unknown_nested_receipt_field_rejected(self):
        self.assert_invalid_response("unknown_nested")


class ProcessFaultTests(InjectionTestCase):
    def test_nonzero_exit_with_plausible_success_json_fails(self):
        result = self.run_helper(
            "process_faults.py", mode="nonzero_plausible_success", timeout_ms=15000
        )
        self.assertEqual(result.outcome_code, errors.PROCESS_FAILED)
        self.assertEqual(result.exit_code, 3)

    def test_crash_after_read_fails(self):
        result = self.run_helper(
            "process_faults.py", mode="crash_after_read", timeout_ms=15000
        )
        self.assertEqual(result.outcome_code, errors.PROCESS_FAILED)

    def test_zero_exit_with_invalid_json_is_invalid_response(self):
        result = self.run_helper(
            "process_faults.py", mode="zero_exit_invalid", timeout_ms=15000
        )
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE)


class CorrelationTests(InjectionTestCase):
    def assert_correlation_mismatch(self, level, field):
        result = self.run_helper(
            "wrong_correlation.py",
            mode=field,
            timeout_ms=15000,
            extra_sentinel={"helper_level.txt": level},
        )
        self.assertEqual(result.outcome_code, errors.RECEIPT_MISMATCH,
                         f"{level}.{field}: {result.reason[:140]}")

    def test_response_request_id_corrupted(self):
        self.assert_correlation_mismatch("response", "request_id")

    def test_response_job_id_corrupted(self):
        self.assert_correlation_mismatch("response", "job_id")

    def test_response_operation_corrupted(self):
        self.assert_correlation_mismatch("response", "operation")

    def test_receipt_request_id_corrupted(self):
        self.assert_correlation_mismatch("receipt", "request_id")

    def test_receipt_job_id_corrupted(self):
        self.assert_correlation_mismatch("receipt", "job_id")

    def test_receipt_operation_corrupted(self):
        self.assert_correlation_mismatch("receipt", "operation")


class ReceiptShapeTests(InjectionTestCase):
    def assert_code(self, mode, expected_code):
        result = self.run_helper("receipt_shape.py", mode=mode, timeout_ms=15000)
        self.assertEqual(result.outcome_code, expected_code,
                         f"mode={mode}: {result.reason[:140]}")
        self.assertFalse(result.ok)

    def test_missing_receipt_on_success_rejected(self):
        self.assert_code("missing_receipt", errors.INVALID_RESPONSE)

    def test_null_error_on_success_rejected(self):
        self.assert_code("null_error_on_success", errors.INVALID_RESPONSE)

    def test_failed_receipt_with_success_response_rejected(self):
        self.assert_code("failed_receipt", errors.INVALID_RESPONSE)

    def test_unknown_receipt_field_rejected(self):
        self.assert_code("unknown_receipt_field", errors.INVALID_RESPONSE)

    def test_bad_sha_uppercase_rejected(self):
        self.assert_code("bad_sha_upper", errors.INVALID_RESPONSE)

    def test_bad_sha_short_rejected(self):
        self.assert_code("bad_sha_short", errors.INVALID_RESPONSE)

    def test_bad_sha_prefix_rejected(self):
        self.assert_code("bad_sha_prefix", errors.INVALID_RESPONSE)

    def test_bad_sha_whitespace_rejected(self):
        self.assert_code("bad_sha_whitespace", errors.INVALID_RESPONSE)

    def test_output_path_outside_candidates_rejected(self):
        self.assert_code("output_outside_candidates", errors.WORKSPACE_VIOLATION)

    def test_error_code_not_equal_status_rejected(self):
        self.assert_code("error_code_mismatch", errors.INVALID_RESPONSE)

    def test_too_many_inputs_rejected(self):
        self.assert_code("too_many_inputs", errors.INVALID_RESPONSE)

    def test_too_many_outputs_rejected(self):
        self.assert_code("too_many_outputs", errors.INVALID_RESPONSE)

    def test_too_many_warnings_rejected(self):
        self.assert_code("too_many_warnings", errors.INVALID_RESPONSE)

    def test_too_many_assertions_rejected(self):
        self.assert_code("too_many_assertions", errors.INVALID_RESPONSE)


class AssertionDefectTests(InjectionTestCase):
    def test_empty_required_assertions_rejected(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="empty_assertions", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.ASSERTION_FAILED)

    def test_passed_false_yields_assertion_failed(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="passed_false", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.ASSERTION_FAILED)
        self.assertIn("probe", result.reason)

    def test_passed_int_one_rejected_as_schema_violation(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="passed_int_one", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE)

    def test_passed_int_zero_rejected_as_schema_violation(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="passed_int_zero", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE)

    def test_nested_expected_rejected_as_scalar_violation(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="nested_expected", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE)

    def test_float_actual_rejected_as_scalar_violation(self):
        result = self.run_helper("assertion_defects.py",
                                 mode="float_actual", timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.INVALID_RESPONSE)


class ValidErrorResponseTests(InjectionTestCase):
    """P0#2: a worker can return a perfectly schema-valid error response.

    The orchestrator must accept it without indexing into the (null)
    worker_receipt and must classify the session as the worker's reported
    status, not raise an exception.
    """

    def test_workspace_violation_error_response_is_handled(self):
        result = self.run_helper(
            "valid_error_response.py",
            mode="valid_error_workspace_violation", timeout_ms=15000,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIsNone(result.response,
                          "a non-SUCCESS response must not be promoted to "
                          "an executable response")
        self.assertIsNone(result.receipt)


class ReceiptTruthfulnessTests(InjectionTestCase):
    """P0#3: the worker cannot self-declare success by padding the receipt.

    The orchestrator independently re-derives workspace truth; for a
    read-only operation the receipt must declare exactly one input (the
    one the orchestrator provisioned) and no outputs.
    """

    def test_nonempty_outputs_in_readonly_receipt_rejected(self):
        result = self.run_helper("receipt_shape.py",
                                 mode="nonempty_outputs_readonly",
                                 timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIn("outputs", result.reason)

    def test_extra_input_ref_in_receipt_rejected(self):
        result = self.run_helper("receipt_shape.py",
                                 mode="extra_input_ref",
                                 timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIn("inputs", result.reason)

    def test_missing_input_ref_in_receipt_rejected(self):
        result = self.run_helper("receipt_shape.py",
                                 mode="missing_input_ref",
                                 timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIn("inputs", result.reason)

    def test_wrong_input_path_in_receipt_rejected(self):
        result = self.run_helper("receipt_shape.py",
                                 mode="wrong_input_path",
                                 timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIn("inputs", result.reason)

    def test_wrong_input_sha_in_receipt_rejected(self):
        result = self.run_helper("receipt_shape.py",
                                 mode="wrong_input_sha",
                                 timeout_ms=15000)
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIn("inputs", result.reason)


class ValidErrorResponseTests(InjectionTestCase):
    """P0-2: a worker can return a perfectly schema-valid error Response.

    The orchestrator must classify the session as the worker's reported
    status, never index into response["worker_receipt"] (which is null
    by schema), and never raise an exception. Response-level correlation
    MUST still be enforced: an error Response with a wrong job_id is
    RECEIPT_MISMATCH, not the worker's claimed status.
    """

    def test_workspace_violation_error_response_handled(self):
        result = self.run_helper(
            "valid_error_response.py",
            mode="valid_error_workspace_violation", timeout_ms=15000,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.outcome_code, errors.WORKSPACE_VIOLATION)
        self.assertIsNotNone(result.response,
                             "schema-valid Response is preserved for evidence")
        self.assertEqual(result.response["status"],
                         errors.WORKSPACE_VIOLATION)
        self.assertIsNone(result.response["worker_receipt"])
        self.assertEqual(result.response["error"]["code"],
                         errors.WORKSPACE_VIOLATION)
        self.assertIsNone(result.receipt)
        self.assertEqual(result.spawn_count, 1)

    def test_invalid_operation_error_response_handled(self):
        result = self.run_helper(
            "valid_error_response.py",
            mode="valid_error_invalid_operation", timeout_ms=15000,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, errors.INVALID_OPERATION)
        self.assertIsNotNone(result.response)
        self.assertIsNone(result.receipt)

    def test_error_response_with_wrong_job_id_is_receipt_mismatch(self):
        """A schema-valid error Response that does not correlate to the
        trusted request is RECEIPT_MISMATCH, not a PASS-graded error.
        Defense against an adversarial worker that tries to borrow a
        different job_id (for example, a previously successful one)."""
        result = self.run_helper(
            "valid_error_response.py",
            mode="wrong_job_id",
            extra_sentinel={"helper_wrong_job.txt": "1"},
            timeout_ms=15000,
        )
        self.assertEqual(result.outcome_code, errors.RECEIPT_MISMATCH)
        self.assertIn("job_id", result.reason)

    def test_error_response_with_wrong_request_id_is_receipt_mismatch(self):
        result = self.run_helper(
            "valid_error_response.py",
            mode="wrong_request_id",
            timeout_ms=15000,
        )
        self.assertEqual(result.outcome_code, errors.RECEIPT_MISMATCH)


class OutputLimitEarlyAbortTests(InjectionTestCase):
    """P1 OUTPUT_LIMIT must abort immediately, not wait for the deadline."""

    def test_stdout_flood_aborts_well_before_deadline(self):
        timeout_ms = 8000
        started = time.monotonic()
        result = self.run_helper("spam_stdout.py", timeout_ms=timeout_ms)
        elapsed = time.monotonic() - started
        self.assertEqual(result.outcome_code, errors.OUTPUT_LIMIT_EXCEEDED)
        self.assertFalse(result.ok)
        self.assertTrue(result.output_limit_hit)
        self.assertEqual(result.leaked_threads, 0)
        # The helper floods the moment it starts; the orchestrator must
        # detect the cap and terminate long before the configured timeout.
        self.assertLess(
            elapsed, timeout_ms / 1000 / 2.0,
            f"output_limit must trigger early termination; elapsed={elapsed:.3f}s",
        )

    def test_stderr_flood_aborts_well_before_deadline(self):
        timeout_ms = 8000
        started = time.monotonic()
        result = self.run_helper("spam_stderr.py", timeout_ms=timeout_ms)
        elapsed = time.monotonic() - started
        self.assertEqual(result.outcome_code, errors.OUTPUT_LIMIT_EXCEEDED)
        self.assertFalse(result.ok)
        self.assertTrue(result.output_limit_hit)
        self.assertEqual(result.leaked_threads, 0)
        self.assertLess(
            elapsed, timeout_ms / 1000 / 2.0,
            f"output_limit must trigger early termination; elapsed={elapsed:.3f}s",
        )


if __name__ == "__main__":
    unittest.main()
