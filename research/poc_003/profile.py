"""The closed profile ``PAPYRUS_COMPILE_DRYRUN_V1``.

This is a *profile*, not a runner. It declares one permitted executable, one
pinned hash, one argv shape, one cwd policy, one environment policy and one
allowlisted set of operation tokens. There is no field here through which a
caller can name an executable, choose a flag, or smuggle a string into argv.

Operation-specific values may reach argv only as validated typed tokens
resolved trusted-side under a closed grammar, per ADR-004 E4.

The argv shape is not invented. It was read from Bethesda's own
``ScriptCompile.bat`` shipped alongside the executable and confirmed against
the tool's own usage output::

    PapyrusCompiler <object> -f=<flags.flg> -i=<imports> -o=<output>

One empirical property of the tool, measured during POC-003 and therefore
declared here rather than left implicit: the compiler resolves the compilation
object *by script name through the import path list*, so a source file whose
directory is not reachable from ``-i`` fails with "unable to locate script".
The ``-i`` value is consequently composed of the allowlisted import root and
the read-only ``input/`` directory. Both components are trusted-side
constants; neither is caller-supplied.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

PROFILE_ID = "PAPYRUS_COMPILE_DRYRUN_V1"

#: ADR-002 safe-name grammar, reused verbatim.
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

#: Closed operation enum. There is no "run this command" member.
OP_COMPILE_FIXTURE = "compile_fixture"
ALLOWED_OPERATIONS: frozenset[str] = frozenset({OP_COMPILE_FIXTURE})

#: Closed set of safe-name tokens the profile will resolve to a source script.
ALLOWED_SOURCE_TOKENS: frozenset[str] = frozenset(
    {"Poc003Minimal", "Poc003Broken", "Poc003Hang"}
)

#: Bounded capture. Applied during transfer, not after.
STREAM_LIMIT_BYTES = 64 * 1024

#: Single monotonic execution deadline, plus bounded cleanup grace.
DEFAULT_DEADLINE_S = 60.0
CLEANUP_GRACE_S = 10.0

#: Bounded window for joining the bounded I/O reader threads after cleanup.
IO_JOIN_GRACE_S = 5.0

#: Process-tree sampling interval while the tool runs.
TREE_POLL_INTERVAL_S = 0.05

#: Environment redirect targets inside the workspace.
_ENV_TEMP_VARS = ("TEMP", "TMP")

_FIXED_PATH = (r"C:\Windows\System32", r"C:\Windows")


class ProfileViolation(Exception):
    """A closed-world rule was violated before anything was spawned."""


@dataclass(frozen=True)
class LocalConfig:
    """Trusted, machine-local, deliberately not versioned.

    The executable and the Bethesda-shipped flags file are local dependencies.
    Neither is redistributable, so neither is committed; the profile pins them
    by hash instead.
    """

    executable: str
    executable_sha256: str
    flags: str
    flags_sha256: str

    @classmethod
    def from_file(cls, path: str) -> "LocalConfig":
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            raise ProfileViolation(f"unreadable local config {path!r}: {exc}") from exc

        if not isinstance(data, dict):
            raise ProfileViolation(
                f"local config must be a JSON object, got {type(data).__name__}"
            )

        missing = [
            key
            for key in ("executable", "executable_sha256", "flags", "flags_sha256")
            if not isinstance(data.get(key), str) or not data[key]
        ]
        if missing:
            raise ProfileViolation(f"local config missing keys: {sorted(missing)}")

        exe = os.path.abspath(data["executable"])
        flags = os.path.abspath(data["flags"])
        if not os.path.isfile(exe):
            raise ProfileViolation(f"configured executable does not exist: {exe}")
        if not os.path.isfile(flags):
            raise ProfileViolation(f"configured flags file does not exist: {flags}")
        return cls(
            executable=exe,
            executable_sha256=data["executable_sha256"].strip().lower(),
            flags=flags,
            flags_sha256=data["flags_sha256"].strip().lower(),
        )


def validate_profile_id(profile_id: str) -> str:
    """Accept exactly one profile.

    ETEC profiles are individually specified and individually reviewed
    (ADR-004). A request naming any other profile is a closed-world violation,
    not a dispatch decision made by the caller.
    """
    if not isinstance(profile_id, str) or profile_id != PROFILE_ID:
        raise ProfileViolation(f"unknown profile: {profile_id!r}")
    return profile_id


def validate_token(token: str) -> str:
    """Validate a safe-name token against the closed grammar.

    Rejects separators, drive letters, UNC prefixes, whitespace, ``..`` and
    any non-grammar byte before the token is ever resolved to a path.
    """
    if not isinstance(token, str) or not token:
        raise ProfileViolation("source token must be a non-empty string")
    if len(token) > 64:
        raise ProfileViolation("source token exceeds 64 characters")
    if ".." in token:
        raise ProfileViolation("source token contains '..'")
    if not SAFE_NAME_RE.match(token):
        raise ProfileViolation(f"source token violates safe-name grammar: {token!r}")
    if token not in ALLOWED_SOURCE_TOKENS:
        raise ProfileViolation(f"source token is not in the closed allowlist: {token!r}")
    return token


def build_argv(
    config: LocalConfig,
    source_path: str,
    input_dir: str,
    import_dir: str,
    output_dir: str,
) -> list[str]:
    """Build the single permitted argv shape. No free-form element."""
    return [
        config.executable,
        os.path.abspath(source_path),
        f"-f={os.path.abspath(config.flags)}",
        f"-i={os.path.abspath(import_dir)};{os.path.abspath(input_dir)}",
        f"-o={os.path.abspath(output_dir)}",
    ]


def build_environment(temp_dir: str) -> dict[str, str]:
    """Deny-by-default environment. Nothing is inherited blindly.

    ``COMSPEC`` is set because it is a conventional requirement of Win32
    tooling, but nothing in this profile ever launches through it: the spawn is
    ``shell=False`` and no shell process enters the launch tree.
    """
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    return {
        "SystemRoot": system_root,
        "COMSPEC": os.environ.get("COMSPEC") or rf"{system_root}\System32\cmd.exe",
        "PATH": os.pathsep.join(_FIXED_PATH),
        "TEMP": os.path.abspath(temp_dir),
        "TMP": os.path.abspath(temp_dir),
    }
