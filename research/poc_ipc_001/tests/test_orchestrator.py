"""Orchestrator tests: happy path over a REAL subprocess + OperationCall
closed-world matrix.

Pre-spawn failures must not spawn any worker: spawn_count == 0 is asserted
explicitly for every invalid OperationCall, and no receipt/log evidence is
written.

NOTE: request_id and protocol_version are trusted-side wire fields. They do
NOT appear in the public OperationCall. Adversarial wire-schema tests for
those fields (invalid UUID, non-v4, uppercase, wrong-typed protocol_version,
unsupported version) live in test_protocol.py against validate_request()
directly. This is intentional: the public API no longer exposes those
fields to the caller.
"""

import hashlib
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
import protocol  # noqa: E402
from orchestrator import CapabilityRegistry, IPCOrchestrator  # noqa: E402
from workspace import JobWorkspace  # noqa: E402


# A second, recognisably different fixture used to prove the worker only
# ever reads from the orchestrator's own trusted root. SHA(A) != SHA(B) by
# construction (different contents).
SECRET_FIXTURE_NAME = "rogue_fixture.txt"
SECRET_FIXTURE_BYTES = b"ROGUE-ROOT-CONTENT-DO-NOT-LEAK" + b"X" * 4096
SECRET_FIXTURE_SHA = hashlib.sha256(SECRET_FIXTURE_BYTES).hexdigest()


def _make_orchestrator_at(root: Path):
    """Build a fresh orchestrator pinned to an arbitrary trusted root."""
    from orchestrator import IPCOrchestrator as _IPC
    return _IPC(
        python_executable=sys.executable,
        worker_entry=h.POC_DIR / "worker.py",
        trusted_jobs_root=root,
    )


class HappyPathTests(unittest.TestCase):
    def setUp(self):
        self.ws, params = h.make_workspace()
        self.orch = h.make_orchestrator(self.ws)
        self.call = {
            "job_id": self.ws.job_dir.name,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": params,
        }

    def test_full_success_over_real_subprocess(self):
        result = self.orch.execute(self.call)
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
        # Operation-specific truthfulness: read-only → exact one input, no
        # outputs, exact SHA, exact path.
        self.assertEqual(receipt["outputs"], [])
        self.assertEqual(len(receipt["inputs"]), 1)
        self.assertEqual(receipt["inputs"][0]["path"],
                         f"input/{h.FIXTURE_NAME}")
        self.assertEqual(receipt["inputs"][0]["sha256"], h.expected_fixture_sha())
        # Evidence persisted trusted-side only.
        self.assertIsNotNone(result.persisted_receipt)
        self.assertTrue(result.persisted_receipt.exists())
        self.assertTrue(self.ws.candidates_empty())

    def test_two_sessions_get_distinct_request_ids_and_receipts(self):
        first = self.orch.execute(dict(self.call))
        second = self.orch.execute(dict(self.call))
        self.assertTrue(first.ok and second.ok)
        self.assertNotEqual(
            first.response["request_id"], second.response["request_id"]
        )
        self.assertNotEqual(first.persisted_receipt, second.persisted_receipt)


