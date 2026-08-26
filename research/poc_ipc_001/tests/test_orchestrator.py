"""Orchestrator tests: happy path over a REAL subprocess + pre-spawn matrix.

Pre-spawn failures must not spawn any worker: spawn_count == 0 is asserted
explicitly for every invalid request, and no receipt/log evidence is written.
"""

import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _harness as h  # noqa: E402
import errors  # noqa: E402
from orchestrator import CapabilityRegistry, IPCOrchestrator  # noqa: E402


class HappyPathTests(unittest.TestCase):
    def setUp(self):
        self.ws, params = h.make_workspace()
        self.orch = h.make_orchestrator(self.ws)
        self.request = {
            "job_id": self.ws.job_dir.name,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": params,
        }

    def test_full_success_over_real_subprocess(self):
        result = self.orch.execute(self.request, self.ws)
        if not result.ok:
            self.fail(f"expected PASS, got {result.outcome_code}: {result.reason}")
        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(result.spawn_count, 1)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.leaked_threads, 0)
        self.assertFalse(result.timed_out)
        self.assertGreater(result.duration_ms, 0)

        receipt = result.receipt
        self.assertEqual(receipt["status"], "SUCCESS")
        # Non-vacuous assertions from the synthetic operation.
        names = [a["name"] for a in receipt["worker_assertions"]]
        self.assertIn("magic_bytes_match_synthetic", names)
        self.assertTrue(all(a["passed"] is True for a in receipt["worker_assertions"]))
        self.assertTrue(
            all(type(a["passed"]) is bool for a in receipt["worker_assertions"])
        )
        # Read-only operation: empty outputs, input hash matches provisioning.
        self.assertEqual(receipt["outputs"], [])
        ref = receipt["inputs"][0]
        self.assertEqual(ref["path"], f"input/{h.FIXTURE_NAME}")
        self.assertEqual(ref["sha256"], h.expected_fixture_sha())
        # Evidence persisted trusted-side only.
        self.assertIsNotNone(result.persisted_receipt)
        self.assertTrue(result.persisted_receipt.exists())
        self.assertTrue(self.ws.candidates_empty())

    def test_two_sessions_get_distinct_request_ids_and_receipts(self):
        first = self.orch.execute(dict(self.request), self.ws)
        second = self.orch.execute(dict(self.request), self.ws)
        self.assertTrue(first.ok and second.ok)
        self.assertNotEqual(
            first.response["request_id"], second.response["request_id"]
        )
        self.assertNotEqual(first.persisted_receipt, second.persisted_receipt)


