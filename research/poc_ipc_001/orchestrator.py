"""Trusted IPC orchestrator for POC-IPC-001.

Implements the accepted ADR-002 execution lifecycle literally:

- full pre-spawn validation (no worker spawns for invalid requests);
- single MONOTONIC session deadline started immediately after spawn,
  before any I/O;
- bounded, deadline-aware stdin writer + stdout/stderr pumps
  (never communicate(), never unbounded capture);
- fail-closed timeout with platform-honest cleanup
  (POSIX process group; Windows direct child; tree = NO VERIFICADO);
- SUCCESS computed by this trusted side as a conjunction of invariants,
  never inferred from response.status alone.
"""

import ctypes
import os
import select
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import errors
import protocol
import schemas
import synthetic_operation
from workspace import JobWorkspace

IO_POLL_SLICE_S = 0.02      # pump wake-up cadence (no busy loop)
TERMINATE_GRACE_S = 0.5     # SIGTERM grace before SIGKILL (POSIX)
JOIN_GRACE_S = 1.0          # finite join budget after termination


@dataclass
class SessionResult:
    verdict: str                      # "PASS" | "FAIL"
    outcome_code: str                 # taxonomy code behind the verdict
    reason: str
    spawned: bool = False
    spawn_count: int = 0              # observable for pre-spawn tests
    child_pid: int | None = None      # observable for platform-cleanup tests
    exit_code: int | None = None
    duration_ms: int = 0              # derived from the monotonic clock
    timed_out: bool = False
    output_limit_hit: bool = False
    pipe_write_failed: bool = False
    write_completed: bool = False     # full request handed to the OS pipe
    response: dict | None = None
    receipt: dict | None = None
    stdout_bytes: bytes = b""
    stderr_bytes: bytes = b""
    leaked_threads: int = 0           # threads alive after session cleanup
    persisted_receipt: Path | None = None
    notes: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict == "PASS"


class _PumpFlags:
    __slots__ = ("exceeded", "done")

    def __init__(self):
        self.exceeded = False
        self.done = threading.Event()


class CapabilityRegistry:
    """Truthful capability status; unknown operations never route."""

    def __init__(self):
        self._ops = {
            synthetic_operation.OPERATION_NAME: "SUPPORTED",
        }

    def status(self, operation: str) -> str | None:
        return self._ops.get(operation)


def _make_env(workspace) -> dict:
    """Deny-by-default environment; TEMP/TMPDIR redirected into job temp."""
    env: dict = {}
    if os.name == "nt":
        # The C runtime needs SYSTEMROOT; nothing else is inherited.
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        temp = str(workspace.job_temp())
        env["TEMP"] = temp
        env["TMP"] = temp
    else:
        env["TMPDIR"] = str(workspace.job_temp())
    # PATH deliberately absent: executables are addressed absolutely.
    return env


def _pump(fd: int, cap: int, deadline: float, sink: list, flags: _PumpFlags) -> None:
    """Bounded reader: accumulates at most cap+1 bytes, stops at the deadline.

    Never performs an indefinitely-blocking read: Windows polls availability
    via PeekNamedPipe; POSIX polls with select on a non-blocking fd.
    """
    total = 0
    try:
        if os.name == "nt":
            import msvcrt

            handle = msvcrt.get_osfhandle(fd)
            kernel32 = ctypes.windll.kernel32
        else:
            os.set_blocking(fd, False)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            if os.name == "nt":
                avail = ctypes.c_uint32(0)
                ok = kernel32.PeekNamedPipe(
                    handle, None, 0, None, ctypes.byref(avail), None
                )
                if not ok:
                    err = ctypes.GetLastError()
                    if err == 109:  # ERROR_BROKEN_PIPE: writer closed => EOF
                        return
                    time.sleep(IO_POLL_SLICE_S)
                    continue
                if avail.value == 0:
                    time.sleep(IO_POLL_SLICE_S)
                    continue
                want = min(avail.value, protocol.IO_CHUNK_BYTES)
            else:
                timeout = min(remaining, IO_POLL_SLICE_S)
                ready, _, _ = select.select([fd], [], [], timeout)
                if not ready:
                    continue
                want = protocol.IO_CHUNK_BYTES

            chunk = os.read(fd, max(1, want))
            if not chunk:
                return  # EOF
            sink.append(chunk)
            total += len(chunk)
            if total > cap:
                flags.exceeded = True
                return
    except OSError:
        return  # pipe torn down by cleanup
    finally:
        flags.done.set()