class DualRootTrustedRootTests(unittest.TestCase):
    """P0-1 functional proof: worker reads only from the orchestrator root.

    Two roots, two distinct fixtures with distinct SHA-256 hashes. The
    caller (the test) provisions the rogue root with a different file. The
    orchestrator's trusted_jobs_root contains the real fixture. The
    orchestrator runs the worker using the canonical job_id; the worker
    MUST observe the trusted root's bytes (SHA == SHA_TRUSTED), never the
    rogue root's bytes (SHA != SHA_ROGUE).
    """

    def setUp(self):
        self.trusted_root = Path(tempfile.mkdtemp(prefix="pocipc_TRUSTED_"))
        self.rogue_root = Path(tempfile.mkdtemp(prefix="pocipc_ROGUE_"))
        self.job_id = "JOB-DUAL-" + uuid.uuid4().hex[:8].upper()

        # Provision both roots at the SAME job_id the orchestrator will
        # derive, but with different content. The orchestrator we build is
        # bound to trusted_root; the rogue root is the property-deny target.
        self._provision(self.trusted_root, self.job_id, h.FIXTURE_NAME,
                        h.FIXTURE_BYTES)
        self._provision(self.rogue_root, self.job_id, h.FIXTURE_NAME,
                        SECRET_FIXTURE_BYTES)
        assert h.expected_fixture_sha() != SECRET_FIXTURE_SHA

        self.orch = _make_orchestrator_at(self.trusted_root)

    @staticmethod
    def _provision(root, job_id, name, data):
        ws = JobWorkspace(root, job_id)
        ws.ensure_areas()
        ws.provision_input(name, data)

    def test_worker_uses_orchestrator_root_not_caller(self):
        # setUp provisioned the SAME job_id in both roots with different
        # bytes. The orchestrator is bound to trusted_root only, so the
        # worker must read the trusted bytes and never the rogue bytes.
        call = {
            "job_id": self.job_id,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": {"input_name": h.FIXTURE_NAME},
        }
        result = self.orch.execute(call)
        self.assertTrue(
            result.ok,
            f"expected PASS, got {result.outcome_code}: {result.reason}",
        )
        # Truthful receipt: exactly one input pointing at the trusted
        # fixture with the trusted SHA. The rogue SHA must NOT appear.
        self.assertEqual(result.receipt["inputs"], [
            {"path": f"input/{h.FIXTURE_NAME}",
             "sha256": h.expected_fixture_sha()},
        ])
        self.assertNotIn(SECRET_FIXTURE_SHA,
                         result.receipt["inputs"][0]["sha256"])
        # The worker's I/O must not contain any of the rogue root's bytes.
        self.assertNotIn(SECRET_FIXTURE_BYTES, result.stdout_bytes)
        self.assertNotIn(SECRET_FIXTURE_BYTES, result.stderr_bytes)
        # Evidence persisted under the trusted root only.
        self.assertIsNotNone(result.persisted_receipt)
        self.assertIn(
            str(self.trusted_root.resolve()).lower(),
            str(result.persisted_receipt.resolve()).lower(),
        )
        self.assertNotIn(
            str(self.rogue_root.resolve()).lower(),
            str(result.persisted_receipt.resolve()).lower(),
        )

    def test_api_cannot_accept_workspace_from_caller(self):
        """The public execute() takes only an OperationCall. There is no
        API surface that lets a caller pass a JobWorkspace, base_dir, or
        job_root. The constructor binds the orchestrator to a single
        trusted_jobs_root, which is the only path source."""
        import inspect
        sig = inspect.signature(IPCOrchestrator.execute)
        params = list(sig.parameters)
        self.assertEqual(
            params, ["self", "operation_call"],
            "execute() must accept exactly one caller argument: "
            "operation_call. No workspace, no root, no path.",
        )