class PreSpawnMatrixTests(unittest.TestCase):
    """Invalid requests never spawn; each maps to exactly one taxonomy code."""

    def setUp(self):
        self.ws, params = h.make_workspace()
        self.orch = h.make_orchestrator(self.ws)
        self.params = dict(params)
        self.logs_before = self._evidence_files()

    def _evidence_files(self):
        return sorted(
            list(self.ws.areas["receipts"].glob("*"))
            + list(self.ws.areas["logs"].glob("*"))
        )

    def assert_prespawn_rejected(self, request, expected_code):
        before = self._evidence_files()
        started = time.monotonic()
        result = self.orch.execute(request, self.ws)
        elapsed = time.monotonic() - started
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, expected_code)
        self.assertEqual(result.spawn_count, 0)
        self.assertIsNone(result.child_pid)
        self.assertIsNone(result.response)
        self.assertLess(elapsed, 5.0, "pre-spawn rejection must be immediate")
        self.assertEqual(self._evidence_files(), before,
                         "rejected requests must not create evidence")

    def base(self, **overrides):
        request = {
            "job_id": self.ws.job_dir.name,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": dict(self.params),
        }
        request.update(overrides)
        return request

    def test_oversize_request_limit_exceeded(self):
        huge = "x" * (protocol_MAX_REQUEST_BYTES := 65536)
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": self.params["input_name"],
                                  "padding": huge}),
            errors.REQUEST_LIMIT_EXCEEDED,
        )

    def test_unknown_request_field(self):
        request = self.base()
        request["sneaky"] = True
        self.assert_prespawn_rejected(request, errors.INVALID_REQUEST)

    def test_missing_required_field(self):
        request = self.base()
        del request["operation"]
        self.assert_prespawn_rejected(request, errors.INVALID_REQUEST)

    def test_protocol_version_true(self):
        self.assert_prespawn_rejected(
            self.base(protocol_version=True), errors.INVALID_REQUEST)

    def test_protocol_version_float(self):
        self.assert_prespawn_rejected(
            self.base(protocol_version=1.0), errors.INVALID_REQUEST)

    def test_protocol_version_string(self):
        self.assert_prespawn_rejected(
            self.base(protocol_version="1"), errors.INVALID_REQUEST)

    def test_unsupported_protocol_integer(self):
        self.assert_prespawn_rejected(
            self.base(protocol_version=2), errors.UNSUPPORTED_PROTOCOL_VERSION)

    def test_invalid_uuid_malformed(self):
        self.assert_prespawn_rejected(
            self.base(request_id="not-a-uuid"), errors.INVALID_REQUEST)

    def test_non_v4_uuid_rejected(self):
        self.assert_prespawn_rejected(
            self.base(request_id="a0f0e0d0-1111-1222-8333-444455556666"),
            errors.INVALID_REQUEST,
        )

    def test_uppercase_uuid_rejected(self):
        good = uuid.uuid4()
        self.assert_prespawn_rejected(
            self.base(request_id=str(good).upper()), errors.INVALID_REQUEST)

    def test_invalid_job_id_slash(self):
        self.assert_prespawn_rejected(
            self.base(job_id="A/B"), errors.INVALID_JOB_ID)

    def test_invalid_job_id_dotdot(self):
        self.assert_prespawn_rejected(
            self.base(job_id="JOB..X"), errors.INVALID_JOB_ID)

    def test_invalid_operation_not_in_allowlist(self):
        self.assert_prespawn_rejected(
            self.base(operation="EXECUTE_COMMAND"), errors.INVALID_OPERATION)

    def test_disabled_operation_policy_violation(self):
        registry = CapabilityRegistry()
        registry._ops["INSPECT_SYNTHETIC_INPUT"] = "DISABLED"
        orch = IPCOrchestrator(
            python_executable=sys.executable,
            worker_entry=h.POC_DIR / "worker.py",
            trusted_jobs_root=self.ws.trusted_root,
            registry=registry,
        )
        result = orch.execute(self.base(), self.ws)
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, errors.POLICY_VIOLATION)
        self.assertEqual(result.spawn_count, 0)

    def test_parameters_wrong_shape(self):
        self.assert_prespawn_rejected(
            self.base(parameters=[]), errors.INVALID_REQUEST)

    def test_parameters_unknown_key(self):
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": self.params["input_name"],
                                  "extra": 1}),
            errors.INVALID_REQUEST,
        )

    def test_timeout_below_minimum(self):
        self.assert_prespawn_rejected(
            self.base(timeout_ms=0), errors.INVALID_REQUEST)

    def test_timeout_above_maximum(self):
        self.assert_prespawn_rejected(
            self.base(timeout_ms=600001), errors.INVALID_REQUEST)

    def test_timeout_wrong_type_bool(self):
        self.assert_prespawn_rejected(
            self.base(timeout_ms=True), errors.INVALID_REQUEST)

    def test_input_name_traversal_token(self):
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": "../originals/x.bin"}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_absolute_path(self):
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": str(Path(self.ws.trusted_root) / "x")}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_drive_path_windows(self):
        if os.name != "nt":
            self.skipTest("drive paths are a Windows concern")
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": "C:evil.txt"}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_unc_path_windows(self):
        if os.name != "nt":
            self.skipTest("UNC paths are a Windows concern")
        self.assert_prespawn_rejected(
            self.base(parameters={"input_name": "\\\\srv\\share\\x"}),
            errors.INVALID_REQUEST,
        )


protocol_MAX_REQUEST_BYTES = 65536


if __name__ == "__main__":
    unittest.main()
