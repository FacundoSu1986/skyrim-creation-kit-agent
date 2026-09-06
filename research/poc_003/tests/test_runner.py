"""Runner tests against a controlled stand-in executable.

The real PapyrusCompiler.exe is never used here. python.exe stands in, driven
by ``_fake.py``, so spawn, deadline, capture, cleanup and descendant behaviour
are still exercised on real processes.
"""

import os
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from poc_003 import errors, jobobject, profile, proctree, runner, snapshot  # noqa: E402
from _harness import FAKE_TOKEN, TempWorkspace  # noqa: E402


def _run(ws: TempWorkspace, behaviour: str, **kwargs) -> runner.RunEvidence:
    ws.install_fake(behaviour)
    request = runner.RunRequest(operation=profile.OP_COMPILE_FIXTURE, source_token=FAKE_TOKEN, **kwargs)
    return runner.run_once(ws.config, ws.ws, request)


class HappyPathTests(unittest.TestCase):
    def test_success_produces_contained_hashed_artifact(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "success", deadline_s=30.0)
            self.assertTrue(ev.success, msg=str(ev.failures))
            self.assertIsNone(ev.outcome_code)
            self.assertEqual(0, ev.details["exit_code"])
            self.assertEqual("candidates/Poc003Minimal.pex", ev.details["expected_output_rel"])
            self.assertTrue(ev.details["output_size"] > 0)
            self.assertEqual(ev.details["output_sha256"], ev.details["output_sha256_recomputed"])
            self.assertEqual([], ev.details["unexpected_outputs"])

    def test_argv_is_shell_free_and_shape_fixed(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "success", deadline_s=30.0)
            self.assertFalse(ev.details["shell"])
            argv = ev.details["argv_sanitized"]
            self.assertEqual(5, len(argv))
            self.assertEqual("<PAPYRUS_COMPILER_EXE>", argv[0])

    def test_evidence_is_written_under_logs(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "success", deadline_s=30.0)
            path = runner.write_evidence(ws.ws, ev)
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(path.replace("\\", "/").endswith("/logs/evidence.json"))


class PreSpawnGateTests(unittest.TestCase):
    def test_rejects_unknown_profile(self):
        """ETEC profiles are individually named; there is no dispatcher here."""
        with TempWorkspace() as ws:
            ws.install_fake("success")
            request = runner.RunRequest(
                profile_id="PAPYRUS_COMPILE_ANYTHING_V2",
                operation=profile.OP_COMPILE_FIXTURE,
                source_token=FAKE_TOKEN,
            )
            ev = runner.run_once(ws.config, ws.ws, request)
            self.assertEqual(errors.POLICY_VIOLATION, ev.outcome_code)
            self.assertFalse(ev.success)
            self.assertEqual({}, ev.details.get("argv_sanitized", {}))

    def test_rejects_unknown_operation(self):
        with TempWorkspace() as ws:
            ws.install_fake("success")
            request = runner.RunRequest(operation="run_any_command", source_token=FAKE_TOKEN)
            ev = runner.run_once(ws.config, ws.ws, request)
            self.assertEqual(errors.POLICY_VIOLATION, ev.outcome_code)
            self.assertFalse(ev.success)

    def test_rejects_executable_hash_mismatch(self):
        with TempWorkspace() as ws:
            cfg = profile.LocalConfig(
                executable=ws.config.executable,
                executable_sha256="f" * 64,
                flags=ws.config.flags,
                flags_sha256=ws.config.flags_sha256,
            )
            ws.install_fake("success")
            ev = runner.run_once(cfg, ws.ws, runner.RunRequest(deadline_s=30.0))
            self.assertEqual(errors.EXECUTABLE_HASH_MISMATCH, ev.outcome_code)

    def test_rejects_flags_hash_mismatch(self):
        with TempWorkspace() as ws:
            cfg = profile.LocalConfig(
                executable=ws.config.executable,
                executable_sha256=ws.config.executable_sha256,
                flags=ws.config.flags,
                flags_sha256="e" * 64,
            )
            ws.install_fake("success")
            ev = runner.run_once(cfg, ws.ws, runner.RunRequest(deadline_s=30.0))
            self.assertEqual(errors.INPUT_HASH_MISMATCH, ev.outcome_code)

    def test_rejects_pre_existing_output(self):
        with TempWorkspace() as ws:
            with open(os.path.join(ws.ws.candidates, "Poc003Minimal.pex"), "wb") as fh:
                fh.write(b"stale")
            ev = _run(ws, "success", deadline_s=30.0)
            self.assertEqual(errors.PRE_EXISTING_OUTPUT_PRESENT, ev.outcome_code)

    def test_rejects_missing_source_script(self):
        with TempWorkspace() as ws:
            ev = runner.run_once(
                ws.config, ws.ws, runner.RunRequest(source_token="Poc003Hang", deadline_s=30.0)
            )
            self.assertEqual(errors.POLICY_VIOLATION, ev.outcome_code)