def _writer(
    fd: int, payload: bytes, deadline: float, result: SessionResult,
    keepalive_file,
) -> None:
    """Deadline-aware stdin writer.

    POSIX: non-blocking fd + poll(POLLOUT) slices.
    Windows: chunked writes; a blocked write is unbroken by child termination
    (kernel breaks the pipe), which is why termination precedes the join.
    keepalive_file keeps the Popen-owned file object alive; the fd is closed
    exactly once here.
    """
    view = memoryview(payload)
    try:
        if os.name != "nt":
            os.set_blocking(fd, False)
        while view.nbytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return  # deadline owns the outcome classification
            if os.name != "nt":
                timeout = min(remaining, IO_POLL_SLICE_S)
                _, writable, _ = select.select([], [fd], [], timeout)
                if not writable:
                    continue
            sent = os.write(fd, view[:32768])
            view = view[sent:]
        result.write_completed = True
    except BrokenPipeError:
        result.pipe_write_failed = True
    except OSError as exc:
        # Windows: WriteFile to a pipe whose reader died surfaces here too.
        if getattr(exc, "winerror", None) in (232, 109):
            result.pipe_write_failed = True
        # Deadline expiry is owned by the timeout classifier.
    finally:
        # keepalive_file owns the fd. Closing it releases the descriptor
        # exactly once. Closing `fd` here separately would be a double
        # close and could tear down an unrelated descriptor the OS
        # reuses between calls.
        try:
            keepalive_file.close()
        except (OSError, ValueError):
            pass


