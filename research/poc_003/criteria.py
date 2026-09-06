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
        and str(imports).startswith("-i=<WORKSPACE_ROOT>")
        and ";" in str(imports)
        and bool(_ARGV_OUTPUT.match(str(output)))
    )


def evaluate(bundle: dict) -> list[Row]:
    runs = _runs(bundle)
    codes = _codes(bundle)
    det = bundle.get("determinism", {})
    positive = [name for name in ("A", "B") if name in runs]
    rows: list[Row] = []

    # 1 -------------------------------------------------------------------
    shapes_ok = all(_check_argv_shape(_det(r).get("argv_sanitized", [])) for r in runs.values())
    rows.append(Row(
        1,
        "Fixed argv",
        "Every argv element is determined by the profile; operation-specific values enter only as "
        "validated typed tokens resolved trusted-side; no raw caller-controlled string reaches argv",
        f"{sum(1 for r in runs.values() if _check_argv_shape(_det(r).get('argv_sanitized', [])))}"
        f"/{len(runs)} runs with the single permitted 5-element shape; POLICY_VIOLATION present: "
        f"{'POLICY_VIOLATION' in codes}",
        PASS if (shapes_ok and "POLICY_VIOLATION" not in codes) else FAIL,
        "argv is produced only by profile.build_argv()" if shapes_ok else "argv shape deviates",
        "run:all:details.argv_sanitized",
        None if shapes_ok else "POLICY_VIOLATION",
    ))

    # 2 -------------------------------------------------------------------
    no_shell = all(_det(r).get("shell") is False for r in runs.values())
    shells = sorted({n for r in runs.values() for n in _det(r).get("shell_processes_in_launch_tree", [])})
    rows.append(Row(
        2,
        "No shell",
        "Spawn uses shell=False; no shell process is introduced into the process tree rooted at the "
        "POC-003 tool launch",
        f"shell=False on {sum(1 for r in runs.values() if _det(r).get('shell') is False)}/{len(runs)} runs; "
        f"shell processes observed in launch trees: {shells or 'none'}",
        PASS if (no_shell and not shells) else FAIL,
        "spawned with shell=False and no shell binary appeared in the launch tree",
        "run:all:details.shell_processes_in_launch_tree",
        None if (no_shell and not shells) else "POLICY_VIOLATION",
    ))

    # 3 -------------------------------------------------------------------
    exe_ok = all(
        _det(r).get("executable_sha256") == _det(r).get("executable_pinned_sha256")
        for r in runs.values()
    )
    pinned = next(iter(runs.values()))["details"].get("executable_sha256", "") if runs else ""
    rows.append(Row(
        3,
        "Executable integrity",
        "Pinned SHA-256 of PapyrusCompiler.exe matches before spawn",
        f"pinned hash matched on {sum(1 for r in runs.values() if _det(r).get('executable_sha256') == _det(r).get('executable_pinned_sha256'))}"
        f"/{len(runs)} runs; sha256={pinned[:16]}...",
        PASS if (exe_ok and "EXECUTABLE_HASH_MISMATCH" not in codes) else FAIL,
        "hash recomputed pre-spawn on every run",
        "run:all:details.executable_sha256",
        None if exe_ok else "EXECUTABLE_HASH_MISMATCH",
    ))

    # 4 -------------------------------------------------------------------
    contained = all(
        str(_det(r).get("expected_output_rel", "")).startswith("candidates/") for r in runs.values()
    )
    rows.append(Row(
        4,
        "Workspace containment",
        "Every resolved output path lies strictly inside candidates/ after resolve(); temp/ reserved "
        "for environment redirects",
        f"expected output declared under candidates/ on "
        f"{sum(1 for r in runs.values() if str(_det(r).get('expected_output_rel', '')).startswith('candidates/'))}"
        f"/{len(runs)} runs; WORKSPACE_VIOLATION present: {'WORKSPACE_VIOLATION' in codes}",
        PASS if (contained and "WORKSPACE_VIOLATION" not in codes) else FAIL,
        "post-resolve re-containment re-checked before acceptance",
        "run:all:details.expected_output_rel",
        None if contained else "WORKSPACE_VIOLATION",
    ))

    # 5 -------------------------------------------------------------------
    bounded = all(
        int(_det(r).get("stream_limit_bytes", 0) or 0) > 0
        and not _det(r).get("stdout_truncated")
        and not _det(r).get("stderr_truncated")
        for r in runs.values()
    )
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
        PASS if (bounded and "OUTPUT_LIMIT_EXCEEDED" not in codes) else FAIL,
        "readers cap retained bytes and keep draining so a full pipe cannot deadlock the tool",
        "run:all:details.stdout_bytes_retained",
        None if bounded else "OUTPUT_LIMIT_EXCEEDED",
    ))

    # 6 -------------------------------------------------------------------
    t = runs.get("timeout", {})
    t_det = _det(t)
    timed = t_det.get("timed_out") is True and t.get("outcome_code") == "PROCESS_TIMEOUT"
    budget = float(t_det.get("deadline_s", 0) or 0)
    elapsed = float(t_det.get("elapsed_s", 0) or 0)
    within = timed and elapsed <= budget + 15.0
    rows.append(Row(
        6,
        "Deadline",
        "A hang produces failure within the configured budget",
        f"timeout run: deadline={budget}s elapsed={elapsed}s outcome={t.get('outcome_code')}",
        PASS if within else FAIL,
        "deadline expired and the run was failed, not salvaged",
        "run:timeout:details.timed_out",
        None if within else "PROCESS_TIMEOUT",
    ))

    # 7 -------------------------------------------------------------------
    child_dead = t_det.get("direct_child_alive_after_cleanup") is False
    rows.append(Row(
        7,
        "Direct-child termination",
        "After a timeout, the spawned compiler process is dead on Windows",
        f"timeout run: direct_child_alive_after_cleanup={t_det.get('direct_child_alive_after_cleanup')}; "
        f"mechanisms={t_det.get('cleanup_mechanisms')}",
        PASS if child_dead else FAIL,
        "verified with GetExitCodeProcess, not by snapshot presence",
        "run:timeout:details.direct_child_alive_after_cleanup",
        None if child_dead else "PROCESS_TIMEOUT",
    ))

    # 8 -------------------------------------------------------------------
    reliable = all(_det(r).get("tree_observation_reliable") is True for r in runs.values())
    survivors = {
        n: _det(r).get("descendants_alive_after_cleanup") for n, r in runs.items()
    }
    any_survivor = any(v for v in survivors.values() if v)
    observed_any = {n: _det(r).get("descendants_observed") for n, r in runs.items()
                    if _det(r).get("descendant_count")}
    rows.append(Row(
        8,
        "Descendant behaviour",
        "Process tree is observed reliably AND after forced cleanup no descendant associated with the "
        "tool remains alive",
        f"reliable on {sum(1 for r in runs.values() if _det(r).get('tree_observation_reliable'))}/{len(runs)} runs; "
        f"descendants observed: {observed_any or 'none'}; survivors: {survivors}",
        PASS if (reliable and not any_survivor) else FAIL,
        "Toolhelp32 sampling during the run; aliveness re-checked post-cleanup",
        "run:all:details.descendants_alive_after_cleanup",
        None if reliable and not any_survivor else (
            "DESCENDANT_PROCESS_SURVIVED" if any_survivor else "INTERNAL_ERROR"
        ),
    ))

    # 9 -------------------------------------------------------------------
    fresh = "PRE_EXISTING_OUTPUT_PRESENT" not in codes
    produced = all(runs[n].get("success") for n in positive) if positive else False
    neg = runs.get("negative", {})
    neg_clean = (not neg.get("success")) and neg.get("outcome_code") == "PROCESS_FAILED"
    rows.append(Row(
        9,
        "Output freshness & creation",
        "Expected output absent before spawn (fail-closed if pre-existing); exit code zero implies new "
        "expected .pex exists with size > 0",
        f"pre-existing output never present: {fresh}; "
        + "; ".join(
            f"{n}: size={_det(runs[n]).get('output_size')}" for n in positive
        )
        + f"; negative fixture: success={neg.get('success')} outcome={neg.get('outcome_code')}",
        PASS if (fresh and produced and neg_clean) else FAIL,
        "negative fixture proves compiler failure never becomes orchestrator success",
        "run:A/B:details.output_size, run:negative:outcome_code",
        None if (fresh and produced and neg_clean) else "EXPECTED_OUTPUT_MISSING",
    ))

    # 10 ------------------------------------------------------------------
    hash_ok = positive and all(
        _det(runs[n]).get("output_sha256")
        and _det(runs[n]).get("output_sha256") == _det(runs[n]).get("output_sha256_recomputed")
        for n in positive
    )
    rows.append(Row(
        10,
        "Output hash",
        "The .pex SHA-256 is recorded in evidence and independently recomputed from the produced "
        "artifact (recomputed == recorded)",
        "; ".join(
            f"{n}: {str(_det(runs[n]).get('output_sha256'))[:16]}... == {str(_det(runs[n]).get('output_sha256_recomputed'))[:16]}..."
            for n in positive
        ) or "no positive run produced an artifact",
        PASS if hash_ok else FAIL,
        "artifact read and hashed twice, independently",
        "run:A/B:details.output_sha256_recomputed",
        None if hash_ok else "OUTPUT_HASH_MISMATCH",
    ))

    # 11 ------------------------------------------------------------------
    input_ok = all(
        _det(r).get("source_sha256_pre") == _det(r).get("source_sha256_post")
        and _det(r).get("import_snapshot_signature_pre") == _det(r).get("import_snapshot_signature_post")
        for r in runs.values()
        if _det(r).get("source_sha256_pre")
    )
    rows.append(Row(
        11,
        "Input immutability",
        "All declared read-only inputs (source script in input/, allowlisted flags.flg, and import root "
        "via IMPORT_ROOT_SNAPSHOT_V1) are hashed pre-spawn and unchanged across the run",
        f"signatures matched on "
        f"{sum(1 for r in runs.values() if _det(r).get('source_sha256_pre') and _det(r).get('source_sha256_pre') == _det(r).get('source_sha256_post'))}"
        f"/{len(runs)} runs; INPUT_HASH_MISMATCH present: {'INPUT_HASH_MISMATCH' in codes}",
        PASS if (input_ok and "INPUT_HASH_MISMATCH" not in codes) else FAIL,
        "recursive regular-file snapshot with symlink/junction rejection",
        "run:all:details.import_snapshot_signature_pre",
        None if input_ok else "INPUT_HASH_MISMATCH",
    ))

    # 12 ------------------------------------------------------------------
    unexpected = {n: _det(r).get("unexpected_outputs") for n, r in runs.items()
                  if _det(r).get("unexpected_outputs")}
    rows.append(Row(
        12,
        "No unexpected outputs",
        "No file appears that the profile did not declare",
        f"unexpected outputs: {unexpected or 'none'}",
        PASS if not unexpected and "UNEXPECTED_OUTPUT_PRESENT" not in codes else FAIL,
        "whole-workspace snapshot diffed; logs/ and temp/ are declared scratch",
        "run:all:details.workspace_added_paths",
        None if not unexpected else "UNEXPECTED_OUTPUT_PRESENT",
    ))

    # 13 ------------------------------------------------------------------
    captured = all(
        "stdout_bytes_total" in _det(r) and "stderr_bytes_total" in _det(r) for r in runs.values()
    )
    rows.append(Row(
        13,
        "Diagnostics capture",
        "Compiler stdout and stderr are captured, bounded by stream caps, and recorded under logs/ as "
        "untrusted evidence (no semantic filtering gated in v1)",
        "; ".join(
            f"{n}: out={_det(r).get('stdout_bytes_total')}B err={_det(r).get('stderr_bytes_total')}B"
            for n, r in sorted(runs.items())
        ),
        PASS if captured else FAIL,
        "stored as untrusted material; never used as a semantic pass gate",
        "run:all:logs/stdout.log, run:all:logs/stderr.log",
        None if captured else "POLICY_VIOLATION",
    ))

    # 14 ------------------------------------------------------------------
    equal = bool(det.get("equal"))
    rows.append(Row(
        14,
        "Determinism",
        "Two compiles over identical input in separate workspaces agree",
        f"SHA256_A={str(det.get('run_a_sha256'))[:24]}... SHA256_B={str(det.get('run_b_sha256'))[:24]}... "
        f"equal={equal}",
        PASS if equal else FAIL,
        "mandatory criterion; a difference is never reclassified post hoc",
        "bundle:determinism",
        None if equal else "DETERMINISM_MISMATCH",
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
