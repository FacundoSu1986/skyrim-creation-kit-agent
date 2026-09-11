"""Mechanical evaluation of the 15 pre-registered POC-003 criteria.

The wording and the pass rules come from
``docs/research/2026-09-01-poc-003-pre-registration.md``. Nothing here rewrites
them to fit an observation: each row maps a criterion to the evidence the
harness actually recorded and returns ``PASS``/``FAIL``.

``FAIL`` is a gate verdict for a criterion, not a repository status. Repository
status stays in the canonical vocabulary (``NO VERIFICADO`` / ``PASS``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

PASS = "PASS"
FAIL = "FAIL"

_ARGV_SOURCE = re.compile(r"^<WORKSPACE_ROOT>[/\\]input[/\\][A-Za-z0-9._-]+\.psc$")
#: Windows renders the sanitized separator as "\"; a POSIX run would render
#: "/". Both are the same resolved path, so the shape check accepts either.
_ARGV_OUTPUT = re.compile(r"^-o=<WORKSPACE_ROOT>[/\\]candidates$")
_ARGV_IMPORTS = re.compile(
    r"^-i=<WORKSPACE_ROOT>[/\\]imports;<WORKSPACE_ROOT>[/\\]input$"
)


@dataclass
class Row:
    number: int
    criterion: str
    required_evidence: str
    observed_evidence: str = ""
    verdict: str = FAIL
    reason: str = ""
    artifact: str = ""
    outcome_code: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "number": self.number,
            "criterion": self.criterion,
            "required_evidence": self.required_evidence,
            "observed_evidence": self.observed_evidence,
            "verdict": self.verdict,
            "reason": self.reason,
            "artifact": self.artifact,
            "outcome_code": self.outcome_code,
        }


def _runs(bundle: dict) -> dict[str, dict]:
    return bundle.get("runs", {})


def _det(run: dict) -> dict:
    return run.get("details", {})


def _codes(bundle: dict) -> set[str]:
    out: set[str] = set()
    for run in _runs(bundle).values():
        code = run.get("outcome_code")
        if code:
            out.add(code)
    return out


def _check_argv_shape(argv: list[str]) -> bool:
    if not isinstance(argv, list) or len(argv) != 5:
        return False
    exe, source, flags, imports, output = argv
    return bool(
        exe == "<PAPYRUS_COMPILER_EXE>"
        and _ARGV_SOURCE.match(str(source))
        and str(flags) == "-f=<FLAGS_FILE>"
        and _ARGV_IMPORTS.match(str(imports))
        and bool(_ARGV_OUTPUT.match(str(output)))
    )


def evaluate(bundle: dict) -> list[Row]:
    runs = _runs(bundle)
    has_runs = bool(runs)
    codes = _codes(bundle)
    det = bundle.get("determinism", {})
    positive = [name for name in ("A", "B") if name in runs]
    # ``positive`` only asks whether a run *exists* under that name, so a bundle
    # with a single positive run (or with A present but failed) would let
    # criteria 9, 10 and 14 pass on one artifact. Determinism and the artifact
    # gates are comparisons between two independent successes, so require both.
    both_positive = all(
        isinstance(runs.get(n), dict) and runs[n].get("success") for n in ("A", "B")
    )
    rows: list[Row] = []

    # 1 -------------------------------------------------------------------
    shapes_ok = has_runs and all(
        _check_argv_shape(_det(r).get("argv_sanitized", [])) for r in runs.values()
    )
    verdict_1 = PASS if (shapes_ok and "POLICY_VIOLATION" not in codes) else FAIL
    rows.append(Row(
        1,
        "Fixed argv",
        "Every argv element is determined by the profile; operation-specific values enter only as "
        "validated typed tokens resolved trusted-side; no raw caller-controlled string reaches argv",
        f"{sum(1 for r in runs.values() if _check_argv_shape(_det(r).get('argv_sanitized', []))) if has_runs else 0}"
        f"/{len(runs)} runs with the single permitted 5-element shape; POLICY_VIOLATION present: "
        f"{'POLICY_VIOLATION' in codes}",
        verdict_1,
        "argv is produced only by profile.build_argv()"
        if verdict_1 == PASS
        else "no runs recorded or argv shape deviates",
        "run:all:details.argv_sanitized",
        None if verdict_1 == PASS else "POLICY_VIOLATION",
    ))

    # 2 -------------------------------------------------------------------
    no_shell = has_runs and all(_det(r).get("shell") is False for r in runs.values())
    shells = sorted({n for r in runs.values() for n in _det(r).get("shell_processes_in_launch_tree", [])})
    verdict_2 = PASS if (no_shell and not shells) else FAIL
    rows.append(Row(
        2,
        "No shell",
        "Spawn uses shell=False; no shell process is introduced into the process tree rooted at the "
        "POC-003 tool launch",
        f"shell=False on {sum(1 for r in runs.values() if _det(r).get('shell') is False)}/{len(runs)} runs; "
        f"shell processes observed in launch trees: {shells or 'none'}",
        verdict_2,
        "spawned with shell=False and no shell binary appeared in the launch tree"
        if verdict_2 == PASS
        else "no runs recorded, a shell was used, or a shell binary entered the launch tree",
        "run:all:details.shell_processes_in_launch_tree",
        None if verdict_2 == PASS else "POLICY_VIOLATION",
    ))

    # 3 -------------------------------------------------------------------
    exe_ok = has_runs and all(
        _det(r).get("executable_sha256") == _det(r).get("executable_pinned_sha256")
        for r in runs.values()
    )
    pinned = next(iter(runs.values()))["details"].get("executable_sha256", "") if runs else ""
    verdict_3 = PASS if (exe_ok and "EXECUTABLE_HASH_MISMATCH" not in codes) else FAIL
    rows.append(Row(
        3,
        "Executable integrity",
        "Pinned SHA-256 of PapyrusCompiler.exe matches before spawn",
        f"pinned hash matched on {sum(1 for r in runs.values() if _det(r).get('executable_sha256') == _det(r).get('executable_pinned_sha256'))}"
        f"/{len(runs)} runs; sha256={pinned[:16]}...",
        verdict_3,
        "hash recomputed pre-spawn on every run"
        if verdict_3 == PASS
        else "no runs recorded or pinned hash did not match on every run",
        "run:all:details.executable_sha256",
        None if verdict_3 == PASS else "EXECUTABLE_HASH_MISMATCH",
    ))

    # 4 -------------------------------------------------------------------
    contained = has_runs and all(
        str(_det(r).get("expected_output_rel", "")).startswith("candidates/") for r in runs.values()
    )
    verdict_4 = PASS if (contained and "WORKSPACE_VIOLATION" not in codes) else FAIL
    rows.append(Row(
        4,
        "Workspace containment",
        "Every resolved output path lies strictly inside candidates/ after resolve(); temp/ reserved "
        "for environment redirects",
        f"expected output declared under candidates/ on "
        f"{sum(1 for r in runs.values() if str(_det(r).get('expected_output_rel', '')).startswith('candidates/'))}"
        f"/{len(runs)} runs; WORKSPACE_VIOLATION present: {'WORKSPACE_VIOLATION' in codes}",
        verdict_4,
        "post-resolve re-containment re-checked before acceptance"
        if verdict_4 == PASS
        else "no runs recorded or an output path resolved outside candidates/",
        "run:all:details.expected_output_rel",
        None if verdict_4 == PASS else "WORKSPACE_VIOLATION",
    ))

    # 5 -------------------------------------------------------------------
    bounded = has_runs and all(
        int(_det(r).get("stream_limit_bytes", 0) or 0) > 0
        and not _det(r).get("stdout_truncated")
        and not _det(r).get("stderr_truncated")
        for r in runs.values()
    )
    verdict_5 = PASS if (bounded and "OUTPUT_LIMIT_EXCEEDED" not in codes) else FAIL
    rows.append(Row(
        5,
        "Bounded output",
        "stdout and stderr are capped during transfer, not after",
        "caps=" + ", ".join(
            f"{n}:{_det(r).get('stream_limit_bytes')}B(retained "
            f"{_det(r).get('stdout_bytes_retained')}/{_det(r).get('stderr_bytes_retained')}, "
            f"truncated={_det(r).get('stdout_truncated')}/{_det(r).get('stderr_truncated')})"
            for n, r in sorted(runs.items())
        ),
        verdict_5,
        "readers cap retained bytes and keep draining so a full pipe cannot deadlock the tool"
        if verdict_5 == PASS
        else "no runs recorded or a stream exceeded its cap",
        "run:all:details.stdout_bytes_retained",
        None if verdict_5 == PASS else "OUTPUT_LIMIT_EXCEEDED",
    ))

    # 6 -------------------------------------------------------------------
    t = runs.get("timeout", {})
    t_det = _det(t)
    timed = t_det.get("timed_out") is True and t.get("outcome_code") == "PROCESS_TIMEOUT"
    budget = float(t_det.get("deadline_s", 0) or 0)
    elapsed = float(t_det.get("elapsed_s", 0) or 0)
    within = has_runs and timed and elapsed <= budget + 15.0
    verdict_6 = PASS if within else FAIL
    rows.append(Row(
        6,
        "Deadline",
        "A hang produces failure within the configured budget",
        f"timeout run: deadline={budget}s elapsed={elapsed}s outcome={t.get('outcome_code')}",
        verdict_6,
        "deadline expired and the run was failed, not salvaged"
        if verdict_6 == PASS
        else "no runs recorded or the timeout run did not fail inside the configured budget",
        "run:timeout:details.timed_out",
        None if verdict_6 == PASS else "PROCESS_TIMEOUT",
    ))

    # 7 -------------------------------------------------------------------
    child_dead = t_det.get("direct_child_alive_after_cleanup") is False
    verdict_7 = PASS if (has_runs and child_dead) else FAIL
    rows.append(Row(
        7,
        "Direct-child termination",
        "After a timeout, the spawned compiler process is dead on Windows",
        f"timeout run: direct_child_alive_after_cleanup={t_det.get('direct_child_alive_after_cleanup')}; "
        f"mechanisms={t_det.get('cleanup_mechanisms')}",
        verdict_7,
        "verified with GetExitCodeProcess, not by snapshot presence"
        if verdict_7 == PASS
        else "no runs recorded or the direct child was alive after cleanup",
        "run:timeout:details.direct_child_alive_after_cleanup",
        None if verdict_7 == PASS else "PROCESS_TIMEOUT",
    ))

    # 8 -------------------------------------------------------------------
    reliable = has_runs and all(_det(r).get("tree_observation_reliable") is True for r in runs.values())
    survivors = {
        n: _det(r).get("descendants_alive_after_cleanup") for n, r in runs.items()
    }
    any_survivor = any(v for v in survivors.values() if v)
    observed_any = {n: _det(r).get("descendants_observed") for n, r in runs.items()
                    if _det(r).get("descendant_count")}
    verdict_8 = PASS if (reliable and not any_survivor) else FAIL
    rows.append(Row(
        8,
        "Descendant behaviour",
        "Process tree is observed reliably AND after forced cleanup no descendant associated with the "
        "tool remains alive",
        f"reliable on {sum(1 for r in runs.values() if _det(r).get('tree_observation_reliable'))}/{len(runs)} runs; "
        f"descendants observed: {observed_any or 'none'}; survivors: {survivors}",
        verdict_8,
        "Toolhelp32 sampling during the run; aliveness re-checked post-cleanup"
        if verdict_8 == PASS
        else "no runs recorded, the tree was unmeasurable, or a descendant survived cleanup",
        "run:all:details.descendants_alive_after_cleanup",
        None if verdict_8 == PASS else (
            "DESCENDANT_PROCESS_SURVIVED" if any_survivor else "INTERNAL_ERROR"
        ),
    ))

    # 9 -------------------------------------------------------------------
    fresh = "PRE_EXISTING_OUTPUT_PRESENT" not in codes
    produced = both_positive
    neg = runs.get("negative", {})
    neg_clean = (not neg.get("success")) and neg.get("outcome_code") == "PROCESS_FAILED"
    # Exit code 0 is necessary but NOT sufficient: the artifact gate rejects a
    # missing or empty .pex as EXPECTED_OUTPUT_MISSING even when the tool
    # exited 0 (observed on the ``long`` run). The gate is what makes ``success``
    # true, so the observed evidence names it explicitly.
    verdict_9 = PASS if (fresh and produced and neg_clean) else FAIL
    rows.append(Row(
        9,
        "Output freshness & creation",
        "Expected output absent before spawn (fail-closed if pre-existing); exit code zero implies new "
        "expected .pex exists with size > 0",
        f"pre-existing output never present: {fresh}; "
        + "; ".join(
            # ``outcome_code`` is null on a successful run (no failure code is
            # set), so printing it under the label ``exit`` rendered
            # ``exit=None`` for runs whose real exit code was measured as 0.
            # Criterion 9 is about the exit code, so read the measured one.
            f"{n}: size={_det(runs[n]).get('output_size')} "
            f"exit={_det(runs[n]).get('exit_code')}"
            for n in positive
        )
        + f"; negative fixture: success={neg.get('success')} outcome={neg.get('outcome_code')}",
        verdict_9,
        "exit 0 is gated by the artifact check: a missing or empty .pex is "
        "EXPECTED_OUTPUT_MISSING, never orchestrator success"
        if verdict_9 == PASS
        else "pre-existing output, a missing artifact, or a negative fixture reported as success",
        "run:A/B:details.output_size, run:A/B:details.exit_code, run:negative:outcome_code",
        None if verdict_9 == PASS else "EXPECTED_OUTPUT_MISSING",
    ))

    # 10 ------------------------------------------------------------------
    hash_ok = both_positive and all(
        _det(runs[n]).get("output_sha256")
        and _det(runs[n]).get("output_sha256") == _det(runs[n]).get("output_sha256_recomputed")
        for n in positive
    )
    verdict_10 = PASS if hash_ok else FAIL
    rows.append(Row(
        10,
        "Output hash",
        "The .pex SHA-256 is recorded in evidence and independently recomputed from the produced "
        "artifact (recomputed == recorded)",
        "; ".join(
            f"{n}: {str(_det(runs[n]).get('output_sha256'))[:16]}... == {str(_det(runs[n]).get('output_sha256_recomputed'))[:16]}..."
            for n in positive
        ) or "no positive run produced an artifact",
        verdict_10,
        "artifact read and hashed twice, independently"
        if verdict_10 == PASS
        else "no positive artifact, or recomputed hash disagreed with the recorded hash",
        "run:A/B:details.output_sha256_recomputed",
        None if verdict_10 == PASS else "OUTPUT_HASH_MISMATCH",
    ))

    # 11 ------------------------------------------------------------------
    # The pre-registration names three declared read-only inputs — source
    # script, flags.flg and the import root — and each must be recorded
    # pre-spawn AND remain unchanged across the run. Absent post-state
    # evidence is NOT "unchanged" (``None == None`` is not evidence): every
    # run must carry all six values per input, and any demonstrated difference
    # fails the run.

    def _input_status(run: dict) -> dict[str, str]:
        det = _det(run)
        status: dict[str, str] = {}
        for label, pre_key, post_key in (
            ("source", "source_sha256_pre", "source_sha256_post"),
            ("flags", "flags_sha256_pre", "flags_sha256_post"),
            ("imports", "import_snapshot_signature_pre", "import_snapshot_signature_post"),
        ):
            pre = det.get(pre_key)
            post = det.get(post_key)
            if pre is None or post is None:
                status[label] = "MISSING"
            elif pre != post:
                status[label] = "CHANGED"
            else:
                status[label] = "OK"
        return status

    input_status = {n: _input_status(r) for n, r in runs.items()}
    input_ok = has_runs and all(
        all(state == "OK" for state in input_status[n].values()) for n in runs
    )
    # With no runs at all nothing was measured, which is the same failure mode
    # as a missing post-state: unmeasured, not changed. Without this the row
    # would report INPUT_HASH_MISMATCH and assert "an input changed" when no
    # input was ever looked at.
    inputs_unmeasured = (not has_runs) or any(
        "MISSING" in input_status[n].values() for n in runs
    )
    verdict_11 = PASS if (input_ok and "INPUT_HASH_MISMATCH" not in codes) else FAIL
    rows.append(Row(
        11,
        "Input immutability",
        "All declared read-only inputs (source script in input/, allowlisted flags.flg, and import root "
        "via IMPORT_ROOT_SNAPSHOT_V1) are hashed pre-spawn and unchanged across the run",
        "; ".join(
            f"{n}: source={input_status[n].get('source')} flags={input_status[n].get('flags')} "
            f"imports={input_status[n].get('imports')}"
            for n in sorted(runs)
        ) or "no runs recorded",
        verdict_11,
        "presence AND concordance of source, flags and imports verified on every run"
        if verdict_11 == PASS
        else (
            "missing post-state evidence cannot pass (fail closed as INTERNAL_ERROR)"
            if inputs_unmeasured
            else "a declared read-only input changed across a run"
        ),
        "run:all:details.source/flags/imports pre+post",
        None if verdict_11 == PASS else (
            "INTERNAL_ERROR" if inputs_unmeasured else "INPUT_HASH_MISMATCH"
        ),
    ))

    # 12 ------------------------------------------------------------------
    # Criterion 12 is measured on every path that recorded a pre-spawn
    # baseline (success, PROCESS_FAILED, PROCESS_TIMEOUT, ...). A missing
    # ``workspace_post_inspected`` means the inspection never ran or was
    # impossible, and that FAILS the criterion: the absence of an
    # ``unexpected_outputs`` field is NOT read as "no unexpected outputs".
    inspected = has_runs and all(
        _det(r).get("workspace_post_inspected") is True for r in runs.values()
    )
    # Presence is not shape. A string or object in this field would satisfy
    # ``"unexpected_outputs" in det`` while carrying no usable list, and the
    # flagging loop below only reads lists, so it would silently find nothing.
    unexpected_present = has_runs and all(
        isinstance(_det(r).get("unexpected_outputs"), list) for r in runs.values()
    )
    all_unexpected: dict[str, list[str]] = {}
    for n, r in runs.items():
        outs = _det(r).get("unexpected_outputs")
        if isinstance(outs, list):
            flagged = [p for p in outs if p]
            if flagged:
                all_unexpected[n] = flagged
    verdict_12 = PASS if (
        inspected and unexpected_present and not all_unexpected
        and "UNEXPECTED_OUTPUT_PRESENT" not in codes
    ) else FAIL
    rows.append(Row(
        12,
        "No unexpected outputs",
        "No file appears that the profile did not declare",
        "; ".join(
            f"{n}: inspected={_det(r).get('workspace_post_inspected')} "
            f"unexpected={_det(r).get('unexpected_outputs')}"
            for n, r in sorted(runs.items())
        ) or "no runs recorded",
        verdict_12,
        "whole-workspace snapshot diffed against the pre-spawn baseline on every "
        "run; logs/ and temp/ are declared scratch"
        if verdict_12 == PASS
        else (
            "workspace post-state was not inspected on every run"
            if not (inspected and unexpected_present)
            else "an undeclared output appeared outside the declared output/scratch areas"
        ),
        "run:all:details.workspace_post_inspected, run:all:details.unexpected_outputs",
        None if verdict_12 == PASS else (
            "UNEXPECTED_OUTPUT_PRESENT" if all_unexpected else "INTERNAL_ERROR"
        ),
    ))

    # 13 ------------------------------------------------------------------
    captured = has_runs and all(
        "stdout_bytes_total" in _det(r) and "stderr_bytes_total" in _det(r) for r in runs.values()
    )
    verdict_13 = PASS if (captured and "TOOL_DIAGNOSTICS_REJECTED" not in codes) else FAIL
    rows.append(Row(
        13,
        "Diagnostics capture",
        "Compiler stdout and stderr are captured, bounded by stream caps, and recorded under logs/ as "
        "untrusted evidence (no semantic filtering gated in v1)",
        "; ".join(
            f"{n}: out={_det(r).get('stdout_bytes_total')}B err={_det(r).get('stderr_bytes_total')}B"
            for n, r in sorted(runs.items())
        ),
        verdict_13,
        "stored as untrusted material; never used as a semantic pass gate"
        if verdict_13 == PASS
        else "no runs recorded or capture evidence is missing",
        "run:all:logs/stdout.log, run:all:logs/stderr.log",
        None if verdict_13 == PASS else "POLICY_VIOLATION",
    ))

    # 14 ------------------------------------------------------------------
    run_a_hash = _det(runs.get("A", {})).get("output_sha256")
    run_b_hash = _det(runs.get("B", {})).get("output_sha256")
    hashes_present = bool(run_a_hash and run_b_hash)
    recomputed_equal = bool(hashes_present and run_a_hash == run_b_hash)
    bundle_a_hash = det.get("run_a_sha256")
    bundle_b_hash = det.get("run_b_sha256")
    bundle_equal = det.get("equal")

    consistent = bool(
        both_positive
        and hashes_present
        and bundle_a_hash == run_a_hash
        and bundle_b_hash == run_b_hash
        and bundle_equal == recomputed_equal
    )
    equal = bool(consistent and recomputed_equal)
    verdict_14 = PASS if equal else FAIL
    rows.append(Row(
        14,
        "Determinism",
        "Two compiles over identical input in separate workspaces agree",
        f"SHA256_A={str(det.get('run_a_sha256'))[:24]}... SHA256_B={str(det.get('run_b_sha256'))[:24]}... "
        f"equal={equal}",
        verdict_14,
        "mandatory criterion; a difference is never reclassified post hoc"
        if verdict_14 == PASS
        else "no positive runs, or the two artifacts' SHA-256 digests differ",
        "bundle:determinism",
        None if verdict_14 == PASS else "DETERMINISM_MISMATCH",
    ))

    # 15 ------------------------------------------------------------------
    fixtures = bundle.get("meta", {}).get("fixtures", {})
    # The criterion is about .psc provenance. Documentation committed beside
    # the fixtures is not a compiled source and is not what the gate names.
    scripts = sorted(rel for rel in fixtures if rel.endswith(".psc"))
    provenance_ok = bool(scripts) and all(
        rel.startswith("fixture_success/") or rel.startswith("fixture_compile_error/")
        for rel in scripts
    )
    rows.append(Row(
        15,
        "Fixture provenance",
        "No Bethesda-authored .psc is committed; the fixture is own-authored",
        f"in-repo .psc fixtures hashed: {len(scripts)}: {', '.join(scripts)}"
        f" (non-.psc fixture files: {len(fixtures) - len(scripts)})",
        PASS if provenance_ok else FAIL,
        "fixtures are synthetic and redistributable under this repository's license",
        "research/poc_003/fixtures/",
        None if provenance_ok else "POLICY_VIOLATION",
    ))

    return rows


def summarize(rows: list[Row]) -> dict[str, object]:
    failed = [r for r in rows if r.verdict == FAIL]
    return {
        "total": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "failing_numbers": [r.number for r in failed],
        "all_pass": not failed,
    }


def render_markdown(rows: list[Row]) -> str:
    lines = [
        "| # | Criterion | Required evidence | Observed evidence | Verdict | Reason | Reference |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        def cell(text: str) -> str:
            return str(text).replace("|", "\\|").replace("\n", " ")

        lines.append(
            f"| {r.number} | {cell(r.criterion)} | {cell(r.required_evidence)} | "
            f"{cell(r.observed_evidence)} | **{r.verdict}** | {cell(r.reason)} | `{cell(r.artifact)}` |"
        )
    return "\n".join(lines)


def write_matrix(rows: list[Row], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_markdown(rows) + "\n")
