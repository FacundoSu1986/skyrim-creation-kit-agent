"""Tests for the mechanical evaluation of the 15 pre-registered criteria.

The evaluator must be able to fail. A gate that always returns PASS proves
nothing, so these tests feed it bundles that are known-bad in one specific way
and assert the matching row and outcome code.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from poc_003 import criteria  # noqa: E402


def _run_details(**overrides):
    details = {
        "argv_sanitized": [
            "<PAPYRUS_COMPILER_EXE>",
            "<WORKSPACE_ROOT>\\input\\Poc003Minimal.psc",
            "-f=<FLAGS_FILE>",
            "-i=<WORKSPACE_ROOT>\\imports;<WORKSPACE_ROOT>\\input",
            "-o=<WORKSPACE_ROOT>/candidates",
        ],
        "shell": False,
        "shell_processes_in_launch_tree": [],
        "executable_sha256": "aa" * 32,
        "executable_pinned_sha256": "aa" * 32,
        "expected_output_rel": "candidates/Poc003Minimal.pex",
        "stream_limit_bytes": 65536,
        "stdout_bytes_total": 10,
        "stderr_bytes_total": 0,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "source_sha256_pre": "bb" * 32,
        "source_sha256_post": "bb" * 32,
        "flags_sha256_pre": "12" * 32,
        "flags_sha256_post": "12" * 32,
        "import_snapshot_signature_pre": "cc" * 32,
        "import_snapshot_signature_post": "cc" * 32,
        "workspace_post_inspected": True,
        "output_size": 506,
        "output_sha256": "dd" * 32,
        "output_sha256_recomputed": "dd" * 32,
        "unexpected_outputs": [],
        "tree_observation_reliable": True,
        "descendant_count": 0,
        "descendants_observed": {},
        "descendants_alive_after_cleanup": [],
        "direct_child_alive_after_cleanup": False,
        "timed_out": True,
        "deadline_s": 8.0,
        "elapsed_s": 8.1,
    }
    details.update(overrides)
    return details


def _bundle(determinism_equal=True, **run_overrides):
    positive = {
        "success": True,
        "outcome_code": None,
        "details": _run_details(**run_overrides),
    }
    if run_overrides.get("_fail_positive"):
        positive = {"success": False, "outcome_code": "EXPECTED_OUTPUT_MISSING",
                    "details": _run_details()}
    return {
        "meta": {
            "fixtures": {
                "fixture_success/Poc003Minimal.psc": "ee" * 32,
                "fixture_compile_error/Poc003Broken.psc": "ff" * 32,
            }
        },
        "runs": {
            "A": dict(positive),
            "B": dict(positive),
            "negative": {
                "success": False,
                "outcome_code": "PROCESS_FAILED",
                "details": _run_details(),
            },
            "timeout": {
                "success": False,
                "outcome_code": "PROCESS_TIMEOUT",
                "details": _run_details(),
            },
        },
        "determinism": {
            "run_a_sha256": "11" * 32,
            "run_b_sha256": "11" * 32 if determinism_equal else "22" * 32,
            "equal": determinism_equal,
        },
    }


class EvaluatorTests(unittest.TestCase):
    def _verdict(self, number, bundle):
        rows = criteria.evaluate(bundle)
        row = next(r for r in rows if r.number == number)
        return row

    def test_all_mandatory_rows_are_evaluated(self):
        rows = criteria.evaluate(_bundle())
        self.assertEqual(list(range(1, 16)), [r.number for r in rows])

    def test_clean_bundle_passes_every_row(self):
        summary = criteria.summarize(criteria.evaluate(_bundle()))
        self.assertTrue(summary["all_pass"], summary)

    def test_determinism_mismatch_fails_criterion_14(self):
        row = self._verdict(14, _bundle(determinism_equal=False))
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("DETERMINISM_MISMATCH", row.outcome_code)
        summary = criteria.summarize(criteria.evaluate(_bundle(determinism_equal=False)))
        self.assertFalse(summary["all_pass"])
        self.assertIn(14, summary["failing_numbers"])

    def test_one_failure_is_never_a_pass(self):
        """14/15 is not PASS. There is no partial credit in the pre-registration."""
        summary = criteria.summarize(criteria.evaluate(_bundle(determinism_equal=False)))
        self.assertEqual(14, summary["passed"])
        self.assertEqual(1, summary["failed"])
        self.assertFalse(summary["all_pass"])

    def test_shell_in_launch_tree_fails_criterion_2(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["shell_processes_in_launch_tree"] = ["cmd.exe"]
        row = self._verdict(2, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("POLICY_VIOLATION", row.outcome_code)

    def test_executable_hash_mismatch_fails_criterion_3(self):
        bundle = _bundle()
        bundle["runs"]["B"]["details"]["executable_sha256"] = "99" * 32
        self.assertEqual("FAIL", self._verdict(3, bundle).verdict)

    def test_unreliable_tree_fails_criterion_8_with_internal_error(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["tree_observation_reliable"] = False
        row = self._verdict(8, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_surviving_descendant_fails_criterion_8(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["descendant_count"] = 1
        bundle["runs"]["A"]["details"]["descendants_observed"] = {"1234": "PapyrusAssembler.exe"}
        bundle["runs"]["A"]["details"]["descendants_alive_after_cleanup"] = [1234]
        row = self._verdict(8, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("DESCENDANT_PROCESS_SURVIVED", row.outcome_code)

    def test_input_mutation_fails_criterion_11(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["source_sha256_post"] = "ab" * 32
        self.assertEqual("FAIL", self._verdict(11, bundle).verdict)

    def test_flags_mutation_fails_criterion_11(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["flags_sha256_post"] = "ab" * 32
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INPUT_HASH_MISMATCH", row.outcome_code)

    def test_import_mutation_fails_criterion_11(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["import_snapshot_signature_post"] = "ab" * 32
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INPUT_HASH_MISMATCH", row.outcome_code)

    def test_missing_flags_post_evidence_makes_criterion_11_fail(self):
        bundle = _bundle()
        del bundle["runs"]["A"]["details"]["flags_sha256_post"]
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_missing_source_post_evidence_makes_criterion_11_fail(self):
        bundle = _bundle()
        del bundle["runs"]["B"]["details"]["source_sha256_post"]
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_missing_import_post_evidence_makes_criterion_11_fail(self):
        bundle = _bundle()
        del bundle["runs"]["A"]["details"]["import_snapshot_signature_post"]
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_missing_flags_pre_evidence_makes_criterion_11_fail(self):
        """A run that never reached the pre-state cannot pass criterion 11."""
        bundle = _bundle()
        del bundle["runs"]["timeout"]["details"]["flags_sha256_pre"]
        row = self._verdict(11, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_missing_workspace_post_inspection_makes_criterion_12_fail(self):
        """Absent post-state must FAIL: missing evidence is not an empty list."""
        bundle = _bundle()
        del bundle["runs"]["A"]["details"]["workspace_post_inspected"]
        row = self._verdict(12, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_missing_unexpected_outputs_field_makes_criterion_12_fail(self):
        bundle = _bundle()
        del bundle["runs"]["A"]["details"]["unexpected_outputs"]
        row = self._verdict(12, bundle)
        self.assertEqual("FAIL", row.verdict)
        self.assertEqual("INTERNAL_ERROR", row.outcome_code)

    def test_empty_runs_fails_closed(self):
        """A truncated bundle must render a failing matrix, not a passing one."""
        bundle = _bundle()
        bundle["runs"] = {}
        bundle["determinism"] = {"equal": True, "run_a_sha256": "11" * 32, "run_b_sha256": "11" * 32}
        rows = criteria.evaluate(bundle)
        for number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
            self.assertEqual(
                "FAIL",
                next(r for r in rows if r.number == number).verdict,
                f"criterion {number} must fail closed with no runs",
            )
        summary = criteria.summarize(rows)
        self.assertFalse(summary["all_pass"])

    def test_unexpected_output_fails_criterion_12(self):
        bundle = _bundle()
        bundle["runs"]["A"]["details"]["unexpected_outputs"] = ["stray.txt"]
        self.assertEqual("FAIL", self._verdict(12, bundle).verdict)

    def test_negative_fixture_accepted_is_not_success(self):
        bundle = _bundle()
        bundle["runs"]["negative"] = {
            "success": True,
            "outcome_code": None,
            "details": _run_details(),
        }
        self.assertEqual("FAIL", self._verdict(9, bundle).verdict)

    def test_matrix_renders_one_row_per_criterion(self):
        rows = criteria.evaluate(_bundle())
        table = criteria.render_markdown(rows)
        self.assertEqual(17, len(table.strip().splitlines()))


if __name__ == "__main__":
    unittest.main()