class OperationCallClosedWorldTests(unittest.TestCase):
    """OperationCall accepts only job_id/operation/parameters/timeout_ms.

    Every other key — including all trusted-side wire fields and all host
    path components — is a pre-spawn INVALID_REQUEST, never silently
    consumed.
    """

    def setUp(self):
        self.ws, self.params = h.make_workspace()
        self.orch = h.make_orchestrator(self.ws)
        self.base_call = {
            "job_id": self.ws.job_dir.name,
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": dict(self.params),
        }

    def _assert_prespawn_rejected(self, call, expected_code):
        before = self._evidence_files()
        started = time.monotonic()
        result = self.orch.execute(call)
        elapsed = time.monotonic() - started
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, expected_code)
        self.assertEqual(result.spawn_count, 0)
        self.assertIsNone(result.child_pid)
        self.assertIsNone(result.response)
        self.assertLess(elapsed, 5.0, "pre-spawn rejection must be immediate")
        self.assertEqual(self._evidence_files(), before,
                         "rejected OperationCall must not create evidence")

    def _evidence_files(self):
        return sorted(
            list(self.ws.areas["receipts"].glob("*"))
            + list(self.ws.areas["logs"].glob("*"))
        )

    # ---- OperationCall: reserved field rejection (P1 request_id) ------

    def test_caller_request_id_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, request_id=str(uuid.uuid4())),
            errors.INVALID_REQUEST,
        )

    def test_caller_protocol_version_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, protocol_version=1),
            errors.INVALID_REQUEST,
        )

    def test_caller_trusted_jobs_root_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call,
                 trusted_jobs_root=str(self.ws.trusted_root)),
            errors.INVALID_REQUEST,
        )

    def test_caller_workspace_object_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, workspace=self.ws),
            errors.INVALID_REQUEST,
        )

    def test_caller_base_dir_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, base_dir=str(self.ws.trusted_root)),
            errors.INVALID_REQUEST,
        )

    def test_caller_cwd_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, cwd=str(self.ws.job_dir)),
            errors.INVALID_REQUEST,
        )

    def test_caller_job_root_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, job_root=str(self.ws.job_dir)),
            errors.INVALID_REQUEST,
        )

    def test_caller_worker_receipt_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, worker_receipt={"probe": 1}),
            errors.INVALID_REQUEST,
        )

    # ---- OperationCall: shape and policy -------------------------------

    def test_unknown_operation_call_field_rejected(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, sneaky=True),
            errors.INVALID_REQUEST,
        )

    def test_missing_required_field_rejected(self):
        call = dict(self.base_call)
        del call["operation"]
        self._assert_prespawn_rejected(call, errors.INVALID_REQUEST)

    def test_oversize_request_limit_exceeded(self):
        huge = "x" * 65536
        self._assert_prespawn_rejected(
            dict(self.base_call,
                 parameters={"input_name": self.params["input_name"],
                             "padding": huge}),
            errors.REQUEST_LIMIT_EXCEEDED,
        )

    def test_disabled_operation_policy_violation(self):
        registry = CapabilityRegistry()
        registry._ops["INSPECT_SYNTHETIC_INPUT"] = "DISABLED"
        orch = IPCOrchestrator(
            python_executable=sys.executable,
            worker_entry=h.POC_DIR / "worker.py",
            trusted_jobs_root=self.ws.trusted_root,
            registry=registry,
        )
        result = orch.execute(self.base_call)
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome_code, errors.POLICY_VIOLATION)
        self.assertEqual(result.spawn_count, 0)

    def test_parameters_wrong_shape(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, parameters=[]),
            errors.INVALID_REQUEST,
        )

    def test_parameters_unknown_key(self):
        self._assert_prespawn_rejected(
            dict(self.base_call,
                 parameters={"input_name": self.params["input_name"],
                             "extra": 1}),
            errors.INVALID_REQUEST,
        )

    def test_timeout_below_minimum(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, timeout_ms=0),
            errors.INVALID_REQUEST,
        )

    def test_timeout_above_maximum(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, timeout_ms=600001),
            errors.INVALID_REQUEST,
        )

    def test_timeout_wrong_type_bool(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, timeout_ms=True),
            errors.INVALID_REQUEST,
        )

    def test_input_name_traversal_token(self):
        self._assert_prespawn_rejected(
            dict(self.base_call,
                 parameters={"input_name": "../originals/x.bin"}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_absolute_path(self):
        self._assert_prespawn_rejected(
            dict(self.base_call,
                 parameters={"input_name": str(Path(self.ws.trusted_root) / "x")}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_drive_path_windows(self):
        if os.name != "nt":
            self.skipTest("drive paths are a Windows concern")
        self._assert_prespawn_rejected(
            dict(self.base_call, parameters={"input_name": "C:evil.txt"}),
            errors.INVALID_REQUEST,
        )

    def test_input_name_unc_path_windows(self):
        if os.name != "nt":
            self.skipTest("UNC paths are a Windows concern")
        self._assert_prespawn_rejected(
            dict(self.base_call, parameters={"input_name": "\\\\srv\\share\\x"}),
            errors.INVALID_REQUEST,
        )

    # ---- identifier and operation pre-spawn matrix ---------------------

    def test_invalid_job_id_slash(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, job_id="A/B"), errors.INVALID_JOB_ID)

    def test_invalid_job_id_dotdot(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, job_id="JOB..X"), errors.INVALID_JOB_ID)

    def test_invalid_operation_not_in_allowlist(self):
        self._assert_prespawn_rejected(
            dict(self.base_call, operation="EXECUTE_COMMAND"),
            errors.INVALID_OPERATION,
        )


protocol_MAX_REQUEST_BYTES = 65536


if __name__ == "__main__":
    unittest.main()