class IPCOrchestrator:
    def __init__(
        self,
        python_executable: str,
        worker_entry: Path,
        trusted_jobs_root: Path,
        registry: CapabilityRegistry | None = None,
    ):
        self.python_executable = str(Path(python_executable).resolve())
        self.worker_entry = str(Path(worker_entry).resolve())
        self.trusted_jobs_root = Path(trusted_jobs_root).resolve()
        self.registry = registry or CapabilityRegistry()

    # -- public entry ------------------------------------------------------

    # OperationCall: caller-supplied data with NO trusted-side fields.
    # Any attempt to inject a reserved field is a fail-closed pre-spawn
    # INVALID_REQUEST: we never accept caller-supplied request_id,
    # protocol_version, or any host/workspace path. The orchestrator
    # constructs the WireRequest from these fields plus trusted-side values.
    _OPERATION_CALL_REQUIRED = ("job_id", "operation", "parameters")
    _OPERATION_CALL_OPTIONAL = ("timeout_ms",)
    _OPERATION_CALL_RESERVED = frozenset({
        "request_id",
        "protocol_version",
        "trusted_jobs_root",
        "workspace",
        "base_dir",
        "cwd",
        "job_root",
        "worker_receipt",  # never part of a request
    })

    def execute(self, operation_call: dict) -> SessionResult:
        """Run one one-shot IPC session. Fail-closed end to end.

        Public API takes a closed-world OperationCall. The orchestrator
        builds the WireRequest by adding protocol_version and a fresh
        trusted-side request_id. The JobWorkspace is derived from
        ``self.trusted_jobs_root / "jobs" / <job_id>``.

        No host/workspace root, no path component, and no trusted-side wire
        field may be supplied by the caller (D1, D13, D14 of ADR-002).
        """
        result = SessionResult(verdict="FAIL", outcome_code=errors.INTERNAL_ERROR,
                               reason="session did not run")
        started_mono = time.monotonic()

        # (1) Closed-world OperationCall validation: required + optional keys
        # only; reserved fields are an INVALID_REQUEST pre-spawn.
        if not isinstance(operation_call, dict):
            return self._prespawn_fail(
                result, started_mono, errors.INVALID_REQUEST,
                "operation_call must be an object",
            )
        unknown = set(operation_call) - (
            set(self._OPERATION_CALL_REQUIRED) |
            set(self._OPERATION_CALL_OPTIONAL)
        )
        if unknown:
            reserved_hit = unknown & self._OPERATION_CALL_RESERVED
            if reserved_hit:
                return self._prespawn_fail(
                    result, started_mono, errors.INVALID_REQUEST,
                    f"reserved field(s) are not part of OperationCall: "
                    f"{sorted(reserved_hit)}",
                )
            return self._prespawn_fail(
                result, started_mono, errors.INVALID_REQUEST,
                f"unknown OperationCall field(s): {sorted(unknown)}",
            )
        missing = set(self._OPERATION_CALL_REQUIRED) - set(operation_call)
        if missing:
            return self._prespawn_fail(
                result, started_mono, errors.INVALID_REQUEST,
                f"missing OperationCall field(s): {sorted(missing)}",
            )

        # (2) Build the WireRequest. protocol_version and request_id are
        # ALWAYS trusted-side; the caller cannot influence them.
        request = {
            "protocol_version": protocol.PROTOCOL_VERSION,
            "request_id": protocol.new_request_id(),
            "job_id": operation_call["job_id"],
            "operation": operation_call["operation"],
            "parameters": operation_call["parameters"],
        }
        if "timeout_ms" in operation_call:
            request["timeout_ms"] = operation_call["timeout_ms"]

        ok, code, detail = schemas.validate_request(request)
        if not ok:
            return self._prespawn_fail(result, started_mono, code, detail)

        # (5) Serialize and size-check immediately after the generic wire
        # schema: byte limits are enforced cheapest-first, before policy or
        # per-operation parameter validation. (ADR ordering note: this is a
        # stricter-than-required fail-closed placement; nothing passes the
        # size gate that would have failed later anyway.)
        payload = protocol.strict_json_dumps(request)
        if len(payload) > protocol.MAX_REQUEST_BYTES:
            return self._prespawn_fail(result, started_mono,
                                       errors.REQUEST_LIMIT_EXCEEDED,
                                       f"serialized request exceeds MAX_REQUEST_BYTES "
                                       f"({protocol.MAX_REQUEST_BYTES})")

        # (3) Identifier-specific codes are already normative; policy next.
        capability = self.registry.status(request["operation"])
        if capability is None:
            return self._prespawn_fail(
                result, started_mono, errors.INVALID_OPERATION,
                f"operation {request['operation']!r} is not in the allowlist",
            )
        if capability != "SUPPORTED":
            return self._prespawn_fail(
                result, started_mono, errors.POLICY_VIOLATION,
                f"operation {request['operation']!r} is {capability}",
            )

        op_module = synthetic_operation
        ok, detail = op_module.validate_parameters(request["parameters"])
        if not ok:
            return self._prespawn_fail(
                result, started_mono, errors.INVALID_REQUEST, detail
            )

        # (4) Trusted-side workspace derivation. The job directory is
        # resolved strictly from self.trusted_jobs_root + job_id; a caller
        # cannot influence which job_dir the worker sees. The JobWorkspace
        # constructor itself enforces safe-name and post-resolve containment.
        try:
            workspace = JobWorkspace(self.trusted_jobs_root, request["job_id"])
            workspace.ensure_areas()
        except Exception as exc:  # noqa: BLE001 — boundary, fail-closed
            return self._prespawn_fail(
                result, started_mono, errors.WORKSPACE_VIOLATION, repr(exc)[:512]
            )

        # (6)-(8) Spawn without shell; deadline starts immediately after.
        env = _make_env(workspace)
        popen_kwargs = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workspace.job_dir),
            env=env,
            shell=False,
            close_fds=True,
        )
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        argv = [
            self.python_executable,
            "-I",
            "-B",
            self.worker_entry,
            "--job-root",
            str(workspace.job_dir),
        ]
        try:
            proc = subprocess.Popen(argv, **popen_kwargs)
        except OSError as exc:
            result.reason = f"spawn failed: {exc!r}"[:512]
            result.outcome_code = errors.PROCESS_FAILED
            result.duration_ms = int((time.monotonic() - started_mono) * 1000)
            return result

        result.spawned = True
        result.spawn_count = 1
        result.child_pid = proc.pid
        # ADR-002 D13: ONE monotonic deadline, started immediately post-spawn,
        # before any I/O. timeout_ms is milliseconds; monotonic() is seconds.
        deadline = time.monotonic() + self._effective_timeout_ms(request) / 1000.0

        # The writer thread owns the stdin fd from here on. We keep the file
        # object referenced (alive) but detach it from Popen so only the
        # writer's finally-block closes it.
        stdin_file = proc.stdin
        stdin_fd = stdin_file.fileno()
        proc.stdin = None
        out_flags, err_flags = _PumpFlags(), _PumpFlags()
        out_sink: list = []
        err_sink: list = []

        writer = threading.Thread(
            target=_writer,
            args=(stdin_fd, payload, deadline, result, stdin_file),
            name="ipc-stdin-writer", daemon=True,
        )
        pump_out = threading.Thread(
            target=_pump,
            args=(proc.stdout.fileno(), protocol.MAX_STDOUT_BYTES, deadline,
                  out_sink, out_flags),
            name="ipc-stdout-pump", daemon=True,
        )
        pump_err = threading.Thread(
            target=_pump,
            args=(proc.stderr.fileno(), protocol.MAX_STDERR_BYTES, deadline,
                  err_sink, err_flags),
            name="ipc-stderr-pump", daemon=True,
        )
        pump_out.start()
        pump_err.start()
        writer.start()

        # (10) Read/wait strictly under the execution deadline. The wait
        # loop exits for exactly three reasons, each tagged with a single
        # boolean:
        #   - execution deadline expired                 -> timed_out = True
        #   - a stream exceeded its cap (overflow)       -> output_limit_hit
        #   - all I/O threads finished naturally          -> keep waiting for
        #                                                    the child
        # In particular, "the child is still alive but threads finished" is
        # NOT, on its own, a reason to terminate. The child is given the
        # remainder of the execution deadline to exit on its own. This
        # matters on Windows where `proc.poll()` can transiently return None
        # after the worker has flushed stdout but before the kernel marks
        # the process exited; killing it then would convert a clean
        # worker-returned Response into a fake PROCESS_TIMEOUT.
        timed_out = False
        result.output_limit_hit = False
        while True:
            now = time.monotonic()
            if now >= deadline:
                timed_out = True
                break
            if out_flags.exceeded or err_flags.exceeded:
                result.output_limit_hit = True
                break
            if (
                writer.is_alive() is False
                and pump_out.is_alive() is False
                and pump_err.is_alive() is False
            ):
                # I/O drained; wait for the child to exit naturally under
                # the remaining execution deadline.
                break
            time.sleep(min(0.01, max(0.0, deadline - now)))

        # Three orthogonal decision branches, evaluated in priority order.
        if result.output_limit_hit:
            # Stream cap was hit. The child is misbehaving; terminate now.
            # timed_out stays False: the deadline did not expire.
            self._terminate(proc)
        elif timed_out:
            # Execution deadline expired with the child still alive.
            self._terminate(proc)
        else:
            # All I/O threads finished, output cap not hit, and the deadline
            # has not expired. Give the child the remaining budget to exit
            # naturally. We do NOT call _terminate() on `proc.poll() is None`
            # alone — that race would spuriously convert clean worker
            # returns into PROCESS_TIMEOUT.
            remaining = max(0.001, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._terminate(proc)

        # Finite joins; anything left is counted and reported honestly.
        for thread in (writer, pump_out, pump_err):
            thread.join(timeout=JOIN_GRACE_S)
        result.leaked_threads = sum(
            1 for t in (writer, pump_out, pump_err) if t.is_alive()
        )
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=JOIN_GRACE_S)
        except subprocess.TimeoutExpired:
            pass

        # `timed_out` reflects ONLY execution-deadline expiry. Output
        # overflow uses `output_limit_hit` and is a different outcome.
        result.timed_out = timed_out
        result.exit_code = proc.returncode
        result.stdout_bytes = b"".join(out_sink)[: protocol.MAX_STDOUT_BYTES]
        result.stderr_bytes = b"".join(err_sink)[: protocol.MAX_STDERR_BYTES]
        result.duration_ms = int((time.monotonic() - started_mono) * 1000)

        # Persist diagnostics trusted-side (worker cannot write these areas).
        try:
            workspace.persist_stderr_log(request["request_id"], result.stderr_bytes)
        except Exception as exc:  # noqa: BLE001
            result.notes.append(f"stderr persist failed: {exc!r}"[:200])

        # ---- deterministic outcome classification ------------------------
        if result.output_limit_hit:
            return self._fail(result, errors.OUTPUT_LIMIT_EXCEEDED,
                              "a stream exceeded its configured cap")
        if timed_out:
            return self._fail(result, errors.PROCESS_TIMEOUT,
                              "session deadline exceeded")
        if result.pipe_write_failed:
            return self._fail(result, errors.PIPE_WRITE_FAILED,
                              "could not deliver the full request over stdin")
        if (not result.write_completed and result.exit_code is not None
                and result.exit_code == 0):
            # Child exited without consuming the request: the request was
            # never delivered, even if the last chunk fit the pipe buffer.
            return self._fail(result, errors.PIPE_WRITE_FAILED,
                              "child exited before consuming the request")
        if result.leaked_threads:
            return self._fail(
                result, errors.INTERNAL_ERROR,
                f"{result.leaked_threads} I/O thread(s) survived session cleanup",
            )
        if result.exit_code != 0:
            return self._fail(result, errors.PROCESS_FAILED,
                              f"nonzero exit code {result.exit_code}")

        # Response validation (strict JSON + closed-world schema).
        try:
            response = protocol.strict_json_loads(result.stdout_bytes)
        except ValueError as exc:
            return self._fail(result, errors.INVALID_RESPONSE,
                              f"strict JSON: {exc}"[:512])
        ok, why = schemas.validate_response(response)
        if not ok:
            return self._fail(result, errors.INVALID_RESPONSE, why[:512])

        # Persist the validated Response on the result regardless of outcome
        # — it is the only evidence the worker emitted for this session.
        result.response = response

        # Response-level correlation (independent of receipt). On a non-SUCCESS
        # response the receipt is required by the schema to be null; we never
        # index into it. The status value itself is the verdict carrier.
        for key in ("request_id", "job_id", "operation"):
            if response[key] != request[key]:
                return self._fail(
                    result, errors.RECEIPT_MISMATCH,
                    f"response.{key} does not correlate to request",
                )
        if response["status"] != protocol.STATUS_SUCCESS:
            return self._fail(result, response["status"],
                              response.get("error", {}).get("message", "")
                              or "worker returned a non-SUCCESS status")

        # SUCCESS path: receipt must be present, schema-valid, and correlated.
        receipt = response["worker_receipt"]
        for key in ("request_id", "job_id", "operation"):
            if receipt[key] != request[key]:
                return self._fail(
                    result, errors.RECEIPT_MISMATCH,
                    f"receipt.{key} does not correlate to request",
                )

        # Non-vacuous assertions, all passing (contract items 8-9 precede
        # workspace invariants in the deterministic classification order).
        assertions = receipt["worker_assertions"]
        if not assertions:
            return self._fail(result, errors.ASSERTION_FAILED,
                              "required worker assertions are empty")
        failing = [a["name"] for a in assertions if a["passed"] is not True]
        if failing:
            return self._fail(result, errors.ASSERTION_FAILED,
                              f"failing assertions: {failing}")

        # Workspace invariants for the read-only operation. The receipt is
        # the worker's claim; the orchestrator independently re-derives the
        # truth from the filesystem and re-validates the receipt against it.
        # Read-only means: outputs MUST be empty (the worker cannot promote
        # anything), and inputs MUST be exactly the one file the orchestrator
        # provisioned, with its exact SHA-256. Any extra/missing ref is
        # a workspace-truthfulness failure (a worker cannot pad receipts with
        # references to files it never opened).
        if not workspace.candidates_empty():
            return self._fail(result, errors.WORKSPACE_VIOLATION,
                              "read-only operation produced candidates")
        if receipt["outputs"] != []:
            return self._fail(
                result, errors.WORKSPACE_VIOLATION,
                f"read-only operation must declare outputs==[]; "
                f"got {len(receipt['outputs'])} reference(s)",
            )
        expected_ref_path = f"input/{request['parameters']['input_name']}"
        provisioned_sha = workspace.input_sha256(
            request["parameters"]["input_name"]
        )
        inputs = receipt["inputs"]
        if (len(inputs) != 1
                or inputs[0].get("path") != expected_ref_path
                or inputs[0].get("sha256") != provisioned_sha):
            return self._fail(
                result, errors.WORKSPACE_VIOLATION,
                f"receipt.inputs must be exactly "
                f"[{{'path': {expected_ref_path!r}, 'sha256': <provisioned>}}]; "
                f"got len={len(inputs)}",
            )

        # SUCCESS — computed, not declared.
        result.verdict = "PASS"
        result.outcome_code = "SUCCESS"
        result.reason = "all success invariants held"
        result.response = response
        result.receipt = receipt
        try:
            result.persisted_receipt = workspace.persist_receipt(
                request["request_id"], receipt
            )
        except Exception as exc:  # noqa: BLE001
            result.verdict = "FAIL"
            result.outcome_code = errors.INTERNAL_ERROR
            result.reason = f"receipt persistence failed: {exc!r}"[:512]
        return result

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _effective_timeout_ms(request: dict) -> float:
        value = protocol.validate_timeout_ms(request.get("timeout_ms"))
        if value is False or value is None:
            return float(protocol.DEFAULT_TIMEOUT_MS)
        return float(value)

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        """Fail-closed cleanup: POSIX group TERM->KILL; Windows direct child."""
        if proc.poll() is not None:
            return
        if os.name != "nt":
            import signal

            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + TERMINATE_GRACE_S
            while proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.terminate()
        try:
            proc.wait(timeout=TERMINATE_GRACE_S + JOIN_GRACE_S)
        except subprocess.TimeoutExpired:
            pass

    def _prespawn_fail(self, result, started_mono, code, detail) -> SessionResult:
        result.outcome_code = code
        result.reason = detail[:512]
        result.spawn_count = 0
        result.duration_ms = int((time.monotonic() - started_mono) * 1000)
        return result

    @staticmethod
    def _fail(result, code, reason) -> SessionResult:
        result.verdict = "FAIL"
        result.outcome_code = code
        result.reason = reason[:512]
        return result


def default_orchestrator(trusted_jobs_root: Path) -> IPCOrchestrator:
    """Build an orchestrator from trusted configuration only."""
    root = Path(__file__).resolve().parent
    return IPCOrchestrator(
        python_executable=sys.executable,
        worker_entry=root / "worker.py",
        trusted_jobs_root=Path(trusted_jobs_root),
    )


if sys.platform == "win32":  # pragma: no cover - documentation anchor
    # Windows I/O strategy: PeekNamedPipe polling for reads (never blocks past
    # the deadline), chunked writes whose worst case is unblocked by direct
    # child termination. Tree cleanup remains NO VERIFICADO per ADR-002.
    pass
