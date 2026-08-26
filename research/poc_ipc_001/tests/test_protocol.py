"""Unit tests: protocol primitives (strict JSON, identifiers, bounds)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import errors  # noqa: E402
import protocol  # noqa: E402
from schemas import classify_protocol_version, validate_request  # noqa: E402


class StrictJsonTests(unittest.TestCase):
    def test_valid_document_decodes(self):
        obj = protocol.strict_json_loads(b'{"a":1,"b":[true,null]}')
        self.assertEqual(obj, {"a": 1, "b": [True, None]})

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'\xff\xfe{"a":1}')

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'{"score":NaN}')

    def test_infinity_rejected(self):
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'{"v":Infinity}')
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'{"v":-Infinity}')

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'{"a":1,"a":2}')

    def test_trailing_data_rejected(self):
        with self.assertRaises(ValueError):
            protocol.strict_json_loads(b'{"a":1} {"b":2}')

    def test_dumps_is_deterministic(self):
        first = protocol.strict_json_dumps({"b": 1, "a": 2})
        second = protocol.strict_json_dumps({"a": 2, "b": 1})
        self.assertEqual(first, second)


class ExactIntTests(unittest.TestCase):
    def test_bool_is_not_int(self):
        self.assertFalse(protocol.is_exact_int(True))
        self.assertFalse(protocol.is_exact_int(False))

    def test_int_passes(self):
        self.assertTrue(protocol.is_exact_int(1))
        self.assertTrue(protocol.is_exact_int(0))

    def test_float_and_str_fail(self):
        self.assertFalse(protocol.is_exact_int(1.0))
        self.assertFalse(protocol.is_exact_int("1"))


class ProtocolVersionClassificationTests(unittest.TestCase):
    def test_true_maps_to_invalid_request(self):
        ok, code, _ = classify_protocol_version(True)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_float_maps_to_invalid_request(self):
        ok, code, _ = classify_protocol_version(1.0)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_string_maps_to_invalid_request(self):
        ok, code, _ = classify_protocol_version("1")
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_integer_two_maps_to_unsupported(self):
        ok, code, _ = classify_protocol_version(2)
        self.assertFalse(ok)
        self.assertEqual(code, errors.UNSUPPORTED_PROTOCOL_VERSION)

    def test_one_is_supported(self):
        ok, code, _ = classify_protocol_version(1)
        self.assertTrue(ok)
        self.assertIsNone(code)


class RequestIdTests(unittest.TestCase):
    def test_generated_ids_are_canonical_v4(self):
        for _ in range(25):
            rid = protocol.new_request_id()
            self.assertEqual(len(rid), 36)
            self.assertTrue(protocol.validate_request_id(rid))

    def test_uppercase_rejected(self):
        self.assertFalse(
            protocol.validate_request_id(
                "A0F0E0D0-1111-4222-8333-444455556666".replace("A", "a").upper()
            )
        )

    def test_v1_style_nibble_rejected(self):
        self.assertFalse(
            protocol.validate_request_id("a0f0e0d0-1111-1222-8333-444455556666")
        )

    def test_bad_variant_nibble_rejected(self):
        self.assertFalse(
            protocol.validate_request_id("a0f0e0d0-1111-4222-7333-444455556666")
        )

    def test_malformed_rejected(self):
        for bad in ("", "not-a-uuid", "zzzzzzzz-zzzz-4zzz-8zzz-zzzzzzzzzzzz"):
            self.assertFalse(protocol.validate_request_id(bad))

    def test_wrong_length_rejected(self):
        self.assertFalse(protocol.validate_request_id("a" * 64))

    def test_non_string_types_rejected(self):
        for bad in (None, 5, True, 1.5, b"x"):
            self.assertFalse(protocol.validate_request_id(bad))


class JobIdTests(unittest.TestCase):
    def test_valid_ids_accepted(self):
        for good in ("JOB-1", "job.underscore-x", "A" * 64, "Job_01"):
            self.assertTrue(protocol.validate_job_id(good), good)

    def test_dotdot_substring_rejected_even_inside(self):
        self.assertFalse(protocol.validate_job_id("JOB..X"))
        self.assertFalse(protocol.validate_job_id("..JOB"))

    def test_dot_forms_rejected(self):
        self.assertFalse(protocol.validate_job_id("."))
        self.assertFalse(protocol.validate_job_id(".."))
        # leading dot fails the character class anyway
        self.assertFalse(protocol.validate_job_id(".hidden"))

    def test_separators_and_drives_rejected(self):
        for bad in ("A/B", "A\\B", "C:X", "A B", "A:B", "//server", "a:b"):
            self.assertFalse(protocol.validate_job_id(bad))

    def test_length_bound(self):
        self.assertTrue(protocol.validate_job_id("A" * 64))
        self.assertFalse(protocol.validate_job_id("A" * 65))

    def test_non_string_rejected(self):
        self.assertFalse(protocol.validate_job_id(123))
        self.assertFalse(protocol.validate_job_id(None))

    def test_safe_name_matches_job_discipline(self):
        self.assertTrue(protocol.validate_safe_name("fixture.txt"))
        self.assertFalse(protocol.validate_safe_name("../secret.txt"))


class HashFormatTests(unittest.TestCase):
    GOOD = "a" * 64

    def test_good_hash(self):
        self.assertTrue(protocol.validate_hash_format(self.GOOD))

    def test_uppercase_rejected(self):
        self.assertFalse(protocol.validate_hash_format(self.GOOD.upper()))

    def test_short_rejected(self):
        self.assertFalse(protocol.validate_hash_format("a" * 63))

    def test_prefix_rejected(self):
        self.assertFalse(protocol.validate_hash_format("sha256:" + self.GOOD))

    def test_whitespace_rejected(self):
        self.assertFalse(protocol.validate_hash_format(self.GOOD + " "))

    def test_non_string_rejected(self):
        self.assertFalse(protocol.validate_hash_format(123))


class TimeoutTests(unittest.TestCase):
    def test_omitted_yields_default(self):
        self.assertEqual(protocol.validate_timeout_ms(None), protocol.DEFAULT_TIMEOUT_MS)

    def test_bounds_accepted_without_clamp(self):
        self.assertEqual(protocol.validate_timeout_ms(1), 1)
        self.assertEqual(protocol.validate_timeout_ms(protocol.MAX_TIMEOUT_MS),
                         protocol.MAX_TIMEOUT_MS)

    def test_out_of_range_rejects_no_clamp(self):
        self.assertIs(protocol.validate_timeout_ms(0), False)
        self.assertIs(protocol.validate_timeout_ms(protocol.MAX_TIMEOUT_MS + 1), False)

    def test_wrong_types_reject(self):
        for bad in (True, 1.5, "500", [], {}):
            self.assertIs(protocol.validate_timeout_ms(bad), False)


class ScalarDomainTests(unittest.TestCase):
    def test_allowed_scalars(self):
        for good in ("text", 3, True, False, None):
            self.assertTrue(protocol.valid_scalar(good), good)

    def test_float_rejected(self):
        self.assertFalse(protocol.valid_scalar(1.5))

    def test_array_rejected(self):
        self.assertFalse(protocol.valid_scalar([1, 2]))

    def test_object_rejected(self):
        self.assertFalse(protocol.valid_scalar({"deep": True}))


class RequestSchemaUnitTests(unittest.TestCase):
    def base_request(self):
        return {
            "protocol_version": 1,
            "request_id": str(__import__("uuid").uuid4()),
            "job_id": "JOB-U",
            "operation": "INSPECT_SYNTHETIC_INPUT",
            "parameters": {"input_name": "fixture.txt"},
        }

    def test_valid(self):
        ok, code, _ = validate_request(self.base_request())
        self.assertTrue(ok)
        self.assertIsNone(code)

    def test_unknown_field_rejected(self):
        req = self.base_request()
        req["sneaky"] = True
        ok, code, detail = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)
        self.assertIn("sneaky", detail)

    def test_missing_required_rejected(self):
        req = self.base_request()
        del req["operation"]
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_job_id_violation_has_own_code(self):
        req = self.base_request()
        req["job_id"] = "JOB..BAD"
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_JOB_ID)

    def test_operation_violation_has_own_code(self):
        # Malformed operation (schema level); unknown-but-well-formed
        # operations are rejected by the registry with the same code.
        req = self.base_request()
        req["operation"] = 123
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_OPERATION)

    # --- Wire-schema adversarial coverage (P1 request_id provenance) ---
    #
    # The PUBLIC OperationCall API no longer accepts request_id or
    # protocol_version from the caller — those fields are trusted-side
    # wire fields. Their adversarial validation lives HERE, on the
    # WireRequest that the orchestrator would otherwise hand to the
    # worker. Coverage is preserved by exercising validate_request()
    # directly with attacker-shaped WireRequests.

    def test_invalid_uuid_malformed_rejected(self):
        req = self.base_request()
        req["request_id"] = "not-a-uuid"
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_non_v4_uuid_rejected(self):
        req = self.base_request()
        req["request_id"] = "a0f0e0d0-1111-1222-8333-444455556666"
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_uppercase_uuid_rejected(self):
        import uuid as _uuid
        req = self.base_request()
        req["request_id"] = str(_uuid.uuid4()).upper()
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_protocol_version_true_rejected(self):
        req = self.base_request()
        req["protocol_version"] = True
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_protocol_version_float_rejected(self):
        req = self.base_request()
        req["protocol_version"] = 1.0
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_protocol_version_string_rejected(self):
        req = self.base_request()
        req["protocol_version"] = "1"
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.INVALID_REQUEST)

    def test_unsupported_protocol_version_rejected(self):
        req = self.base_request()
        req["protocol_version"] = 2
        ok, code, _ = validate_request(req)
        self.assertFalse(ok)
        self.assertEqual(code, errors.UNSUPPORTED_PROTOCOL_VERSION)


if __name__ == "__main__":
    unittest.main()
