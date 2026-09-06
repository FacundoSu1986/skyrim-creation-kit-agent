"""Windows process-tree observation for POC-003.

Measurement only. It exists to answer one empirical question:

    Does ``PapyrusCompiler.exe`` spawn descendants, and do any of them
    outlive cleanup?

Enumeration goes through the Toolhelp32 snapshot API directly. No shell, no
``wmic``, no PowerShell, no external process is started to perform the
observation.

ADR-004 refuses to infer ``PapyrusCompiler is a direct child => it has no
descendants``. That inference is exactly what this module is here to replace
with a measurement.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = -1
STILL_ACTIVE = 259
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
PROCESS_SET_QUOTA = 0x0100

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class _FILETIME(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


_kernel32.GetProcessTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(_FILETIME),
    ctypes.POINTER(_FILETIME),
    ctypes.POINTER(_FILETIME),
    ctypes.POINTER(_FILETIME),
]


class ProctreeUnavailable(RuntimeError):
    """Raised when the process tree cannot be enumerated.

    Callers must fail closed with ``INTERNAL_ERROR`` rather than treating an
    unmeasurable tree as an empty tree.
    """


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    name: str


def snapshot() -> tuple[Proc, ...]:
    """Return every process visible to Toolhelp32.

    Raises:
        ProctreeUnavailable: the snapshot could not be taken or is empty.
    """
    handle = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if handle in (INVALID_HANDLE_VALUE, 0, None):  # type: ignore[comparison-overlap]
        raise ProctreeUnavailable(
            f"CreateToolhelp32Snapshot failed (last_error={ctypes.get_last_error()})"
        )
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        entries: list[Proc] = []
        ok = _kernel32.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            entries.append(
                Proc(
                    pid=int(entry.th32ProcessID),
                    ppid=int(entry.th32ParentProcessID),
                    name=str(entry.szExeFile),
                )
            )
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = _kernel32.Process32NextW(handle, ctypes.byref(entry))
        if not entries:
            raise ProctreeUnavailable("process snapshot was empty")
        return tuple(entries)
    finally:
        _kernel32.CloseHandle(handle)


def selfcheck() -> bool:
    """True when enumeration is demonstrably working in this process.

    A snapshot that does not even contain our own pid is not a measurement.
    """
    try:
        procs = snapshot()
    except ProctreeUnavailable:
        return False
    return any(p.pid == os.getpid() for p in procs)


def is_alive(pid: int) -> bool:
    """True when ``pid`` names a process that has not exited.

    Uses ``GetExitCodeProcess`` rather than mere presence in a snapshot, so a
    zombie entry or a recycled pid cannot read as "alive".
    """
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        _kernel32.CloseHandle(handle)


def descendants_of(root_pid: int, procs: tuple[Proc, ...]) -> frozenset[int]:
    """Every pid whose ancestry chain reaches ``root_pid`` (exclusive)."""
    children: dict[int, list[int]] = {}
    for proc in procs:
        children.setdefault(proc.ppid, []).append(proc.pid)

    found: set[int] = set()
    stack = list(children.get(root_pid, ()))
    while stack:
        pid = stack.pop()
        if pid in found or pid == root_pid:
            continue
        found.add(pid)
        stack.extend(children.get(pid, ()))
    return frozenset(found)


def names_of(pids: frozenset[int] | set[int], procs: tuple[Proc, ...]) -> dict[int, str]:
    by_pid = {p.pid: p.name for p in procs}
    return {pid: by_pid.get(pid, "<unknown>") for pid in sorted(pids)}


def creation_time(pid: int) -> int | None:
    """Creation time of ``pid`` as a FILETIME integer, or None if unavailable.

    Ancestry read from a Toolhelp32 snapshot is ppid-based, and ppid is not
    unique over time: when a pid is recycled, an unrelated process can appear
    to be the child of a process that did not create it. Creation time
    corroborates the link — a real descendant cannot have been created before
    its ancestor.
    """
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        created = _FILETIME()
        exit_time = _FILETIME()
        kernel_time = _FILETIME()
        user_time = _FILETIME()
        if not _kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            return None
        return (created.high << 32) | created.low
    finally:
        _kernel32.CloseHandle(handle)


def is_plausible_descendant(pid: int, ancestor_created: int | None) -> bool:
    """True unless ``pid`` is provably not a descendant of the ancestor.

    Returns False only on positive evidence of a stale link (the candidate was
    created before the ancestor). A candidate that has already exited, or whose
    creation time cannot be read, is simply not a live survivor, so it is not
    recorded either.
    """
    if ancestor_created is None:
        return False
    created = creation_time(pid)
    if created is None:
        return False
    return created >= ancestor_created


def kill(pid: int) -> bool:
    """Terminate ``pid``. Returns True when TerminateProcess was accepted."""
    handle = _kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(_kernel32.TerminateProcess(handle, 1))
    finally:
        _kernel32.CloseHandle(handle)
