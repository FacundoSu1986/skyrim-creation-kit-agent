"""Trusted orchestrator for one ``PAPYRUS_COMPILE_DRYRUN_V1`` execution.

The tool decides nothing about success. It emits untrusted bytes on
stdout/stderr and untrusted files in the workspace; every verdict below is
computed by this module from independently recheckable invariants, in the order
given by ADR-004 "Evidence model".

Topology is a direct spawn::

    trusted orchestrator -- DIRECT SPAWN --> PapyrusCompiler.exe

There is deliberately no Python wrapper process between them, so the tool is a
direct child rather than a grandchild.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

from . import errors, jobobject, profile, proctree, snapshot, workspace

SHELL_NAMES = frozenset({"cmd.exe", "powershell.exe", "pwsh.exe", "wsl.exe", "bash.exe"})


@dataclass
class RunRequest:
    """A closed-world request. Every field is validated before use."""

    profile_id: str = profile.PROFILE_ID
    operation: str = profile.OP_COMPILE_FIXTURE
    source_token: str = "Poc003Minimal"
    deadline_s: float = profile.DEFAULT_DEADLINE_S
    stream_limit_bytes: int = profile.STREAM_LIMIT_BYTES
    expected_output_name: str | None = None

    def expected_output(self) -> str:
        return self.expected_output_name or f"{self.source_token}.pex"


@dataclass
class RunEvidence:
    profile_id: str = profile.PROFILE_ID
    operation: str = ""
    source_token: str = ""
    outcome_code: str | None = None
    success: bool = False
    failures: list[dict[str, str]] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "operation": self.operation,
            "source_token": self.source_token,
            "outcome_code": self.outcome_code,
            "success": self.success,
            "failures": self.failures,
            "details": self.details,
        }


def sanitize(text: str, exe: str, flags: str, ws_root: str) -> str:
    """Redact host-specific paths while keeping technical content intact."""
    out = text.replace(ws_root, "<WORKSPACE_ROOT>")
    # Full executable path first: replacing only its directory would leave the
    # binary name behind, which is exactly what must not leak into evidence.
    out = out.replace(exe, "<PAPYRUS_COMPILER_EXE>")
    out = out.replace(os.path.dirname(exe), "<PAPYRUS_COMPILER_DIR>")
    out = out.replace(flags, "<FLAGS_FILE>")
    return out


def _reader(stream, cap: int, sink: dict[str, object]) -> None:
    """Bounded, deadline-aware reader. Retains at most ``cap`` bytes.

    Draining continues past the cap (discarding) so a chatty tool can never
    block on a full pipe and turn a capture problem into a hang.
    """
    buf = bytearray()
    total = 0
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            total += len(chunk)
            room = cap - len(buf)
            if room > 0:
                buf.extend(chunk[:room])
    except (ValueError, OSError):
        pass
    finally:
        try:
            stream.close()
        except (ValueError, OSError):
            pass
        sink["data"] = bytes(buf)
        sink["total_bytes"] = total
        sink["truncated"] = total > cap


def run_once(config: profile.LocalConfig, ws: workspace.Workspace, request: RunRequest) -> RunEvidence:
    """Execute one compilation and compute the verdict trusted-side."""
    ev = RunEvidence(operation=request.operation, source_token=request.source_token)
    d = ev.details

    proc: subprocess.Popen[bytes] | None = None
    job: jobobject.JobObject | None = None
    observed_descendants: dict[int, str] = {}
    stdout_sink: dict[str, object] = {}
    stderr_sink: dict[str, object] = {}
    threads: list[threading.Thread] = []
    job_error: str | None = None
    baseline_entries: tuple[snapshot.FileEntry, ...] | None = None

    try:
        # --- pre-spawn gate 1: closed profile -------------------------------
        try:
            profile.validate_profile_id(request.profile_id)
        except profile.ProfileViolation as exc:
            raise errors.EtecFailure(errors.POLICY_VIOLATION, str(exc)) from exc
        if request.operation not in profile.ALLOWED_OPERATIONS:
            raise errors.EtecFailure(errors.POLICY_VIOLATION, f"unknown operation {request.operation!r}")
        token = profile.validate_token(request.source_token)

        source_path = os.path.join(ws.input, f"{token}.psc")
        if not os.path.isfile(source_path):
            raise errors.EtecFailure(errors.POLICY_VIOLATION, f"source script absent: {token}.psc")

        # --- pre-spawn gate 2: executable integrity -------------------------
        exe_digest = snapshot.sha256_file(config.executable)
        d["executable_sha256"] = exe_digest
        d["executable_pinned_sha256"] = config.executable_sha256
        if exe_digest != config.executable_sha256:
            raise errors.EtecFailure(errors.EXECUTABLE_HASH_MISMATCH, "pinned hash mismatch before spawn")

        # --- pre-spawn gate 3: flags integrity ------------------------------
        # The evidence record carries an explicit pre/post pair. A single
        # ambiguous "flags_sha256" field is deliberately not used: criterion 11
        # requires presence AND concordance of both values per run.
        flags_digest = snapshot.sha256_file(config.flags)
        d["flags_sha256_pre"] = flags_digest
        if flags_digest != config.flags_sha256:
            raise errors.EtecFailure(errors.INPUT_HASH_MISMATCH, "allowlisted flags file hash mismatch")

        # --- pre-spawn gate 4: expected output must not exist ---------------
        expected_path = os.path.join(ws.candidates, request.expected_output())
        d["expected_output_rel"] = os.path.relpath(expected_path, ws.root).replace(os.sep, "/")
        if os.path.exists(expected_path):
            raise errors.EtecFailure(errors.PRE_EXISTING_OUTPUT_PRESENT, d["expected_output_rel"])

        # --- pre-spawn: record declared read-only inputs --------------------
        source_digest = snapshot.sha256_file(source_path)
        d["source_sha256_pre"] = source_digest
        # Kept so the post-run re-verification can run even when the verdict
        # path exited early. It is an absolute path inside the throwaway
        # workspace and is never emitted into the sanitized evidence record.
        d["source_path"] = source_path
        try:
            import_pre = snapshot.snapshot_tree(ws.imports)
        except snapshot.SnapshotUninspectable as exc:
            raise errors.EtecFailure(errors.INTERNAL_ERROR, f"import root uninspectable: {exc}") from exc
        d["import_snapshot_pre"] = [e.rel for e in import_pre]
        d["import_snapshot_signature_pre"] = snapshot.signature(import_pre)
        d["import_snapshot_size_pre"] = len(import_pre)

        baseline = snapshot.snapshot_tree(ws.root)
        baseline_entries = baseline
        d["workspace_baseline_signature"] = snapshot.signature(baseline)

        argv = profile.build_argv(config, source_path, ws.input, ws.imports, ws.candidates)
        env = profile.build_environment(ws.temp)
        d["argv_sanitized"] = [sanitize(a, config.executable, config.flags, ws.root) for a in argv]
        d["argv_element_count"] = len(argv)
        d["shell"] = False
        d["cwd_sanitized"] = "<WORKSPACE_ROOT>"
        d["env_keys"] = sorted(env)
        d["deadline_s"] = request.deadline_s
        d["stream_limit_bytes"] = request.stream_limit_bytes

        if not proctree.selfcheck():
            raise errors.EtecFailure(errors.INTERNAL_ERROR, "process-tree observation self-check failed")

        # --- spawn (direct child, no shell) ---------------------------------
        # On Windows the process is created SUSPENDED so it cannot execute a
        # single instruction (or spawn a descendant) between CreateProcess and
        # AssignProcessToJobObject. If the Job Object cannot be established the
        # process still runs — the fallback path is explicitly recorded — and
        # the primary thread is resumed either way.
        creation_flags = getattr(subprocess, "CREATE_SUSPENDED", 0)
        started = time.monotonic()
        proc = subprocess.Popen(
            argv,
            cwd=ws.root,
            env=env,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            creationflags=creation_flags,
        )
        d["pid"] = proc.pid
        d["direct_child"] = True
        d["spawn_suspended"] = bool(os.name == "nt" and creation_flags)

        try:
            job = jobobject.JobObject()
            job.assign_process(proc._handle)  # type: ignore[attr-defined]
            d["job_object"] = "assigned"
        except jobobject.JobObjectUnavailable as exc:
            job_error = str(exc)
            if job is not None:
                job.close()
                job = None
            d["job_object"] = f"unavailable: {job_error}"

        if d["spawn_suspended"]:
            if not proctree.resume(proc.pid):
                try:
                    proc.kill()
                except OSError:
                    pass
                raise errors.EtecFailure(
                    errors.INTERNAL_ERROR,
                    "primary thread resume failed after suspended spawn",
                )

        threads = [
            threading.Thread(target=_reader, args=(proc.stdout, request.stream_limit_bytes, stdout_sink), daemon=True),
            threading.Thread(target=_reader, args=(proc.stderr, request.stream_limit_bytes, stderr_sink), daemon=True),
        ]
        for t in threads:
            t.start()

        # --- deadline + process-tree sampling -------------------------------
        # Ancestry alone is ppid-based and a recycled pid can fabricate a
        # child, so the tool's own creation time anchors every observation.
        tool_created = proctree.creation_time(proc.pid)
        d["tool_creation_time_available"] = tool_created is not None
        if tool_created is None:
            observation_reliable = False

        deadline = started + request.deadline_s
        samples = 0
        observation_reliable = tool_created is not None
        timed_out = False
        while True:
            if proc.poll() is not None:
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            samples += 1
            try:
                procs = proctree.snapshot()
                for pid in proctree.descendants_of(proc.pid, procs):
                    if pid in observed_descendants:
                        continue
                    if not proctree.is_plausible_descendant(pid, tool_created):
                        continue
                    observed_descendants[pid] = proctree.names_of({pid}, procs).get(pid, "<unknown>")
            except proctree.ProctreeUnavailable:
                observation_reliable = False
            time.sleep(profile.TREE_POLL_INTERVAL_S)

        d["tree_samples"] = samples
        d["tree_observation_reliable"] = observation_reliable
        d["descendants_observed"] = {
            str(pid): name for pid, name in sorted(observed_descendants.items())
        }
        d["descendant_count"] = len(observed_descendants)
        d["shell_processes_in_launch_tree"] = sorted(
            {name for name in observed_descendants.values() if name.lower() in SHELL_NAMES}
        )

        # --- cleanup ---------------------------------------------------------
        mechanisms: list[str] = []
        if timed_out:
            mechanisms.append("deadline_expired")
        if job is not None:
            job.close()
            job = None
            mechanisms.append("job_object_close")
        else:
            for pid in sorted(observed_descendants):
                if proctree.kill(pid):
                    mechanisms.append(f"terminate_descendant:{pid}")
        # ``direct_child_terminate`` must name a termination the kernel was
        # actually asked to perform. On Windows ``Popen.kill()`` returns
        # immediately for an already-exited process without issuing a
        # TerminateProcess, so recording it unconditionally would claim a
        # cleanup action that never happened. The honest record for that case
        # is that the child had already exited on its own.
        try:
            if proc.poll() is None:
                proc.kill()
                mechanisms.append("direct_child_terminate")
            else:
                mechanisms.append("direct_child_exited")
        except OSError:
            pass

        try:
            proc.wait(timeout=profile.CLEANUP_GRACE_S)
        except subprocess.TimeoutExpired:
            mechanisms.append("grace_expired")
        for t in threads:
            t.join(timeout=profile.IO_JOIN_GRACE_S)
        leaked = [t.name for t in threads if t.is_alive()]
        if leaked:
            mechanisms.append("io_threads_leaked")
        d["cleanup_mechanisms"] = mechanisms
        d["io_threads_leaked"] = bool(leaked)

        exit_code = proc.returncode
        elapsed = time.monotonic() - started
        d["exit_code"] = exit_code
        d["elapsed_s"] = round(elapsed, 3)
        d["timed_out"] = timed_out

        # --- post-cleanup descendant verification ----------------------------
        alive_descendants: list[int] = []
        if observation_reliable:
            alive_descendants = [pid for pid in sorted(observed_descendants) if proctree.is_alive(pid)]
        d["descendants_alive_after_cleanup"] = alive_descendants
        child_alive = proctree.is_alive(proc.pid) if observation_reliable else None
        d["direct_child_alive_after_cleanup"] = child_alive

        # --- streams ---------------------------------------------------------
        stdout_data = bytes(stdout_sink.get("data", b""))
        stderr_data = bytes(stderr_sink.get("data", b""))
        d["stdout_bytes_retained"] = len(stdout_data)
        d["stdout_bytes_total"] = int(stdout_sink.get("total_bytes", 0))
        d["stdout_truncated"] = bool(stdout_sink.get("truncated", False))
        d["stderr_bytes_retained"] = len(stderr_data)
        d["stderr_bytes_total"] = int(stderr_sink.get("total_bytes", 0))
        d["stderr_truncated"] = bool(stderr_sink.get("truncated", False))

        logs_dir = ws.logs
        with open(os.path.join(logs_dir, "stdout.log"), "wb") as fh:
            fh.write(stdout_data)
        with open(os.path.join(logs_dir, "stderr.log"), "wb") as fh:
            fh.write(stderr_data)

        # --- verdict computation --------------------------------------------
        # Order matters: report the most specific cause first. A descendant
        # that survives while holding the inherited pipes also starves the
        # reader threads, so checking the leak first would name the symptom and
        # bury the cause. The leak is still recorded in the evidence either way.
        if not observation_reliable:
            raise errors.EtecFailure(errors.INTERNAL_ERROR, "process-tree observation unreliable")
        if alive_descendants:
            raise errors.EtecFailure(
                errors.DESCENDANT_PROCESS_SURVIVED,
                f"alive after cleanup: {alive_descendants}",
            )
        if child_alive:
            raise errors.EtecFailure(errors.PROCESS_TIMEOUT, "direct child alive after cleanup")
        if leaked:
            raise errors.EtecFailure(errors.INTERNAL_ERROR, "I/O reader threads leaked past cleanup grace")
        if d["stdout_truncated"] or d["stderr_truncated"]:
            raise errors.EtecFailure(errors.OUTPUT_LIMIT_EXCEEDED, "stream cap exceeded")
        if timed_out:
            raise errors.EtecFailure(errors.PROCESS_TIMEOUT, f"deadline {request.deadline_s}s exceeded")
        if exit_code != 0:
            raise errors.EtecFailure(errors.PROCESS_FAILED, f"exit_code={exit_code}")

        # exit code zero is necessary but NOT sufficient: the compiler returns
        # 0 even for a usage error, so the artifact gates decide.
        if not os.path.isfile(expected_path):
            raise errors.EtecFailure(errors.EXPECTED_OUTPUT_MISSING, "expected artifact absent after exit 0")
        size = os.path.getsize(expected_path)
        d["output_size"] = size
        if size == 0:
            raise errors.EtecFailure(errors.EXPECTED_OUTPUT_MISSING, "expected artifact is 0 bytes")
        if not os.path.isfile(expected_path) or not workspace.is_strictly_inside(expected_path, ws.candidates):
            raise errors.EtecFailure(errors.WORKSPACE_VIOLATION, "artifact escaped candidates/")

        first = snapshot.sha256_file(expected_path)
        second = snapshot.sha256_file(expected_path)
        if first != second:
            raise errors.EtecFailure(errors.OUTPUT_HASH_MISMATCH, "independent recomputation disagrees")
        d["output_sha256"] = first
        d["output_sha256_recomputed"] = second

        # --- input immutability ---------------------------------------------
        source_post = snapshot.sha256_file(source_path)
        d["source_sha256_post"] = source_post
        if source_post != source_digest:
            raise errors.EtecFailure(errors.INPUT_HASH_MISMATCH, "source script mutated")
        try:
            import_post = snapshot.snapshot_tree(ws.imports)
        except snapshot.SnapshotUninspectable as exc:
            raise errors.EtecFailure(errors.INTERNAL_ERROR, f"import root uninspectable post-run: {exc}") from exc
        d["import_snapshot_signature_post"] = snapshot.signature(import_post)
        changes = snapshot.diff(import_pre, import_post)
        d["import_snapshot_changes"] = changes
        if any(changes.values()):
            raise errors.EtecFailure(errors.INPUT_HASH_MISMATCH, f"import root changed: {changes}")
        try:
            d["flags_sha256_post"] = snapshot.sha256_file(config.flags)
        except OSError as exc:
            raise errors.EtecFailure(errors.INTERNAL_ERROR, f"flags post-state uninspectable: {exc}") from exc
        if d["flags_sha256_post"] != flags_digest:
            raise errors.EtecFailure(errors.INPUT_HASH_MISMATCH, "flags file mutated during run")

        # --- unexpected outputs (criterion 12) ------------------------------
        workspace_failures = _record_post_workspace_state(ws, baseline_entries, d)
        if workspace_failures:
            raise errors.EtecFailure(
                workspace_failures[0]["code"], workspace_failures[0]["detail"]
            )

        ev.success = True

    except errors.EtecFailure as exc:
        ev.outcome_code = exc.code
        ev.failures.append(exc.as_dict())
    except snapshot.SnapshotUninspectable as exc:
        ev.outcome_code = errors.INTERNAL_ERROR
        ev.failures.append({"code": errors.INTERNAL_ERROR, "detail": str(exc)})
    finally:
        # Input and workspace immutability are verified on every path that
        # reached the pre-spawn baseline, not only on the happy one: a tool
        # that fails can still have mutated a declared read-only input
        # (criterion 11) or produced an undeclared output (criterion 12), and
        # both must be measurable for those runs too. A post-state failure is
        # appended to the evidence without overwriting the primary outcome, so
        # PROCESS_TIMEOUT + INTERNAL_ERROR (or + INPUT_HASH_MISMATCH) can
        # coexist in ``failures``.
        if "source_sha256_pre" in d:
            for failure in _record_post_input_state(config, ws, d):
                ev.failures.append(failure)
                if ev.outcome_code is None:
                    ev.outcome_code = failure["code"]
                    ev.success = False
        if "workspace_baseline_signature" in d and "workspace_post_inspected" not in d:
            for failure in _record_post_workspace_state(ws, baseline_entries, d):
                ev.failures.append(failure)
                if ev.outcome_code is None:
                    ev.outcome_code = failure["code"]
                    ev.success = False
        # Internal bookkeeping only: an absolute path must not reach the
        # committed evidence record.
        d.pop("source_path", None)
        if job is not None:
            job.close()

    _settle_input_verdict(ev)
    return ev


def _record_post_input_state(
    config: profile.LocalConfig, ws: workspace.Workspace, d: dict[str, object]
) -> list[dict[str, str]]:
    """Record post-run input hashes on every path that reached pre-state.

    Criterion 11 names three declared read-only inputs (source script, flags
    file, import root); each is re-measured independently here. Returns a list
    of failure entries (``INTERNAL_ERROR``) for any input that cannot be
    re-measured, so criterion 11 fails closed instead of reading "unchanged".
    A *demonstrated* difference is not reported here; ``_settle_input_verdict``
    maps that to ``INPUT_HASH_MISMATCH``.
    """
    failures: list[dict[str, str]] = []
    try:
        d["source_sha256_post"] = snapshot.sha256_file(str(d.get("source_path")))
    except (OSError, TypeError) as exc:
        d["input_post_state"] = f"source uninspectable: {exc}"
        failures.append(
            {
                "code": errors.INTERNAL_ERROR,
                "detail": f"source post-state uninspectable: {exc}",
            }
        )
    try:
        d["flags_sha256_post"] = snapshot.sha256_file(config.flags)
    except OSError as exc:
        d["input_post_state"] = f"flags uninspectable: {exc}"
        failures.append(
            {
                "code": errors.INTERNAL_ERROR,
                "detail": f"flags post-state uninspectable: {exc}",
            }
        )
    try:
        d["import_snapshot_signature_post"] = snapshot.signature(
            snapshot.snapshot_tree(ws.imports)
        )
    except (OSError, snapshot.SnapshotUninspectable) as exc:
        d["input_post_state"] = f"import root uninspectable: {exc}"
        failures.append(
            {
                "code": errors.INTERNAL_ERROR,
                "detail": f"import root post-state uninspectable: {exc}",
            }
        )
    return failures


def _record_post_workspace_state(
    ws: workspace.Workspace,
    baseline: tuple[snapshot.FileEntry, ...] | None,
    d: dict[str, object],
) -> list[dict[str, str]]:
    """Snapshot the workspace post-run and classify undeclared additions.

    Runs on every path that recorded a pre-spawn baseline, so criterion 12 is
    measurable for failed and timed-out runs too. The only accepted additions
    are the declared expected output and the declared scratch areas (``logs/``,
    ``temp/``). Every other new file is an ``UNEXPECTED_OUTPUT_PRESENT``
    finding; a path outside the workspace cannot appear in the whole-workspace
    snapshot and remains the containment gate's ``WORKSPACE_VIOLATION``, so the
    two classes are never merged.
    """
    failures: list[dict[str, str]] = []
    if baseline is None:
        d["workspace_post_inspected"] = False
        failures.append(
            {
                "code": errors.INTERNAL_ERROR,
                "detail": "workspace baseline absent; post-state not measured",
            }
        )
        return failures
    try:
        after = snapshot.snapshot_tree(ws.root)
        added = _added_paths(baseline, after)
        allowed = d.get("expected_output_rel")
        unexpected = sorted(
            p
            for p in added
            if p != allowed and not p.startswith("logs/") and not p.startswith("temp/")
        )
        d["workspace_added_paths"] = sorted(added)
        d["unexpected_outputs"] = unexpected
        d["workspace_post_inspected"] = True
        if unexpected:
            failures.append(
                {
                    "code": errors.UNEXPECTED_OUTPUT_PRESENT,
                    "detail": str(unexpected),
                }
            )
    except (OSError, snapshot.SnapshotUninspectable) as exc:
        d["workspace_post_inspected"] = False
        failures.append(
            {
                "code": errors.INTERNAL_ERROR,
                "detail": f"workspace post-state uninspectable: {exc}",
            }
        )
    return failures


def _settle_input_verdict(ev: RunEvidence) -> None:
    """Attach INPUT_HASH_MISMATCH when a *measured* comparison disagrees.

    A missing post value is unmeasured, not changed: the post-state recorder
    already emitted ``INTERNAL_ERROR`` for it. ``INPUT_HASH_MISMATCH`` is only
    produced when both the pre and post values exist and differ, for any of the
    three declared read-only inputs (source, flags, import root).
    """
    d = ev.details
    changed = False
    pre = d.get("source_sha256_pre")
    post = d.get("source_sha256_post")
    if pre is not None and post is not None and pre != post:
        changed = True
    flags_pre = d.get("flags_sha256_pre")
    flags_post = d.get("flags_sha256_post")
    if flags_pre is not None and flags_post is not None and flags_pre != flags_post:
        changed = True
    import_pre = d.get("import_snapshot_signature_pre")
    import_post = d.get("import_snapshot_signature_post")
    if import_pre is not None and import_post is not None and import_pre != import_post:
        changed = True
    if not changed:
        return
    entry = {
        "code": errors.INPUT_HASH_MISMATCH,
        "detail": "declared read-only input changed across the run",
    }
    if ev.outcome_code is None:
        ev.outcome_code = errors.INPUT_HASH_MISMATCH
        ev.success = False
    ev.failures.append(entry)


def _added_paths(
    before: tuple[snapshot.FileEntry, ...], after: tuple[snapshot.FileEntry, ...]
) -> set[str]:
    before_map = {e.rel: e.sha256 for e in before}
    after_map = {e.rel: e.sha256 for e in after}
    added = set(after_map) - set(before_map)
    added |= {rel for rel in set(before_map) & set(after_map) if before_map[rel] != after_map[rel]}
    return added


def write_evidence(ws: workspace.Workspace, evidence: RunEvidence) -> str:
    path = os.path.join(ws.logs, "evidence.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(evidence.to_dict(), fh, indent=2, sort_keys=True)
    fh.close()
    return path
