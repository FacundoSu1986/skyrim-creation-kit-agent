"""Structural contract: the forensic probe must reuse the ETEC runner.

POC-003's adversarial review found that ``pex_header_probe`` launched
``PapyrusCompiler.exe`` with its own ``subprocess.run``, creating a second
execution boundary that skipped the executable/flags hash gates, the Job
Object, process-tree measurement, bounded streaming, input verification and
workspace policy. This test pins the corrected topology::

    pex_header_probe
        ↓
    trusted POC-003 runner
        ↓
    PAPYRUS_COMPILE_DRYRUN_V1
        ↓
    PapyrusCompiler.exe

A second ``subprocess``-based launcher must never reappear.
"""

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import poc_003.runner as runner  # noqa: E402
from poc_003 import pex_header_probe  # noqa: E402


class ProbeContractTests(unittest.TestCase):
    def test_probe_uses_runner_not_direct_subprocess_contract(self):
        source = inspect.getsource(pex_header_probe)
        self.assertNotIn("subprocess.run", source)
        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("import subprocess", source)
        self.assertIn("runner.run_once", source)

    def test_probe_loads_the_same_closed_profile(self):
        source = inspect.getsource(pex_header_probe)
        self.assertIn("profile.LocalConfig.from_file", source)
        self.assertIn("runner.RunRequest", source)

    def test_probe_never_prints_raw_pex_bytes(self):
        """PEX artifacts embed the host account/machine name in clear text."""
        source = inspect.getsource(pex_header_probe)
        self.assertNotIn("prefix_redacted", source)
        self.assertNotIn("PEX_PREFIX", source)

    def test_diff_offsets_include_the_longer_tail(self):
        a = b"aaaa"
        b = b"ab"  # differs at index 1 and the tail (2,3)
        self.assertEqual([1, 2, 3], pex_header_probe._diff_offsets(a, b))

    def test_header_observations_are_structured_non_raw(self):
        observations = pex_header_probe._header_observations(b"PEX\x0c" + bytes(24))
        self.assertEqual("5045580c", observations["magic_hex"])
        self.assertIn("uint32_be_offset_0x0c", observations)
        self.assertIn("ascii_segments_in_prefix_512", observations)
        # No raw string table content may ever be exposed.
        self.assertNotIn("raw_strings", observations)
        self.assertNotIn("host_name", observations)


if __name__ == "__main__":
    unittest.main()