class OutputGateTests(unittest.TestCase):
    def test_missing_output_is_not_success(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "no_output", deadline_s=30.0)
            self.assertEqual(errors.EXPECTED_OUTPUT_MISSING, ev.outcome_code)
            self.assertFalse(ev.success)

    def test_empty_output_is_not_success(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "empty_output", deadline_s=30.0)
            self.assertEqual(errors.EXPECTED_OUTPUT_MISSING, ev.outcome_code)

    def test_input_mutation_is_detected_even_when_the_tool_fails(self):
        """A failing tool can still have mutated a declared read-only input.

        Criterion 11 must therefore be measurable on failure paths too, which
        is why post-run input state is recorded in a ``finally``.
        """
        with TempWorkspace() as ws:
            ev = _run(ws, "fail_and_mutate", deadline_s=30.0)
            self.assertEqual(errors.PROCESS_FAILED, ev.outcome_code)
            self.assertIn(
                errors.INPUT_HASH_MISMATCH, [f["code"] for f in ev.failures]
            )
            self.assertEqual(
                ev.details["source_sha256_pre"], ev.details["source_sha256_post"]
            )

    def test_unexpected_output_is_detected(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "stray", deadline_s=30.0)
            self.assertEqual(errors.UNEXPECTED_OUTPUT_PRESENT, ev.outcome_code)
            self.assertIn("stray.txt", str(ev.failures))

    def test_input_mutation_is_detected(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "mutate_import", deadline_s=30.0)
            self.assertEqual(errors.INPUT_HASH_MISMATCH, ev.outcome_code)

    def test_output_hash_inconsistency_is_detected(self):
        """Recomputation must be independent; a disagreement is not success."""
        with TempWorkspace() as ws:
            real = snapshot.sha256_file
            calls = {"n": 0}

            def flaky(path):
                calls["n"] += 1
                if str(path).endswith(".pex") and calls["n"] % 2 == 1:
                    return "a" * 64
                return real(path)

            with unittest.mock.patch.object(snapshot, "sha256_file", side_effect=flaky):
                ev = _run(ws, "success", deadline_s=30.0)
            self.assertEqual(errors.OUTPUT_HASH_MISMATCH, ev.outcome_code)

    def test_nonzero_exit_never_succeeds(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "fail", deadline_s=30.0)
            self.assertEqual(errors.PROCESS_FAILED, ev.outcome_code)
            self.assertFalse(ev.success)
            self.assertNotIn("output_sha256", ev.details)


class StreamCapTests(unittest.TestCase):
    def test_bounded_stdout_and_stderr(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "spam", deadline_s=60.0, stream_limit_bytes=1024)
            self.assertEqual(errors.OUTPUT_LIMIT_EXCEEDED, ev.outcome_code)
            self.assertTrue(ev.details["stdout_truncated"])
            self.assertTrue(ev.details["stderr_truncated"])
            self.assertGreaterEqual(ev.details["stdout_bytes_total"], 1024)
            self.assertLessEqual(ev.details["stdout_bytes_retained"], 1024)

    def test_capture_is_bounded_within_limit(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "success", deadline_s=30.0, stream_limit_bytes=4096)
            self.assertFalse(ev.details["stdout_truncated"])
            self.assertFalse(ev.details["stderr_truncated"])


