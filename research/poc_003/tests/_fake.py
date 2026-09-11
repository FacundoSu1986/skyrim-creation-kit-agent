"""Controlled stand-in for ``PapyrusCompiler.exe``, used only by the tests.

The real compiler is never invoked by the unit suite, so the suite stays
hermetic and CI-runnable. The stand-in is a Python script written to
``<token>.psc`` and launched with ``shell=False`` by the very same code path
the real experiment uses, so spawn, deadline, capture, containment and cleanup
logic are all genuinely exercised.

Behaviour is selected by name. Every behaviour is deterministic except
``random_output``, which exists to prove the determinism gate can fail.
"""

from __future__ import annotations

import os
import sys
import time

_TEMPLATE = '''"""Controlled stand-in. Not Papyrus source at runtime; a test double."""
import os, sys, time, subprocess

BEHAVIOUR = {behaviour!r}
args = {{a.split("=", 1)[0]: a.split("=", 1)[1] for a in sys.argv[1:] if "=" in a}}
out_dir = args.get("-o", ".")
imports = args.get("-i", ".").split(";")[0]
ws_root = os.path.dirname(os.path.abspath(out_dir))

if BEHAVIOUR == "success":
    with open(os.path.join(out_dir, {token!r} + ".pex"), "wb") as fh:
        fh.write(b"FAKE-PEX-CONTENT")

elif BEHAVIOUR == "random_output":
    with open(os.path.join(out_dir, {token!r} + ".pex"), "wb") as fh:
        fh.write(os.urandom(32))

elif BEHAVIOUR == "empty_output":
    open(os.path.join(out_dir, {token!r} + ".pex"), "wb").close()

elif BEHAVIOUR == "no_output":
    pass

elif BEHAVIOUR == "fail":
    sys.stderr.write("synthetic failure")
    sys.exit(3)

elif BEHAVIOUR == "mutate_flags":
    flags_path = args.get("-f", "")
    if flags_path:
        with open(flags_path, "wb") as fh:
            fh.write(b"tampered")
    sys.exit(0)

elif BEHAVIOUR == "fail_and_stray":
    with open(os.path.join(ws_root, "stray.txt"), "wb") as fh:
        fh.write(b"undeclared")
    sys.exit(3)

elif BEHAVIOUR == "sleep":
    time.sleep(300)

elif BEHAVIOUR == "spam":
    sys.stdout.write("A" * 200000)
    sys.stderr.write("B" * 200000)
    with open(os.path.join(out_dir, {token!r} + ".pex"), "wb") as fh:
        fh.write(b"FAKE-PEX-CONTENT")

elif BEHAVIOUR == "stray":
    with open(os.path.join(out_dir, {token!r} + ".pex"), "wb") as fh:
        fh.write(b"FAKE-PEX-CONTENT")
    with open(os.path.join(ws_root, "stray.txt"), "wb") as fh:
        fh.write(b"undeclared")

elif BEHAVIOUR == "mutate_import":
    with open(os.path.join(out_dir, {token!r} + ".pex"), "wb") as fh:
        fh.write(b"FAKE-PEX-CONTENT")
    with open(os.path.join(imports, "injected.psc"), "wb") as fh:
        fh.write(b"injected")

elif BEHAVIOUR == "fail_and_mutate":
    with open(os.path.join(imports, "injected.psc"), "wb") as fh:
        fh.write(b"injected")
    sys.exit(3)

elif BEHAVIOUR == "spawn_child":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    time.sleep(300)

sys.exit(0)
'''


def write_fake(path: str, token: str, behaviour: str) -> str:
    """Materialise the stand-in at ``path``. Returns the path."""
    with open(path, "w", encoding="ascii", newline="") as handle:
        handle.write(_TEMPLATE.format(behaviour=behaviour, token=token))
    return path
