"""Optional Windows Job Object confinement (ADR-004 E9, option b).

ADR-004 offers an ETEC profile two ways to satisfy its cleanup requirement:

    (a) demonstrate that no descendant survives cleanup, or
    (b) confine the tool in a Windows Job Object created with
        ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``, so cleanup is enforced by the
        kernel rather than inferred from a ``terminate()`` call.

It states (b) is preferred where available, because it replaces a claim of the
form "we killed what we could enumerate" with one of the form "the OS released
everything in the set", which does not depend on enumerating the tree at all.

This module is best-effort by design. If the Job Object cannot be created or
the process cannot be assigned, :class:`JobObjectUnavailable` is raised and the
caller falls back to terminate-and-verify, recording which mechanism was used.
Never silently downgrade a failed confinement into a claim of confinement.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9

_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
_kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
]
_kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount",
        "WriteOperationCount",
        "OtherOperationCount",
        "ReadTransferCount",
        "WriteTransferCount",
        "OtherTransferCount",
    )]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


#: Size of JOBOBJECT_EXTENDED_LIMIT_INFORMATION on 64-bit Windows. If the
#: struct layout ever disagrees with this, SetInformationJobObject would be
#: handed a wrong-sized buffer, so we refuse rather than guess.
EXPECTED_STRUCT_SIZE = 144


class JobObjectUnavailable(RuntimeError):
    """Raised when kernel-enforced confinement cannot be established."""


class JobObject:
    """A Job Object that kills every member when its handle is closed."""

    def __init__(self) -> None:
        handle = _kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise JobObjectUnavailable(
                f"CreateJobObjectW failed (last_error={ctypes.get_last_error()})"
            )
        self._handle = handle
        self._closed = False
        try:
            self._set_kill_on_close()
        except JobObjectUnavailable:
            _kernel32.CloseHandle(self._handle)
            self._closed = True
            raise

    def _set_kill_on_close(self) -> None:
        if ctypes.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION) != EXPECTED_STRUCT_SIZE:
            raise JobObjectUnavailable(
                "unexpected JOBOBJECT_EXTENDED_LIMIT_INFORMATION size: "
                f"{ctypes.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)} != {EXPECTED_STRUCT_SIZE}"
            )
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = _kernel32.SetInformationJobObject(
            self._handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            raise JobObjectUnavailable(
                f"SetInformationJobObject failed (last_error={ctypes.get_last_error()})"
            )

    def assign_process(self, process_handle: int) -> None:
        """Add an already-created process to the job."""
        ok = _kernel32.AssignProcessToJobObject(
            self._handle, wintypes.HANDLE(int(process_handle))
        )
        if not ok:
            raise JobObjectUnavailable(
                f"AssignProcessToJobObject failed (last_error={ctypes.get_last_error()})"
            )

    def close(self) -> None:
        """Close the job handle. With KILL_ON_JOB_CLOSE this terminates members."""
        if self._closed:
            return
        self._closed = True
        _kernel32.CloseHandle(self._handle)

    def __enter__(self) -> "JobObject":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
