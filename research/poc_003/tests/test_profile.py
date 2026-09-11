"""Closed-world profile tests: unknown tokens, escapes, argv shape, environment."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from poc_003 import errors, profile  # noqa: E402

BAD_TOKENS = (
    "",
    "..",
    "../evil",
    "a/../../evil",
    "C:evil",
    "\\\\server\\share\\x",
    "has space",
    "has;semicolon",
    "leading-dash",
    "x" * 65,
    "NotInAllowlist",
    "Poc003Minimal/../../x",
)


class TokenGrammarTests(unittest.TestCase):
    def test_rejects_escapes_and_unknown_tokens(self):
        for bad in BAD_TOKENS:
            with self.subTest(token=bad):
                with self.assertRaises(profile.ProfileViolation):
                    profile.validate_token(bad)

    def test_accepts_allowlisted_tokens(self):
        for good in ("Poc003Minimal", "Poc003Broken", "Poc003Hang"):
            self.assertEqual(good, profile.validate_token(good))

    def test_operation_enum_is_closed(self):
        self.assertNotIn("run_command", profile.ALLOWED_OPERATIONS)
        self.assertNotIn("execute_process", profile.ALLOWED_OPERATIONS)
        self.assertEqual(1, len(profile.ALLOWED_OPERATIONS))


class ArgvShapeTests(unittest.TestCase):
    def test_argv_has_no_free_form_element(self):
        cfg = profile.LocalConfig(
            executable=r"G:\x\PapyrusCompiler.exe",
            executable_sha256="0" * 64,
            flags=r"G:\x\flags.flg",
            flags_sha256="0" * 64,
        )
        argv = profile.build_argv(cfg, r"W:\input\Poc003Minimal.psc", r"W:\input", r"W:\imports", r"W:\candidates")
        self.assertEqual(5, len(argv))
        self.assertEqual(cfg.executable, argv[0])
        self.assertEqual(1, sum(1 for a in argv[1:] if a.startswith("-f=")))
        self.assertEqual(1, sum(1 for a in argv[1:] if a.startswith("-i=")))
        self.assertEqual(1, sum(1 for a in argv[1:] if a.startswith("-o=")))
        self.assertTrue(argv[2].startswith("-f="))
        self.assertIn(";", argv[3])

    def test_token_cannot_reach_argv_unvalidated(self):
        """A traversal token must raise before it is ever resolved to a path."""
        with self.assertRaises(profile.ProfileViolation):
            profile.validate_token("../../Windows/System32/evil")


class EnvironmentTests(unittest.TestCase):
    def test_environment_is_deny_by_default(self):
        env = profile.build_environment(r"W:\temp")
        self.assertEqual({"SystemRoot", "COMSPEC", "PATH", "TEMP", "TMP"}, set(env))
        self.assertNotIn("USERPROFILE", env)
        self.assertNotIn("APPDATA", env)
        self.assertEqual(env["TEMP"], env["TMP"])

    def test_temp_is_redirected_into_workspace(self):
        import tempfile

        env = profile.build_environment(os.path.join(tempfile.gettempdir(), "poc003-temp-test"))
        self.assertNotEqual(env["TEMP"], os.environ.get("TEMP"))


class ConfigValidationTests(unittest.TestCase):
    def test_non_object_json_config_is_rejected(self):
        import json
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(["not", "an", "object"], handle)
            path = handle.name
        self.addCleanup(os.unlink, path)
        with self.assertRaises(profile.ProfileViolation):
            profile.LocalConfig.from_file(path)

    def test_malformed_json_config_is_rejected(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{ not json")
            path = handle.name
        self.addCleanup(os.unlink, path)
        with self.assertRaises(profile.ProfileViolation):
            profile.LocalConfig.from_file(path)


class TaxonomyTests(unittest.TestCase):
    def test_transport_bound_codes_are_never_declared(self):
        """ADR-004 E8: nine codes cannot fire without a wire transport."""
        self.assertEqual(9, len(errors.NOT_APPLICABLE))
        self.assertFalse(errors.DECLARED_OUTCOME_SET & errors.NOT_APPLICABLE)
        for code in ("ASSERTION_FAILED", "RECEIPT_MISMATCH", "INVALID_RESPONSE"):
            self.assertIn(code, errors.NOT_APPLICABLE)

    def test_undeclared_code_cannot_be_constructed(self):
        with self.assertRaises(ValueError):
            errors.EtecFailure("ASSERTION_FAILED", "nope")


if __name__ == "__main__":
    unittest.main()