class DeadlineAndCleanupTests(unittest.TestCase):
    def test_hang_produces_timeout_within_budget(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "sleep", deadline_s=3.0)
            self.assertEqual(errors.PROCESS_TIMEOUT, ev.outcome_code)
            self.assertTrue(ev.details["timed_out"])
            self.assertLess(ev.details["elapsed_s"], 3.0 + profile.CLEANUP_GRACE_S + 10.0)

    def test_direct_child_is_terminated(self):
        with TempWorkspace() as ws:
            ev = _run(ws, "sleep", deadline_s=3.0)
            self.assertFalse(ev.details["direct_child_alive_after_cleanup"])

    def test_descendants_are_observed_and_cleaned(self):
        """The stand-in spawns a child; kernel-enforced cleanup must reap it."""
        with TempWorkspace() as ws:
            ev = _run(ws, "spawn_child", deadline_s=4.0)
            self.assertEqual(errors.PROCESS_TIMEOUT, ev.outcome_code)
            self.assertGreaterEqual(ev.details["descendant_count"], 1)
            self.assertEqual("job_object_close", ev.details["cleanup_mechanisms"][-2])
            self.assertEqual([], ev.details["descendants_alive_after_cleanup"])

    def test_stale_ancestry_from_a_recycled_pid_is_not_a_descendant(self):
        """ppid is not unique over time.

        When a pid is recycled, an unrelated process can appear to be the
        child of a process that never created it. Reported as a surviving
        descendant, that fabrication would fail the run for no reason.
        """
        self.assertFalse(proctree.is_plausible_descendant(4242, None))
        with unittest.mock.patch.object(proctree, "creation_time", return_value=100):
            # candidate created before the ancestor: stale link
            self.assertFalse(proctree.is_plausible_descendant(4242, 200))
            # candidate created after the ancestor: plausible
            self.assertTrue(proctree.is_plausible_descendant(4242, 50))
        with unittest.mock.patch.object(proctree, "creation_time", return_value=None):
            # already gone, or unreadable: not a live survivor either way
            self.assertFalse(proctree.is_plausible_descendant(4242, 50))

    def test_unmeasurable_tree_fails_closed(self):
        with TempWorkspace() as ws:
            with unittest.mock.patch.object(proctree, "selfcheck", return_value=False):
                ev = _run(ws, "success", deadline_s=30.0)
            self.assertEqual(errors.INTERNAL_ERROR, ev.outcome_code)
            self.assertFalse(ev.success)

    def test_descendant_survival_is_reported_not_hidden(self):
        """Force the fallback path with a kill that fails: a survivor must FAIL."""
        with TempWorkspace() as ws:
            class NoJob:
                def __init__(self, *a, **k):
                    raise jobobject.JobObjectUnavailable("forced")

            with unittest.mock.patch.object(jobobject, "JobObject", NoJob), \
                 unittest.mock.patch.object(proctree, "kill", return_value=False):
                ev = _run(ws, "spawn_child", deadline_s=4.0)
            self.assertEqual(errors.DESCENDANT_PROCESS_SURVIVED, ev.outcome_code)
            self.assertTrue(ev.details["descendants_alive_after_cleanup"])
            for pid in ev.details["descendants_alive_after_cleanup"]:
                proctree.kill(pid)


class DeterminismTests(unittest.TestCase):
    def _two_runs(self, behaviour: str) -> tuple[str, str]:
        with TempWorkspace() as a, TempWorkspace() as b:
            first = _run(a, behaviour, deadline_s=30.0)
            second = _run(b, behaviour, deadline_s=30.0)
            return first.details.get("output_sha256"), second.details.get("output_sha256")

    def test_identical_input_agrees(self):
        first, second = self._two_runs("success")
        self.assertEqual(first, second)

    def test_divergent_output_is_detected(self):
        """The gate can fail. If it cannot, it is not a gate."""
        first, second = self._two_runs("random_output")
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
