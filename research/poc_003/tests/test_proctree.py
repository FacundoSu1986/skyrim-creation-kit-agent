"""ctypes binding correctness for the Win32 process-tree helpers.

These tests exist because a wrong ``restype`` is invisible in review and silent
at runtime: ctypes will happily hand back a signed ``c_int`` where the API
returns a ``DWORD``, and every comparison against the documented sentinel then
reads as success.
"""

import ctypes
import os
import sys
import unittest
import unittest.mock
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from poc_003 import proctree  # noqa: E402

TARGET_PID = 4242
FAILURE_SENTINEL = 0xFFFFFFFF


class _FakeThread32:
    """Minimal stand-in for the kernel32 calls ``resume`` makes."""

    def __init__(self, resume_result):
        self.resume_result = resume_result
        self.handle = ctypes.c_void_p(0x1234).value

    def create_snapshot(self, _flags, _pid):
        return self.handle

    def thread32_first(self, _handle, entry):
        # ``resume`` passes ``ctypes.byref(entry)``, which arrives as a
        # CArgObject; the real struct hangs off ``_obj``.
        target = entry._obj if hasattr(entry, "_obj") else entry
        target.th32OwnerProcessID = TARGET_PID
        target.th32ThreadID = 99
        return True

    def thread32_next(self, _handle, _entry):
        return False

    def open_thread(self, _access, _inherit, _tid):
        return self.handle

    def close_handle(self, _handle):
        return True


@unittest.skipUnless(os.name == "nt", "Win32 bindings")
class ResumeThreadReturnTypeTests(unittest.TestCase):
    def test_resume_failure_sentinel_is_detected(self):
        """``(DWORD)-1`` must read as failure, not as success.

        With no explicit ``restype`` ctypes converts the DWORD to a signed int,
        so the sentinel arrives as ``-1`` and ``-1 != 0xFFFFFFFF`` is true: a
        failed resume would be reported as accepted, leaving the child
        suspended until it hit the deadline as PROCESS_TIMEOUT instead of
        failing closed with INTERNAL_ERROR.
        """
        fake = _FakeThread32(FAILURE_SENTINEL)
        with unittest.mock.patch.object(proctree._kernel32, "CreateToolhelp32Snapshot",
                                        fake.create_snapshot), \
             unittest.mock.patch.object(proctree._kernel32, "Thread32First",
                                        fake.thread32_first), \
             unittest.mock.patch.object(proctree._kernel32, "Thread32Next",
                                        fake.thread32_next), \
             unittest.mock.patch.object(proctree._kernel32, "OpenThread",
                                        fake.open_thread), \
             unittest.mock.patch.object(proctree._kernel32, "ResumeThread",
                                        lambda _h: FAILURE_SENTINEL), \
             unittest.mock.patch.object(proctree._kernel32, "CloseHandle",
                                        fake.close_handle):
            self.assertFalse(proctree.resume(TARGET_PID))

    def test_resume_binding_uses_the_dword_return_type(self):
        self.assertIs(wintypes.DWORD, proctree._kernel32.ResumeThread.restype)

    def test_invalid_handle_value_is_pointer_width(self):
        """A handle is pointer-sized; ``-1`` is only correct on 32-bit."""
        self.assertEqual(ctypes.c_void_p(-1).value, proctree.INVALID_HANDLE_VALUE)
        self.assertEqual(ctypes.sizeof(ctypes.c_void_p) * 8,
                         proctree.INVALID_HANDLE_VALUE.bit_length()
                         if proctree.INVALID_HANDLE_VALUE > 0 else 32)


if __name__ == "__main__":
    unittest.main()
