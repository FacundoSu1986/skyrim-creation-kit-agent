"""Platform cleanup tests: real timeouts, real kills, honest claims.

Classification rules (ADR-002 honesty contract):
- VERIFIED: demonstrated by a passing test on this platform.
- NO_VERIFICADO: not demonstrable here; reported, never converted to PASS.
"""

import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _harness as h  # noqa: E402
import errors  # noqa: E402

IS_POSIX = os.name != "nt"
DEADLINE_MS = 1200


class HangTimeoutTests(unittest.TestCase):
    def test_hanging_child_is_terminated_within_budget(self):
        ws, params = h.make_workspace()
        orch = h.make_orchestrator(ws)
        orch.worker_entry = h.helper("hang.py")
        started = time.monotonic()
        result = orch.execute(
            {"job_id": ws.job_dir.name,
             "operation": "INSPECT_SYNTHETIC_INPUT",
             "parameters": dict(params),
             "timeout_ms": DEADLINE_MS},
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.outcome_code, errors.PROCESS_TIMEOUT)
        self.assertTrue(result.timed_out)
        # Returned promptly after the deadline instead of hanging forever.
        self.assertLess(elapsed, DEADLINE_MS / 1000 + 6.0)
        self.assertGreaterEqual(result.duration_ms, DEADLINE_MS - 50)

    def test_no_threads_survive_session_cleanup(self):
        ws, params = h.make_workspace()
        orch = h.make_orchestrator(ws)
        orch.worker_entry = h.helper("hang.py")
        result = orch.execute(
            {"job_id": ws.job_dir.name,
             "operation": "INSPECT_SYNTHETIC_INPUT",
             "parameters": dict(params),
             "timeout_ms": DEADLINE_MS},
        )
        self.assertEqual(result.leaked_threads, 0,
                         "deadline-polled pumps/writer must always exit")


class DirectChildTerminationTests(unittest.TestCase):
    def test_direct_child_is_really_dead_after_timeout(self):
        ws, params = h.make_workspace()
        orch = h.make_orchestrator(ws)
        orch.worker_entry = h.helper("hang.py")
        result = orch.execute(
            {"job_id": ws.job_dir.name,
             "operation": "INSPECT_SYNTHETIC_INPUT",
             "parameters": dict(params),
             "timeout_ms": DEADLINE_MS},
        )
        self.assertEqual(result.outcome_code, errors.PROCESS_TIMEOUT)
        self.assertIsNotNone(result.child_pid)
        # The kernel has reaped the child: the OS-level handle proves it.
        if IS_POSIX:
            with self.assertRaises(ProcessLookupError):
                os.kill(result.child_pid, 0)
        else:
            self._assert_windows_child_reaped(result.child_pid)

    def _assert_windows_child_reaped(self, pid):
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        # `OpenProcess` errors that are consistent with a reaped (no longer
        # active) PID we cannot otherwise query. ERROR_ACCESS_DENIED is
        # intentionally NOT in this set: per Microsoft Learn, a live
        # protected process (e.g. System / CSRSS) can also surface
        # ERROR_ACCESS_DENIED on `OpenProcess`, so accepting that error
        # would let a still-alive process pass the assertion.
        ERROR_INVALID_PARAMETER = 87
        ERROR_NOT_FOUND = 1168

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid),
        )
        if not handle:
            err = ctypes.get_last_error()
            self.assertIn(
                err,
                {ERROR_INVALID_PARAMETER, ERROR_NOT_FOUND},
                f"OpenProcess on pid {pid} failed with unexpected error {err}; "
                f"the process may still be alive (and possibly protected)",
            )
            return
        try:
            code = wintypes.DWORD(0)
            self.assertTrue(
                kernel32.GetExitCodeProcess(handle, ctypes.byref(code)),
                "GetExitCodeProcess must succeed on the reaped child",
            )
            self.assertNotEqual(
                int(code.value), STILL_ACTIVE,
                f"GetExitCodeProcess reported STILL_ACTIVE for pid {pid}; "
                f"the child was not terminated",
            )
        finally:
            kernel32.CloseHandle(handle)


@unittest.skipUnless(IS_POSIX, "process-group cleanup is POSIX-specific")
class PosixProcessGroupTests(unittest.TestCase):
    def test_process_group_is_destroyed_after_timeout(self):
        ws, params = h.make_workspace()
        orch = h.make_orchestrator(ws)
        orch.worker_entry = h.helper("hang.py")
        result = orch.execute(
            {"job_id": ws.job_dir.name,
             "operation": "INSPECT_SYNTHETIC_INPUT",
             "parameters": dict(params),
             "timeout_ms": DEADLINE_MS},
        )
        self.assertEqual(result.outcome_code, errors.PROCESS_TIMEOUT)
        # The whole group is gone: signalling it must fail.
        with self.assertRaises(ProcessLookupError):
            os.killpg(os.getpgid(result.child_pid), 0)


class DescendantHoldingPipeTests(unittest.TestCase):
    """An orphan descendant inheriting pipe handles cannot stall the session."""

    def test_session_returns_on_time_despite_descendant(self):
        ws, params = h.make_workspace()
        orch = h.make_orchestrator(ws)
        orch.worker_entry = h.helper("spawn_descendant.py")
        started = time.monotonic()
        result = orch.execute(
            {"job_id": ws.job_dir.name,
             "operation": "INSPECT_SYNTHETIC_INPUT",
             "parameters": dict(params),
             "timeout_ms": DEADLINE_MS},
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.outcome_code, errors.PROCESS_TIMEOUT)
        self.assertLess(elapsed, DEADLINE_MS / 1000 + 6.0,
                        "descendant holding pipes must not stall the exchange")

    @unittest.skipIf(IS_POSIX, "tree claim is only open on Windows")
    def test_windows_tree_cleanup_claim_stays_unverified(self):
        """Honesty anchor: direct-child termination is what we demonstrate.

        WINDOWS_DIRECT_CHILD_TERMINATION: PASS is asserted by
        test_direct_child_is_really_dead_after_timeout on Windows runners.
        WINDOWS_TREE_CLEANUP remains NO_VERIFICADO — Job Objects / taskkill /T
        are future work and are never claimed by this POC.
        """
        self.assertTrue(True)  # documented NO_VERIFICADO; nothing to assert


if __name__ == "__main__":
    unittest.main()
